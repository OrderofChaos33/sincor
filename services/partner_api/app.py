from fastapi import FastAPI, HTTPException, Response, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
import hashlib
import secrets
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("PARTNER_ADMIN_KEY", "admin-dev-key")

security = HTTPBearer()

# Metrics
PARTNER_REQUESTS = Counter("partner_api_requests_total", "Partner API requests", ["partner", "endpoint"])
PARTNER_LEADS = Counter("partner_leads_total", "Leads from partners", ["partner", "vertical"])
REV_SHARE_PAID = Counter("partner_revenue_share_cents_total", "Revenue share paid", ["partner"])

class PartnerRegistration(BaseModel):
    company_name: str
    contact_email: EmailStr
    website: Optional[str] = None
    verticals: List[str]
    revenue_share_pct: float  # e.g., 0.15 for 15%
    
class LeadSubmission(BaseModel):
    email: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    vertical: str
    source: Optional[str] = None
    campaign_id: Optional[str] = None
    custom_data: Optional[Dict] = {}

class RevenueEvent(BaseModel):
    lead_id: str
    event_type: str  # delivery, conversion, subscription
    amount_cents: int
    metadata: Optional[Dict] = {}

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

async def verify_partner_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify partner API key and return partner info"""
    api_key = credentials.credentials
    
    partner = await app.state.db.fetchrow("""
        SELECT * FROM partner_accounts 
        WHERE api_key = $1 AND active = true
    """, api_key)
    
    if not partner:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    
    # Update last seen
    await app.state.db.execute("""
        UPDATE partner_accounts SET last_seen = now() WHERE id = $1
    """, partner['id'])
    
    return partner

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)

@app.get("/health")
async def health():
    return {"ok": True, "service": "partner_api"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Partner Management
@app.post("/partners/register", dependencies=[Depends(verify_admin)])
async def register_partner(registration: PartnerRegistration):
    """Register new partner (admin only)"""
    
    # Generate API key
    api_key = f"pk_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"
    webhook_secret = secrets.token_urlsafe(32)
    
    partner_id = await app.state.db.fetchval("""
        INSERT INTO partner_accounts (
            company_name, contact_email, website, verticals, 
            revenue_share_pct, api_key, webhook_secret, active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, true)
        RETURNING id
    """, registration.company_name, registration.contact_email, registration.website,
        registration.verticals, registration.revenue_share_pct, api_key, webhook_secret)
    
    return {
        "partner_id": str(partner_id),
        "company_name": registration.company_name,
        "api_key": api_key,
        "webhook_secret": webhook_secret,
        "revenue_share_pct": registration.revenue_share_pct,
        "endpoints": {
            "submit_lead": "/v1/leads",
            "get_stats": "/v1/stats",
            "webhook_url": "https://your-domain.com/partner/webhook"
        }
    }

@app.get("/partners", dependencies=[Depends(verify_admin)])
async def list_partners():
    """List all partners (admin only)"""
    
    partners = await app.state.db.fetch("""
        SELECT 
            p.*,
            (SELECT COUNT(*) FROM partner_leads pl WHERE pl.partner_id = p.id) as total_leads,
            (SELECT SUM(revenue_share_cents) FROM partner_ledger pl2 WHERE pl2.partner_id = p.id) as total_earned_cents
        FROM partner_accounts p
        ORDER BY p.created_at DESC
    """)
    
    return {
        "partners": [
            {
                "id": str(p['id']),
                "company_name": p['company_name'],
                "contact_email": p['contact_email'],
                "verticals": p['verticals'],
                "revenue_share_pct": float(p['revenue_share_pct']),
                "active": p['active'],
                "total_leads": p['total_leads'],
                "total_earned_cents": p['total_earned_cents'] or 0,
                "created_at": p['created_at'].isoformat(),
                "last_seen": p['last_seen'].isoformat() if p['last_seen'] else None
            } for p in partners
        ]
    }

# Partner API Endpoints
@app.post("/v1/leads")
async def submit_lead(
    lead: LeadSubmission,
    request: Request,
    partner = Depends(verify_partner_key)
):
    """Submit lead via partner API"""
    
    PARTNER_REQUESTS.labels(partner=partner['company_name'], endpoint="/v1/leads").inc()
    
    # Validate vertical
    if lead.vertical not in partner['verticals']:
        raise HTTPException(
            status_code=403, 
            detail=f"Vertical '{lead.vertical}' not authorized. Allowed: {partner['verticals']}"
        )
    
    # Create lead record
    lead_data = {
        "email": lead.email,
        "phone": lead.phone,
        "vertical": lead.vertical,
        "payload": {
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "source": lead.source or f"partner_{partner['company_name']}",
            "campaign_id": lead.campaign_id,
            "partner_data": lead.custom_data,
            "ip": request.client.host
        },
        "contact": {
            "email": lead.email,
            "phone": lead.phone
        },
        "attributes": {
            "name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
            "partner_id": str(partner['id']),
            "partner_campaign": lead.campaign_id
        }
    }
    
    # Insert lead
    lead_id = await app.state.db.fetchval("""
        INSERT INTO leads (id, vertical, email, phone, ip, payload, contact, attributes)
        VALUES (gen_random_uuid(), $1, $2, $3, $4::inet, $5, $6, $7)
        RETURNING id
    """, lead.vertical, lead.email, lead.phone, request.client.host, 
        json.dumps(lead_data["payload"]), json.dumps(lead_data["contact"]), 
        json.dumps(lead_data["attributes"]))
    
    # Track partner lead
    await app.state.db.execute("""
        INSERT INTO partner_leads (partner_id, lead_id, vertical, source, campaign_id)
        VALUES ($1, $2, $3, $4, $5)
    """, partner['id'], lead_id, lead.vertical, lead.source, lead.campaign_id)
    
    # Emit to lead processing pipeline
    await app.state.redis.xadd("stream.leads.received", {
        "lead_id": str(lead_id),
        "vertical": lead.vertical,
        "source": f"partner_{partner['company_name']}",
        "partner_id": str(partner['id'])
    })
    
    PARTNER_LEADS.labels(partner=partner['company_name'], vertical=lead.vertical).inc()
    
    return {
        "lead_id": str(lead_id),
        "status": "accepted",
        "vertical": lead.vertical,
        "estimated_processing_time": "2-5 minutes"
    }

@app.get("/v1/stats")
async def get_partner_stats(partner = Depends(verify_partner_key)):
    """Get partner performance statistics"""
    
    PARTNER_REQUESTS.labels(partner=partner['company_name'], endpoint="/v1/stats").inc()
    
    # Lead statistics
    lead_stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_leads,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as leads_30d,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as leads_7d,
            COUNT(DISTINCT vertical) as active_verticals
        FROM partner_leads 
        WHERE partner_id = $1
    """, partner['id'])
    
    # Revenue statistics
    revenue_stats = await app.state.db.fetchrow("""
        SELECT 
            SUM(revenue_share_cents) as total_earned_cents,
            SUM(revenue_share_cents) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as earned_30d_cents,
            COUNT(*) as total_payouts
        FROM partner_ledger 
        WHERE partner_id = $1
    """, partner['id'])
    
    # Conversion rates by vertical
    conversion_stats = await app.state.db.fetch("""
        SELECT 
            pl.vertical,
            COUNT(pl.*) as submitted_leads,
            COUNT(dl.*) as delivered_leads,
            ROUND(COUNT(dl.*) * 100.0 / GREATEST(COUNT(pl.*), 1), 2) as conversion_rate_pct
        FROM partner_leads pl
        LEFT JOIN delivery_ledger dl ON pl.lead_id = dl.lead_id AND dl.status = 'DELIVERED'
        WHERE pl.partner_id = $1
        GROUP BY pl.vertical
        ORDER BY submitted_leads DESC
    """, partner['id'])
    
    return {
        "partner_id": str(partner['id']),
        "company_name": partner['company_name'],
        "performance": {
            "total_leads": lead_stats['total_leads'],
            "leads_30d": lead_stats['leads_30d'],
            "leads_7d": lead_stats['leads_7d'],
            "active_verticals": lead_stats['active_verticals']
        },
        "earnings": {
            "total_earned_cents": revenue_stats['total_earned_cents'] or 0,
            "earned_30d_cents": revenue_stats['earned_30d_cents'] or 0,
            "total_payouts": revenue_stats['total_payouts'] or 0
        },
        "conversion_by_vertical": [
            {
                "vertical": cs['vertical'],
                "submitted_leads": cs['submitted_leads'],
                "delivered_leads": cs['delivered_leads'],
                "conversion_rate_pct": float(cs['conversion_rate_pct'])
            } for cs in conversion_stats
        ]
    }

@app.get("/v1/leads")
async def get_partner_leads(
    partner = Depends(verify_partner_key),
    vertical: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get partner's submitted leads with status"""
    
    PARTNER_REQUESTS.labels(partner=partner['company_name'], endpoint="/v1/leads").inc()
    
    query = """
        SELECT 
            pl.*,
            l.email,
            l.phone,
            l.created_at as submitted_at,
            dl.status as delivery_status,
            dl.created_at as delivered_at
        FROM partner_leads pl
        JOIN leads l ON pl.lead_id = l.id
        LEFT JOIN delivery_ledger dl ON pl.lead_id = dl.lead_id
        WHERE pl.partner_id = $1
    """
    params = [partner['id']]
    
    if vertical:
        params.append(vertical)
        query += f" AND pl.vertical = ${len(params)}"
    
    query += " ORDER BY pl.created_at DESC"
    params.extend([limit, offset])
    query += f" LIMIT ${len(params)-1} OFFSET ${len(params)}"
    
    leads = await app.state.db.fetch(query, *params)
    
    return {
        "leads": [
            {
                "lead_id": str(lead['lead_id']),
                "email": lead['email'],
                "phone": lead['phone'],
                "vertical": lead['vertical'],
                "source": lead['source'],
                "campaign_id": lead['campaign_id'],
                "submitted_at": lead['submitted_at'].isoformat(),
                "delivery_status": lead['delivery_status'],
                "delivered_at": lead['delivered_at'].isoformat() if lead['delivered_at'] else None
            } for lead in leads
        ],
        "total_returned": len(leads)
    }

# Revenue Tracking & Webhooks
@app.post("/webhook/revenue")
async def track_revenue_event(event: RevenueEvent):
    """Internal webhook for revenue tracking"""
    
    # Find partner for this lead
    partner_lead = await app.state.db.fetchrow("""
        SELECT pl.*, pa.revenue_share_pct, pa.company_name
        FROM partner_leads pl
        JOIN partner_accounts pa ON pl.partner_id = pa.id
        WHERE pl.lead_id = $1
    """, event.lead_id)
    
    if not partner_lead:
        return {"status": "ignored", "reason": "not_partner_lead"}
    
    # Calculate revenue share
    revenue_share_cents = int(event.amount_cents * partner_lead['revenue_share_pct'])
    
    # Record in partner ledger
    ledger_id = await app.state.db.fetchval("""
        INSERT INTO partner_ledger (
            partner_id, lead_id, event_type, gross_cents, 
            revenue_share_cents, revenue_share_pct
        ) VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
    """, partner_lead['partner_id'], event.lead_id, event.event_type,
        event.amount_cents, revenue_share_cents, partner_lead['revenue_share_pct'])
    
    REV_SHARE_PAID.labels(partner=partner_lead['company_name']).inc(revenue_share_cents)
    
    return {
        "ledger_id": str(ledger_id),
        "partner_id": str(partner_lead['partner_id']),
        "revenue_share_cents": revenue_share_cents,
        "status": "recorded"
    }

@app.get("/v1/payouts")
async def get_partner_payouts(partner = Depends(verify_partner_key)):
    """Get partner payout history"""
    
    payouts = await app.state.db.fetch("""
        SELECT 
            DATE_TRUNC('month', created_at) as month,
            SUM(revenue_share_cents) as total_cents,
            COUNT(*) as event_count,
            array_agg(DISTINCT event_type) as event_types
        FROM partner_ledger 
        WHERE partner_id = $1
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month DESC
        LIMIT 12
    """, partner['id'])
    
    return {
        "partner_id": str(partner['id']),
        "monthly_payouts": [
            {
                "month": payout['month'].strftime("%Y-%m"),
                "total_cents": payout['total_cents'],
                "event_count": payout['event_count'],
                "event_types": payout['event_types']
            } for payout in payouts
        ]
    }

# Admin Revenue Share Management
@app.get("/admin/ledger", dependencies=[Depends(verify_admin)])
async def get_revenue_ledger(
    partner_id: Optional[str] = None,
    limit: int = 100
):
    """Get revenue share ledger (admin only)"""
    
    query = """
        SELECT 
            pl.*,
            pa.company_name,
            l.email,
            l.vertical
        FROM partner_ledger pl
        JOIN partner_accounts pa ON pl.partner_id = pa.id
        JOIN leads l ON pl.lead_id = l.id
        WHERE 1=1
    """
    params = []
    
    if partner_id:
        params.append(partner_id)
        query += f" AND pl.partner_id = ${len(params)}"
    
    query += " ORDER BY pl.created_at DESC"
    params.append(limit)
    query += f" LIMIT ${len(params)}"
    
    entries = await app.state.db.fetch(query, *params)
    
    return {
        "ledger_entries": [
            {
                "id": str(entry['id']),
                "partner_company": entry['company_name'],
                "lead_email": entry['email'],
                "vertical": entry['vertical'],
                "event_type": entry['event_type'],
                "gross_cents": entry['gross_cents'],
                "revenue_share_cents": entry['revenue_share_cents'],
                "revenue_share_pct": float(entry['revenue_share_pct']),
                "created_at": entry['created_at'].isoformat()
            } for entry in entries
        ]
    }