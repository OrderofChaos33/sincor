from datetime import datetime
import asyncpg
from libs.pkg_bus.bus import xadd, redis

async def handle_voice_status(webhook_data: dict, db_conn):
    """Handle Twilio voice status webhooks"""
    
    call_sid = webhook_data.get('CallSid')
    call_status = webhook_data.get('CallStatus')
    duration = int(webhook_data.get('CallDuration', 0))
    recording_url = webhook_data.get('RecordingUrl')
    
    # Map Twilio statuses to our internal statuses
    status_mapping = {
        'queued': 'queued',
        'initiated': 'dialing', 
        'ringing': 'dialing',
        'in-progress': 'connected',
        'answered': 'connected',
        'completed': 'completed',
        'busy': 'busy',
        'no-answer': 'no_answer',
        'failed': 'failed',
        'canceled': 'failed'
    }
    
    internal_status = status_mapping.get(call_status, call_status)
    
    # Update call record
    call_data = await db_conn.fetchrow("""
        UPDATE calls 
        SET 
            status = $1,
            duration_seconds = $2,
            recording_url = $3,
            ended_at = CASE WHEN $1 IN ('completed', 'failed', 'busy', 'no_answer') THEN now() ELSE ended_at END,
            updated_at = now()
        WHERE provider_call_id = $4
        RETURNING id, lead_id, status
    """, internal_status, duration, recording_url, call_sid)
    
    if call_data:
        # Emit events based on call status
        r = await redis()
        
        if internal_status == 'connected':
            await xadd(r, "stream.voice.call_connected", {
                "call_id": str(call_data['id']),
                "lead_id": str(call_data['lead_id']),
                "provider_call_id": call_sid,
                "timestamp": datetime.now().isoformat()
            })
            
        elif internal_status == 'completed':
            await xadd(r, "stream.voice.call_completed", {
                "call_id": str(call_data['id']),
                "lead_id": str(call_data['lead_id']),
                "duration_seconds": duration,
                "recording_url": recording_url,
                "timestamp": datetime.now().isoformat()
            })
            
        elif internal_status in ['no_answer', 'busy']:
            await xadd(r, f"stream.voice.{internal_status}", {
                "call_id": str(call_data['id']),
                "lead_id": str(call_data['lead_id']),
                "status": internal_status,
                "timestamp": datetime.now().isoformat()
            })
            
        elif internal_status == 'failed':
            await xadd(r, "stream.voice.call_failed", {
                "call_id": str(call_data['id']),
                "lead_id": str(call_data['lead_id']),
                "error": webhook_data.get('ErrorMessage', 'Call failed'),
                "timestamp": datetime.now().isoformat()
            })

async def handle_machine_detection(webhook_data: dict, db_conn):
    """Handle answering machine detection"""
    
    call_sid = webhook_data.get('CallSid')
    answered_by = webhook_data.get('AnsweredBy')  # 'human' or 'machine'
    
    if answered_by == 'machine':
        # Update call status to voicemail
        await db_conn.execute("""
            UPDATE calls 
            SET status = 'voicemail', outcome = 'voicemail_detected', updated_at = now()
            WHERE provider_call_id = $1
        """, call_sid)
        
        # Emit voicemail event
        call_data = await db_conn.fetchrow("""
            SELECT id, lead_id FROM calls WHERE provider_call_id = $1
        """, call_sid)
        
        if call_data:
            r = await redis()
            await xadd(r, "stream.voice.voicemail", {
                "call_id": str(call_data['id']),
                "lead_id": str(call_data['lead_id']),
                "provider_call_id": call_sid,
                "timestamp": datetime.now().isoformat()
            })

# Webhook handler mapping for voice events
VOICE_WEBHOOK_HANDLERS = {
    'status_callback': handle_voice_status,
    'machine_detection': handle_machine_detection
}