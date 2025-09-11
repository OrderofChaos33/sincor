from fastapi import FastAPI, HTTPException, Response, Depends, Header, Request
from pydantic import BaseModel, EmailStr
import asyncpg
import os
import jwt
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import aioredis
from passlib.context import CryptContext

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
JWT_SECRET = os.getenv("JWT_SECRET", "tenant-jwt-secret")
ADMIN_API_KEY = os.getenv("TENANT_ADMIN_KEY", "admin-dev-key")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Metrics
TENANT_REQUESTS = Counter("tenant_gateway_requests_total", "Tenant gateway requests", ["tenant", "endpoint"])
TENANT_LOGINS = Counter("tenant_logins_total", "Tenant login attempts", ["tenant", "success"])

class TenantRegistration(BaseModel):
    tenant_name: str
    admin_email: EmailStr
    password: str
    plan: Optional[str] = "starter"
    custom_domain: Optional[str] = None
    branding: Optional[Dict[str, Any]] = {}

class TenantLogin(BaseModel):
    tenant_name: str
    email: EmailStr
    password: str

class TenantConfigUpdate(BaseModel):
    branding: Optional[Dict[str, Any]] = None
    domain_settings: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, bool]] = None

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)

async def verify_admin(authorization: str = Header(None)):
    """Verify admin API key"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

async def extract_tenant(request: Request) -> str:
    """Extract tenant from request (subdomain or JWT)"""
    # Check for custom domain mapping first
    host = request.headers.get("host", "").lower()
    
    # Check database for custom domain mapping
    tenant_from_domain = await app.state.db.fetchval(
        "SELECT tenant_name FROM tenants WHERE custom_domain = $1 AND active = true",
        host
    )
    
    if tenant_from_domain:
        return tenant_from_domain
    
    # Extract from subdomain
    if "." in host:
        subdomain = host.split(".")[0]
        # Verify subdomain exists as tenant
        tenant_exists = await app.state.db.fetchval(
            "SELECT tenant_name FROM tenants WHERE tenant_name = $1 AND active = true",
            subdomain
        )
        if tenant_exists:
            return subdomain
    
    # Fallback to JWT token
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            token = auth.split(" ")[1]
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload.get("tenant")
        except jwt.InvalidTokenError:
            pass
    
    raise HTTPException(status_code=400, detail="Tenant not identified")

async def verify_tenant_access(request: Request, tenant: str = Depends(extract_tenant)):
    """Verify tenant access and return config"""
    TENANT_REQUESTS.labels(tenant=tenant, endpoint=request.url.path).inc()
    
    config = await app.state.db.fetchrow(
        "SELECT * FROM tenants WHERE tenant_name = $1 AND active = true",
        tenant
    )
    
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {"tenant": tenant, "config": dict(config)}

@app.get("/health")
async def health():
    return {"ok": True, "service": "tenant_gateway"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Tenant Management
@app.post("/tenants/register")
async def register_tenant(registration: TenantRegistration):
    """Register new tenant (public endpoint)"""
    try:
        # Check if tenant already exists
        existing = await app.state.db.fetchval(
            "SELECT tenant_name FROM tenants WHERE tenant_name = $1",
            registration.tenant_name
        )
        
        if existing:
            raise HTTPException(status_code=409, detail="Tenant already exists")
        
        # Hash password
        hashed_password = pwd_context.hash(registration.password)
        
        # Create tenant
        tenant_id = await app.state.db.fetchval("""
            INSERT INTO tenants (
                tenant_name, admin_email, admin_password_hash, plan, 
                custom_domain, branding, active
            )
            VALUES ($1, $2, $3, $4, $5, $6, true)
            RETURNING id
        """, registration.tenant_name, registration.admin_email, hashed_password,
            registration.plan, registration.custom_domain, registration.branding)
        
        # Generate JWT token
        token_payload = {
            "tenant": registration.tenant_name,
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(days=30)
        }
        
        token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
        
        return {
            "tenant_id": str(tenant_id),
            "tenant_name": registration.tenant_name,
            "access_token": token,
            "subdomain_url": f"https://{registration.tenant_name}.sincor.app",
            "status": "registered"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@app.post("/tenants/login")
async def tenant_login(login: TenantLogin):
    """Tenant admin login"""
    try:
        tenant = await app.state.db.fetchrow(
            "SELECT * FROM tenants WHERE tenant_name = $1 AND admin_email = $2",
            login.tenant_name, login.email
        )
        
        if not tenant or not pwd_context.verify(login.password, tenant["admin_password_hash"]):
            TENANT_LOGINS.labels(tenant=login.tenant_name, success="false").inc()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not tenant["active"]:
            raise HTTPException(status_code=403, detail="Tenant suspended")
        
        # Generate JWT
        token_payload = {
            "tenant": login.tenant_name,
            "role": "admin", 
            "exp": datetime.utcnow() + timedelta(days=30)
        }
        
        token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
        
        TENANT_LOGINS.labels(tenant=login.tenant_name, success="true").inc()
        
        return {
            "access_token": token,
            "tenant_name": login.tenant_name,
            "role": "admin",
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")

@app.get("/tenants/config")
async def get_tenant_config(tenant_info = Depends(verify_tenant_access)):
    """Get tenant configuration"""
    config = tenant_info["config"]
    
    # Remove sensitive data
    safe_config = {
        "tenant_name": config["tenant_name"],
        "plan": config["plan"],
        "custom_domain": config["custom_domain"],
        "branding": config["branding"],
        "feature_flags": config["feature_flags"],
        "created_at": config["created_at"].isoformat(),
        "api_endpoints": {
            "leads": f"https://{config['tenant_name']}.sincor.app/api/leads",
            "bookings": f"https://{config['tenant_name']}.sincor.app/api/bookings",
            "analytics": f"https://{config['tenant_name']}.sincor.app/api/analytics"
        }
    }
    
    return safe_config

@app.put("/tenants/config")
async def update_tenant_config(
    updates: TenantConfigUpdate,
    tenant_info = Depends(verify_tenant_access)
):
    """Update tenant configuration"""
    tenant = tenant_info["tenant"]
    
    # Build update query dynamically
    update_fields = []
    params = []
    
    if updates.branding is not None:
        update_fields.append(f"branding = ${len(params) + 1}")
        params.append(updates.branding)
        
    if updates.domain_settings is not None:
        update_fields.append(f"domain_settings = ${len(params) + 1}")
        params.append(updates.domain_settings)
        
    if updates.feature_flags is not None:
        update_fields.append(f"feature_flags = ${len(params) + 1}")
        params.append(updates.feature_flags)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(tenant)
    update_query = f"""
        UPDATE tenants 
        SET {', '.join(update_fields)}, updated_at = NOW()
        WHERE tenant_name = ${len(params)}
    """
    
    await app.state.db.execute(update_query, *params)
    
    return {"tenant": tenant, "status": "updated"}

# Tenant Data Isolation
@app.get("/tenants/stats")
async def get_tenant_stats(tenant_info = Depends(verify_tenant_access)):
    """Get tenant-specific usage statistics"""
    tenant = tenant_info["tenant"]
    
    # Lead stats
    leads_stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_leads,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as leads_30d,
            COUNT(*) FILTER (WHERE status = 'delivered') as delivered_leads
        FROM leads 
        WHERE vertical = $1
    """, tenant)
    
    # Booking stats  
    booking_stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_bookings,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as bookings_30d,
            COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed_bookings
        FROM appointments 
        WHERE tenant_id = $1
    """, tenant)
    
    # Revenue stats
    revenue_stats = await app.state.db.fetchrow("""
        SELECT 
            COALESCE(SUM(amount_cents), 0) as total_revenue_cents,
            COALESCE(SUM(amount_cents) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days'), 0) as revenue_30d_cents,
            COUNT(*) as total_transactions
        FROM purchases 
        WHERE tenant_id = $1 AND status = 'completed'
    """, tenant)
    
    return {
        "tenant": tenant,
        "leads": {
            "total": leads_stats["total_leads"],
            "last_30_days": leads_stats["leads_30d"], 
            "delivered": leads_stats["delivered_leads"],
            "conversion_rate": round(leads_stats["delivered_leads"] / max(leads_stats["total_leads"], 1) * 100, 2)
        },
        "bookings": {
            "total": booking_stats["total_bookings"],
            "last_30_days": booking_stats["bookings_30d"],
            "confirmed": booking_stats["confirmed_bookings"]
        },
        "revenue": {
            "total_cents": revenue_stats["total_revenue_cents"],
            "last_30_days_cents": revenue_stats["revenue_30d_cents"],
            "total_transactions": revenue_stats["total_transactions"]
        }
    }

# Tenant API Proxying
@app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_service(
    service_name: str,
    path: str,
    request: Request,
    tenant_info = Depends(verify_tenant_access)
):
    """Proxy API requests to tenant-scoped services"""
    tenant = tenant_info["tenant"]
    
    # Service mapping
    service_map = {
        "leads": "http://lead_ingest:8000",
        "router": "http://lead_router:8000", 
        "bookings": "http://booking_core:8000",
        "analytics": "http://analytics_api:8000",
        "marketplace": "http://marketplace:8000",
        "voice": "http://voice_hub:8000"
    }
    
    if service_name not in service_map:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Add tenant context to headers
    headers = dict(request.headers)
    headers["x-tenant-id"] = tenant
    headers["x-tenant-config"] = json.dumps(tenant_info["config"])
    
    # Forward request (simplified - in production use httpx)
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{service_map[service_name]}/{path}",
            headers=headers,
            content=await request.body(),
            params=request.query_params
        )
    
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

# Admin endpoints
@app.get("/admin/tenants", dependencies=[Depends(verify_admin)])
async def list_all_tenants():
    """List all tenants (admin only)"""
    tenants = await app.state.db.fetch("""
        SELECT tenant_name, admin_email, plan, active, created_at,
               (SELECT COUNT(*) FROM leads WHERE vertical = tenant_name) as lead_count
        FROM tenants 
        ORDER BY created_at DESC
    """)
    
    return {
        "tenants": [
            {
                "tenant_name": t["tenant_name"],
                "admin_email": t["admin_email"],
                "plan": t["plan"],
                "active": t["active"],
                "lead_count": t["lead_count"],
                "created_at": t["created_at"].isoformat()
            } for t in tenants
        ],
        "total_count": len(tenants)
    }

@app.put("/admin/tenants/{tenant_name}/suspend", dependencies=[Depends(verify_admin)])
async def suspend_tenant(tenant_name: str):
    """Suspend tenant (admin only)"""
    await app.state.db.execute(
        "UPDATE tenants SET active = false WHERE tenant_name = $1",
        tenant_name
    )
    return {"tenant": tenant_name, "status": "suspended"}