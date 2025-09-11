from fastapi import FastAPI, HTTPException, Response, Request, Form
from pydantic import BaseModel
import asyncpg
import os
from datetime import datetime
from typing import Optional
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from dialer import VoiceDialer
from webhooks import VOICE_WEBHOOK_HANDLERS
from libs.pkg_bus.bus import consume, redis

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")

# Initialize dialer
dialer = VoiceDialer()

# Metrics
CALLS_INITIATED = Counter("voice_calls_initiated_total", "Total calls initiated")
CALLS_CONNECTED = Counter("voice_calls_connected_total", "Total calls connected")
CALLS_COMPLETED = Counter("voice_calls_completed_total", "Total calls completed", ["outcome"])

class DialRequest(BaseModel):
    lead_id: str
    phone: str
    agent_id: Optional[str] = None
    notes: Optional[str] = ""

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)

@app.get("/health")
async def health():
    return {"ok": True, "service": "voice_hub"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/dial")
async def dial_lead(dial_request: DialRequest, request: Request):
    """Initiate outbound call to lead"""
    
    # Get lead data
    lead = await app.state.db.fetchrow("SELECT * FROM leads WHERE id = $1", dial_request.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Parse lead payload
    import json
    lead_data = json.loads(lead['payload']) if lead['payload'] else {}
    lead_data['lead_id'] = dial_request.lead_id
    lead_data['phone'] = dial_request.phone
    
    # Get webhook base URL from request
    host = request.headers.get("host")
    protocol = "https" if "https" in str(request.url) else "http"
    webhook_base_url = f"{protocol}://{host}"
    
    # Initiate call
    call_result = await dialer.initiate_call(lead_data, webhook_base_url)
    
    if call_result['status'] == 'error':
        raise HTTPException(status_code=400, detail=call_result['message'])
    
    # Create call record
    call_id = await app.state.db.fetchval("""
        INSERT INTO calls (
            lead_id, phone_number, status, agent_id, notes, 
            provider_call_id, started_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
    """, 
        dial_request.lead_id, 
        dial_request.phone,
        call_result.get('status', 'queued'),
        dial_request.agent_id,
        dial_request.notes,
        call_result.get('provider_call_id'),
        datetime.now() if call_result['status'] != 'deferred' else None
    )
    
    if call_result['status'] == 'initiated':
        CALLS_INITIATED.inc()
    
    return {
        "call_id": str(call_id),
        "status": call_result['status'],
        "provider_call_id": call_result.get('provider_call_id'),
        "message": call_result.get('message')
    }

@app.get("/calls/{call_id}")
async def get_call_details(call_id: str):
    """Get call details and status"""
    
    call = await app.state.db.fetchrow("""
        SELECT c.*, l.vertical, l.payload->>'contact'->>'email' as lead_email
        FROM calls c
        LEFT JOIN leads l ON c.lead_id = l.id
        WHERE c.id = $1
    """, call_id)
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "id": str(call['id']),
        "lead_id": str(call['lead_id']),
        "phone_number": call['phone_number'],
        "status": call['status'],
        "duration_seconds": call['duration_seconds'],
        "recording_url": call['recording_url'],
        "outcome": call['outcome'],
        "agent_id": call['agent_id'],
        "notes": call['notes'],
        "started_at": call['started_at'].isoformat() if call['started_at'] else None,
        "ended_at": call['ended_at'].isoformat() if call['ended_at'] else None,
        "lead_context": {
            "vertical": call['vertical'],
            "email": call['lead_email']
        }
    }

@app.get("/calls")
async def list_calls(
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 50
):
    """List calls with filters"""
    
    query = "SELECT * FROM calls WHERE 1=1"
    params = []
    
    if status:
        params.append(status)
        query += f" AND status = ${len(params)}"
    
    if agent_id:
        params.append(agent_id)
        query += f" AND agent_id = ${len(params)}"
    
    params.append(limit)
    query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
    
    calls = await app.state.db.fetch(query, *params)
    
    return {
        "calls": [
            {
                "id": str(call['id']),
                "lead_id": str(call['lead_id']),
                "phone_number": call['phone_number'],
                "status": call['status'],
                "duration_seconds": call['duration_seconds'],
                "outcome": call['outcome'],
                "agent_id": call['agent_id'],
                "started_at": call['started_at'].isoformat() if call['started_at'] else None
            } for call in calls
        ]
    }

# TwiML Endpoints
@app.post("/voice/twiml")
async def twiml_instructions(request: Request):
    """Serve TwiML instructions for calls"""
    
    form_data = await request.form()
    call_sid = form_data.get('CallSid')
    
    # Get call context
    call = await app.state.db.fetchrow("""
        SELECT c.*, l.payload 
        FROM calls c
        LEFT JOIN leads l ON c.lead_id = l.id
        WHERE c.provider_call_id = $1
    """, call_sid)
    
    if call:
        import json
        lead_data = json.loads(call['payload']) if call['payload'] else {}
        twiml = dialer.generate_twiml_script(lead_data)
    else:
        # Fallback TwiML
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you for your interest. Please hold while we connect you.</Say>
    <Hangup/>
</Response>"""
    
    return Response(content=twiml, media_type="text/xml")

@app.post("/voice/gather")
async def handle_gather(request: Request):
    """Handle DTMF input from calls"""
    
    form_data = await request.form()
    call_sid = form_data.get('CallSid')
    digits = form_data.get('Digits', '')
    
    # Get call context
    call = await app.state.db.fetchrow("""
        SELECT c.*, l.payload 
        FROM calls c
        LEFT JOIN leads l ON c.lead_id = l.id
        WHERE c.provider_call_id = $1
    """, call_sid)
    
    # Update call outcome based on selection
    outcome_mapping = {
        '1': 'interested',
        '2': 'callback_requested', 
        '9': 'opt_out'
    }
    
    outcome = outcome_mapping.get(digits, 'no_response')
    
    if call:
        await app.state.db.execute("""
            UPDATE calls SET outcome = $1, updated_at = now() 
            WHERE provider_call_id = $2
        """, outcome, call_sid)
        
        import json
        lead_data = json.loads(call['payload']) if call['payload'] else {}
        twiml = dialer.process_gather_response(digits, lead_data)
    else:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Hangup/></Response>"""
    
    return Response(content=twiml, media_type="text/xml")

# Webhook Endpoints
@app.post("/webhooks/voice-status")
async def voice_status_webhook(request: Request):
    """Handle Twilio voice status webhooks"""
    
    form_data = await request.form()
    webhook_data = dict(form_data)
    
    # Process webhook
    if 'status_callback' in VOICE_WEBHOOK_HANDLERS:
        await VOICE_WEBHOOK_HANDLERS['status_callback'](webhook_data, app.state.db)
    
    # Update metrics
    call_status = webhook_data.get('CallStatus')
    if call_status == 'answered':
        CALLS_CONNECTED.inc()
    elif call_status == 'completed':
        # Get outcome from database
        call_sid = webhook_data.get('CallSid')
        call = await app.state.db.fetchrow("""
            SELECT outcome FROM calls WHERE provider_call_id = $1
        """, call_sid)
        outcome = call['outcome'] if call else 'unknown'
        CALLS_COMPLETED.labels(outcome=outcome).inc()
    
    return {"received": True}

@app.post("/webhooks/machine-detection")
async def machine_detection_webhook(request: Request):
    """Handle answering machine detection webhooks"""
    
    form_data = await request.form()
    webhook_data = dict(form_data)
    
    if 'machine_detection' in VOICE_WEBHOOK_HANDLERS:
        await VOICE_WEBHOOK_HANDLERS['machine_detection'](webhook_data, app.state.db)
    
    return {"received": True}

# Call Analytics
@app.get("/analytics/calls")
async def call_analytics():
    """Get call center analytics"""
    
    # Overall stats
    overall_stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_calls,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_calls,
            COUNT(CASE WHEN status = 'connected' THEN 1 END) as connected_calls,
            COUNT(CASE WHEN outcome IN ('interested', 'qualified', 'converted') THEN 1 END) as positive_outcomes,
            AVG(duration_seconds) as avg_duration
        FROM calls
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    """)
    
    # Outcome breakdown
    outcome_stats = await app.state.db.fetch("""
        SELECT outcome, COUNT(*) as count
        FROM calls 
        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        AND outcome IS NOT NULL
        GROUP BY outcome
        ORDER BY count DESC
    """)
    
    connect_rate = 0
    if overall_stats['total_calls'] > 0:
        connect_rate = overall_stats['connected_calls'] / overall_stats['total_calls'] * 100
    
    return {
        "summary": {
            "total_calls": overall_stats['total_calls'],
            "completed_calls": overall_stats['completed_calls'],
            "connected_calls": overall_stats['connected_calls'],
            "connect_rate_percent": round(connect_rate, 2),
            "positive_outcomes": overall_stats['positive_outcomes'],
            "avg_duration_seconds": round(float(overall_stats['avg_duration'] or 0), 2)
        },
        "outcomes": [
            {
                "outcome": row['outcome'],
                "count": row['count']
            } for row in outcome_stats
        ]
    }