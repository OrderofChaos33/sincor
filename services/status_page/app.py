from fastapi import FastAPI, HTTPException, Response, Depends, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import asyncio

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("STATUS_ADMIN_KEY", "admin-dev-key")
BASE_URL = os.getenv("STATUS_BASE_URL", "https://status.sincor.com")

# Metrics
SLA_VIOLATIONS = Counter("sla_violations_total", "SLA violations", ["service", "tier"])
UPTIME_PERCENTAGE = Gauge("service_uptime_percentage", "Service uptime percentage", ["service"])
RESPONSE_TIME_MS = Gauge("service_response_time_ms", "Service response time", ["service"])

class SLAIncident(BaseModel):
    title: str
    description: str
    service: str
    severity: str  # low, medium, high, critical
    status: str = "investigating"  # investigating, identified, monitoring, resolved
    
class SLATier(BaseModel):
    name: str
    uptime_sla: float  # 99.9, 99.95, 99.99
    response_time_sla: int  # milliseconds
    support_hours: str  # "24/7", "business_hours"
    monthly_fee_cents: int
    credit_rate: float  # % of monthly fee per SLA violation

class TenantSLA(BaseModel):
    tenant_id: str
    sla_tier: str
    start_date: datetime
    monthly_fee_cents: int

# SLA Tier Definitions
SLA_TIERS = {
    "basic": {
        "name": "Basic",
        "uptime_sla": 99.0,
        "response_time_sla": 5000,
        "support_hours": "business_hours",
        "monthly_fee_cents": 0,
        "credit_rate": 0.0
    },
    "premium": {
        "name": "Premium",
        "uptime_sla": 99.9,
        "response_time_sla": 2000,
        "support_hours": "24/7",
        "monthly_fee_cents": 9900,  # $99
        "credit_rate": 0.10  # 10% credit per violation
    },
    "enterprise": {
        "name": "Enterprise", 
        "uptime_sla": 99.95,
        "response_time_sla": 1000,
        "support_hours": "24/7",
        "monthly_fee_cents": 29900,  # $299
        "credit_rate": 0.25  # 25% credit per violation
    }
}

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

def calculate_uptime_percentage(total_minutes: int, downtime_minutes: int) -> float:
    """Calculate uptime percentage"""
    if total_minutes == 0:
        return 100.0
    return max(0.0, ((total_minutes - downtime_minutes) / total_minutes) * 100)

def calculate_sla_credits(sla_tier: Dict, uptime_pct: float, avg_response_time_ms: int) -> float:
    """Calculate SLA credit percentage owed"""
    credit_pct = 0.0
    
    # Uptime SLA breach
    if uptime_pct < sla_tier['uptime_sla']:
        violation_severity = sla_tier['uptime_sla'] - uptime_pct
        if violation_severity >= 1.0:  # >1% downtime
            credit_pct += sla_tier['credit_rate'] * 2  # Double credit for major outage
        else:
            credit_pct += sla_tier['credit_rate']
    
    # Response time SLA breach
    if avg_response_time_ms > sla_tier['response_time_sla']:
        excess_ms = avg_response_time_ms - sla_tier['response_time_sla']
        if excess_ms > 1000:  # >1s over SLA
            credit_pct += sla_tier['credit_rate']
    
    return min(credit_pct, 1.0)  # Cap at 100% credit

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)
    
    # Start background SLA monitoring
    asyncio.create_task(sla_monitoring_task())

async def sla_monitoring_task():
    """Background task for SLA monitoring"""
    while True:
        try:
            await check_service_health()
            await calculate_daily_sla_metrics()
            await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            print(f"SLA monitoring error: {e}")
            await asyncio.sleep(60)

async def check_service_health():
    """Check health of all services"""
    services = [
        ("lead_ingest", "http://lead_ingest:8000/health"),
        ("lead_router", "http://lead_router:8000/health"),
        ("voice_hub", "http://voice_hub:8000/health"),
        ("marketplace", "http://marketplace:8000/health"),
        ("analytics_api", "http://analytics_api:8000/health")
    ]
    
    import httpx
    
    for service_name, health_url in services:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = datetime.now()
                response = await client.get(health_url)
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                is_healthy = response.status_code == 200
                
                # Record health check
                await app.state.db.execute("""
                    INSERT INTO service_health_checks (
                        service_name, is_healthy, response_time_ms, checked_at
                    ) VALUES ($1, $2, $3, now())
                """, service_name, is_healthy, int(response_time))
                
                # Update Prometheus metrics
                UPTIME_PERCENTAGE.labels(service=service_name).set(
                    100.0 if is_healthy else 0.0
                )
                RESPONSE_TIME_MS.labels(service=service_name).set(response_time)
                
        except Exception as e:
            # Service is down
            await app.state.db.execute("""
                INSERT INTO service_health_checks (
                    service_name, is_healthy, response_time_ms, error_message, checked_at
                ) VALUES ($1, false, 0, $2, now())
            """, service_name, str(e))
            
            UPTIME_PERCENTAGE.labels(service=service_name).set(0.0)

async def calculate_daily_sla_metrics():
    """Calculate daily SLA metrics for all tenants"""
    # Get tenants with SLA agreements
    tenants = await app.state.db.fetch("""
        SELECT * FROM tenant_sla_agreements WHERE active = true
    """)
    
    for tenant in tenants:
        tenant_id = tenant['tenant_id']
        sla_tier = SLA_TIERS.get(tenant['sla_tier'], SLA_TIERS['basic'])
        
        # Calculate yesterday's metrics (full day)
        yesterday = datetime.now() - timedelta(days=1)
        start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get service health for tenant's primary service
        health_stats = await app.state.db.fetchrow("""
            SELECT 
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE is_healthy = true) as healthy_checks,
                AVG(response_time_ms) as avg_response_time
            FROM service_health_checks 
            WHERE service_name = 'lead_ingest'
            AND checked_at BETWEEN $1 AND $2
        """, start_of_day, end_of_day)
        
        if health_stats['total_checks'] > 0:
            uptime_pct = (health_stats['healthy_checks'] / health_stats['total_checks']) * 100
            avg_response_time = health_stats['avg_response_time'] or 0
            
            # Calculate SLA credits
            credit_pct = calculate_sla_credits(sla_tier, uptime_pct, avg_response_time)
            credit_amount_cents = int(tenant['monthly_fee_cents'] * credit_pct)
            
            # Record daily SLA metrics
            await app.state.db.execute("""
                INSERT INTO sla_daily_metrics (
                    tenant_id, date, uptime_percentage, avg_response_time_ms,
                    sla_tier, credit_percentage, credit_amount_cents
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (tenant_id, date) 
                DO UPDATE SET 
                    uptime_percentage = EXCLUDED.uptime_percentage,
                    avg_response_time_ms = EXCLUDED.avg_response_time_ms,
                    credit_percentage = EXCLUDED.credit_percentage,
                    credit_amount_cents = EXCLUDED.credit_amount_cents
            """, tenant_id, start_of_day.date(), uptime_pct, avg_response_time,
                tenant['sla_tier'], credit_pct, credit_amount_cents)
            
            # Track SLA violations
            if credit_pct > 0:
                SLA_VIOLATIONS.labels(service="lead_ingest", tier=tenant['sla_tier']).inc()

@app.get("/health")
async def health():
    return {"ok": True, "service": "status_page"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Public Status Page
@app.get("/", response_class=HTMLResponse)
async def status_page():
    """Public status page"""
    
    # Get current service status
    services = await app.state.db.fetch("""
        SELECT DISTINCT ON (service_name) 
            service_name, is_healthy, response_time_ms, checked_at
        FROM service_health_checks 
        ORDER BY service_name, checked_at DESC
    """)
    
    # Get recent incidents
    incidents = await app.state.db.fetch("""
        SELECT * FROM status_incidents 
        WHERE status != 'resolved' OR created_at >= NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    # Calculate overall system status
    healthy_services = sum(1 for s in services if s['is_healthy'])
    total_services = len(services)
    
    if healthy_services == total_services:
        overall_status = "operational"
        status_color = "#28a745"
    elif healthy_services == 0:
        overall_status = "major_outage"
        status_color = "#dc3545"
    else:
        overall_status = "partial_outage"
        status_color = "#ffc107"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sincor Status</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                margin: 0; padding: 0; background: #f8f9fa;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .status-badge {{
                display: inline-block; padding: 8px 16px; border-radius: 20px;
                color: white; font-weight: bold; font-size: 14px;
                background: {status_color};
            }}
            .service-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
            .service-card {{
                background: white; border-radius: 10px; padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .service-status {{ display: flex; justify-content: space-between; align-items: center; }}
            .healthy {{ color: #28a745; }}
            .unhealthy {{ color: #dc3545; }}
            .incident-card {{
                background: #fff3cd; border-left: 4px solid #ffc107;
                padding: 15px; margin: 10px 0; border-radius: 5px;
            }}
            .resolved {{ background: #d1ecf1; border-color: #bee5eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Sincor System Status</h1>
                <div class="status-badge">{overall_status.replace('_', ' ').title()}</div>
                <p>Real-time status of our lead generation platform</p>
            </div>
            
            <div class="service-grid">
    """
    
    # Service status cards
    for service in services:
        status_class = "healthy" if service['is_healthy'] else "unhealthy"
        status_text = "Operational" if service['is_healthy'] else "Down"
        response_time = f"{service['response_time_ms']:.0f}ms" if service['response_time_ms'] else "N/A"
        
        html += f"""
                <div class="service-card">
                    <div class="service-status">
                        <div>
                            <h3>{service['service_name'].replace('_', ' ').title()}</h3>
                            <span class="{status_class}">{status_text}</span>
                        </div>
                        <div>
                            <small>Response: {response_time}</small>
                        </div>
                    </div>
                </div>
        """
    
    html += """
            </div>
            
            <h2>Recent Incidents</h2>
    """
    
    # Recent incidents
    if incidents:
        for incident in incidents:
            resolved_class = "resolved" if incident['status'] == 'resolved' else ""
            html += f"""
            <div class="incident-card {resolved_class}">
                <h4>{incident['title']}</h4>
                <p>{incident['description']}</p>
                <small>Status: {incident['status']} | Updated: {incident['updated_at'].strftime('%Y-%m-%d %H:%M UTC')}</small>
            </div>
            """
    else:
        html += "<p>No recent incidents to report.</p>"
    
    html += f"""
            
            <div style="text-align: center; margin-top: 40px; color: #666;">
                <small>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Auto-refresh every 60s</small>
            </div>
        </div>
        
        <script>
            setTimeout(() => window.location.reload(), 60000); // Auto-refresh
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

# Incident Management
@app.post("/incidents", dependencies=[Depends(verify_admin)])
async def create_incident(incident: SLAIncident):
    """Create new incident (admin only)"""
    
    incident_id = await app.state.db.fetchval("""
        INSERT INTO status_incidents (
            title, description, service, severity, status
        ) VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """, incident.title, incident.description, incident.service,
        incident.severity, incident.status)
    
    return {
        "incident_id": str(incident_id),
        "title": incident.title,
        "status": incident.status,
        "created_at": datetime.now().isoformat()
    }

@app.put("/incidents/{incident_id}", dependencies=[Depends(verify_admin)])
async def update_incident(incident_id: str, status: str, update_message: str = ""):
    """Update incident status (admin only)"""
    
    await app.state.db.execute("""
        UPDATE status_incidents 
        SET status = $2, updated_at = now()
        WHERE id = $1
    """, incident_id, status)
    
    # Add incident update
    if update_message:
        await app.state.db.execute("""
            INSERT INTO incident_updates (incident_id, message, created_at)
            VALUES ($1, $2, now())
        """, incident_id, update_message)
    
    return {"incident_id": incident_id, "status": status}

# SLA Management
@app.post("/sla/agreements", dependencies=[Depends(verify_admin)])
async def create_sla_agreement(agreement: TenantSLA):
    """Create SLA agreement for tenant"""
    
    await app.state.db.execute("""
        INSERT INTO tenant_sla_agreements (
            tenant_id, sla_tier, start_date, monthly_fee_cents, active
        ) VALUES ($1, $2, $3, $4, true)
        ON CONFLICT (tenant_id) 
        DO UPDATE SET 
            sla_tier = EXCLUDED.sla_tier,
            monthly_fee_cents = EXCLUDED.monthly_fee_cents,
            updated_at = now()
    """, agreement.tenant_id, agreement.sla_tier, agreement.start_date,
        agreement.monthly_fee_cents)
    
    return {
        "tenant_id": agreement.tenant_id,
        "sla_tier": agreement.sla_tier,
        "status": "active"
    }

@app.get("/sla/credits/{tenant_id}")
async def get_sla_credits(tenant_id: str):
    """Get SLA credits for tenant"""
    
    # Get current month's credits
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    credits = await app.state.db.fetchrow("""
        SELECT 
            SUM(credit_amount_cents) as total_credits_cents,
            COUNT(*) as violation_days,
            AVG(uptime_percentage) as avg_uptime
        FROM sla_daily_metrics 
        WHERE tenant_id = $1 AND date >= $2
    """, tenant_id, current_month)
    
    # Get SLA agreement
    agreement = await app.state.db.fetchrow("""
        SELECT * FROM tenant_sla_agreements WHERE tenant_id = $1 AND active = true
    """, tenant_id)
    
    if not agreement:
        raise HTTPException(status_code=404, detail="No active SLA agreement")
    
    sla_tier = SLA_TIERS.get(agreement['sla_tier'], SLA_TIERS['basic'])
    
    return {
        "tenant_id": tenant_id,
        "sla_tier": agreement['sla_tier'],
        "current_month": {
            "total_credits_cents": credits['total_credits_cents'] or 0,
            "violation_days": credits['violation_days'] or 0,
            "avg_uptime_percentage": round(credits['avg_uptime'] or 100, 2),
            "sla_target": sla_tier['uptime_sla']
        },
        "monthly_fee_cents": agreement['monthly_fee_cents']
    }

@app.get("/sla/tiers")
async def get_sla_tiers():
    """Get available SLA tiers"""
    
    return {
        "tiers": [
            {
                "tier_id": tier_id,
                **tier_config
            } for tier_id, tier_config in SLA_TIERS.items()
        ]
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint for monitoring"""
    
    services = await app.state.db.fetch("""
        SELECT DISTINCT ON (service_name) 
            service_name, is_healthy, response_time_ms, checked_at
        FROM service_health_checks 
        ORDER BY service_name, checked_at DESC
    """)
    
    return {
        "status": "operational" if all(s['is_healthy'] for s in services) else "degraded",
        "services": [
            {
                "name": s['service_name'],
                "status": "operational" if s['is_healthy'] else "down",
                "response_time_ms": s['response_time_ms'],
                "last_check": s['checked_at'].isoformat()
            } for s in services
        ],
        "timestamp": datetime.now().isoformat()
    }