from fastapi import FastAPI, HTTPException, Response, Depends, Header, UploadFile, File
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import csv
import io
from typing import Optional, List, Set
from datetime import datetime, timedelta
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("SUPPRESSION_ADMIN_KEY", "admin-dev-key")

# Metrics
SUPPRESSION_CHECKS = Counter("suppression_checks_total", "Suppression checks", ["result"])
DNC_UPLOADS = Counter("dnc_uploads_total", "DNC list uploads", ["source"])

class SuppressionEntry(BaseModel):
    contact: str  # email or phone
    type: str  # email, phone, sms
    reason: Optional[str] = "manual"
    expires_at: Optional[datetime] = None

class BulkSuppressionRequest(BaseModel):
    entries: List[SuppressionEntry]
    source: Optional[str] = "api"

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

async def extract_tenant(request) -> str:
    """Extract tenant from API key or default to global"""
    return "global"  # For now, global suppression

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)

@app.get("/health")
async def health():
    return {"ok": True, "service": "suppression_graph"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/suppress")
async def add_suppression(entry: SuppressionEntry, tenant: str = Depends(extract_tenant)):
    """Add a contact to suppression list"""
    # Normalize contact
    contact = entry.contact.lower().strip()
    
    # Insert or update suppression entry
    await app.state.db.execute("""
        INSERT INTO suppressions (tenant_id, contact, contact_type, reason, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (tenant_id, contact, contact_type)
        DO UPDATE SET 
            reason = EXCLUDED.reason,
            expires_at = EXCLUDED.expires_at,
            updated_at = now()
    """, tenant, contact, entry.type, entry.reason, entry.expires_at)
    
    # Cache in Redis for fast lookups (24hr TTL)
    cache_key = f"suppress:{tenant}:{entry.type}:{contact}"
    await app.state.redis.setex(cache_key, 86400, "1")
    
    return {"contact": contact, "type": entry.type, "status": "suppressed"}

@app.post("/suppress/bulk")
async def add_bulk_suppression(
    request: BulkSuppressionRequest, 
    tenant: str = Depends(extract_tenant)
):
    """Bulk add contacts to suppression list"""
    entries_added = 0
    
    # Process in batches
    batch_size = 1000
    for i in range(0, len(request.entries), batch_size):
        batch = request.entries[i:i+batch_size]
        
        # Prepare batch insert
        values = []
        cache_ops = []
        
        for entry in batch:
            contact = entry.contact.lower().strip()
            values.extend([tenant, contact, entry.type, entry.reason, entry.expires_at])
            
            # Prepare cache operations
            cache_key = f"suppress:{tenant}:{entry.type}:{contact}"
            cache_ops.append((cache_key, "1"))
        
        # Batch database insert
        placeholders = []
        for j in range(len(batch)):
            base = j * 5
            placeholders.append(f"(${base+1}, ${base+2}, ${base+3}, ${base+4}, ${base+5})")
        
        query = f"""
            INSERT INTO suppressions (tenant_id, contact, contact_type, reason, expires_at)
            VALUES {', '.join(placeholders)}
            ON CONFLICT (tenant_id, contact, contact_type)
            DO UPDATE SET 
                reason = EXCLUDED.reason,
                expires_at = EXCLUDED.expires_at,
                updated_at = now()
        """
        
        await app.state.db.execute(query, *values)
        
        # Batch cache operations
        async with app.state.redis.pipeline() as pipe:
            for cache_key, value in cache_ops:
                pipe.setex(cache_key, 86400, value)
            await pipe.execute()
        
        entries_added += len(batch)
    
    DNC_UPLOADS.labels(source=request.source).inc()
    
    return {
        "entries_processed": len(request.entries),
        "entries_added": entries_added,
        "source": request.source
    }

@app.get("/check/{contact_type}/{contact}")
async def check_suppression(
    contact_type: str, 
    contact: str,
    tenant: str = Depends(extract_tenant)
):
    """Check if a contact is suppressed"""
    contact = contact.lower().strip()
    
    # Check cache first
    cache_key = f"suppress:{tenant}:{contact_type}:{contact}"
    cached = await app.state.redis.get(cache_key)
    
    if cached:
        SUPPRESSION_CHECKS.labels(result="suppressed").inc()
        return {"contact": contact, "suppressed": True, "source": "cache"}
    
    # Check database
    row = await app.state.db.fetchrow("""
        SELECT reason, expires_at FROM suppressions 
        WHERE tenant_id = $1 AND contact = $2 AND contact_type = $3
        AND (expires_at IS NULL OR expires_at > now())
    """, tenant, contact, contact_type)
    
    if row:
        # Cache the result
        await app.state.redis.setex(cache_key, 86400, "1")
        SUPPRESSION_CHECKS.labels(result="suppressed").inc()
        
        return {
            "contact": contact,
            "suppressed": True,
            "reason": row['reason'],
            "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None,
            "source": "database"
        }
    else:
        # Cache negative result (shorter TTL)
        await app.state.redis.setex(cache_key + ":neg", 3600, "0")
        SUPPRESSION_CHECKS.labels(result="allowed").inc()
        
        return {"contact": contact, "suppressed": False, "source": "database"}

@app.post("/check/batch")
async def check_batch_suppression(
    contacts: List[str],
    contact_type: str = "email",
    tenant: str = Depends(extract_tenant)
):
    """Batch check multiple contacts"""
    results = {}
    uncached_contacts = []
    
    # Check cache first
    for contact in contacts:
        contact = contact.lower().strip()
        cache_key = f"suppress:{tenant}:{contact_type}:{contact}"
        cached = await app.state.redis.get(cache_key)
        
        if cached:
            results[contact] = {"suppressed": True, "source": "cache"}
        else:
            # Check negative cache
            neg_cached = await app.state.redis.get(cache_key + ":neg")
            if neg_cached:
                results[contact] = {"suppressed": False, "source": "cache"}
            else:
                uncached_contacts.append(contact)
    
    # Batch database lookup for uncached contacts
    if uncached_contacts:
        rows = await app.state.db.fetch("""
            SELECT contact, reason, expires_at FROM suppressions 
            WHERE tenant_id = $1 AND contact = ANY($2::text[]) AND contact_type = $3
            AND (expires_at IS NULL OR expires_at > now())
        """, tenant, uncached_contacts, contact_type)
        
        suppressed_contacts = {row['contact'] for row in rows}
        
        # Process results and update cache
        cache_ops = []
        for contact in uncached_contacts:
            if contact in suppressed_contacts:
                results[contact] = {"suppressed": True, "source": "database"}
                cache_ops.append((f"suppress:{tenant}:{contact_type}:{contact}", "1", 86400))
            else:
                results[contact] = {"suppressed": False, "source": "database"}
                cache_ops.append((f"suppress:{tenant}:{contact_type}:{contact}:neg", "0", 3600))
        
        # Batch cache update
        async with app.state.redis.pipeline() as pipe:
            for cache_key, value, ttl in cache_ops:
                pipe.setex(cache_key, ttl, value)
            await pipe.execute()
    
    # Update metrics
    suppressed_count = sum(1 for r in results.values() if r["suppressed"])
    SUPPRESSION_CHECKS.labels(result="suppressed").inc(suppressed_count)
    SUPPRESSION_CHECKS.labels(result="allowed").inc(len(contacts) - suppressed_count)
    
    return {"results": results, "total_checked": len(contacts)}

@app.post("/upload/dnc", dependencies=[Depends(verify_admin)])
async def upload_dnc_file(
    file: UploadFile = File(...),
    contact_type: str = "phone",
    source: str = "dnc_registry"
):
    """Upload DNC file (admin only)"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files supported")
    
    # Read and parse CSV
    content = await file.read()
    csv_data = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_data)
    
    # Expected columns: contact, reason (optional)
    entries = []
    for row in reader:
        contact = row.get('contact', row.get('phone', row.get('email', ''))).strip()
        if contact:
            entries.append(SuppressionEntry(
                contact=contact,
                type=contact_type,
                reason=row.get('reason', source)
            ))
    
    if not entries:
        raise HTTPException(status_code=400, detail="No valid contacts found in file")
    
    # Process bulk suppression
    result = await add_bulk_suppression(
        BulkSuppressionRequest(entries=entries, source=source),
        tenant="global"
    )
    
    return {
        "filename": file.filename,
        "contact_type": contact_type,
        "source": source,
        **result
    }

@app.delete("/suppress/{contact_type}/{contact}")
async def remove_suppression(
    contact_type: str,
    contact: str, 
    tenant: str = Depends(extract_tenant)
):
    """Remove contact from suppression list"""
    contact = contact.lower().strip()
    
    # Remove from database
    await app.state.db.execute("""
        DELETE FROM suppressions 
        WHERE tenant_id = $1 AND contact = $2 AND contact_type = $3
    """, tenant, contact, contact_type)
    
    # Remove from cache
    cache_key = f"suppress:{tenant}:{contact_type}:{contact}"
    await app.state.redis.delete(cache_key, cache_key + ":neg")
    
    return {"contact": contact, "type": contact_type, "status": "unsuppressed"}

@app.get("/export", dependencies=[Depends(verify_admin)])
async def export_suppression_list(
    contact_type: Optional[str] = None,
    tenant: Optional[str] = None,
    format: str = "csv"
):
    """Export suppression list (admin only)"""
    query = "SELECT * FROM suppressions WHERE 1=1"
    params = []
    
    if tenant:
        params.append(tenant)
        query += f" AND tenant_id = ${len(params)}"
    
    if contact_type:
        params.append(contact_type)
        query += f" AND contact_type = ${len(params)}"
    
    query += " ORDER BY created_at DESC"
    
    rows = await app.state.db.fetch(query, *params)
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["contact", "contact_type", "reason", "tenant_id", "created_at", "expires_at"])
        
        for row in rows:
            writer.writerow([
                row['contact'],
                row['contact_type'], 
                row['reason'],
                row['tenant_id'],
                row['created_at'].isoformat(),
                row['expires_at'].isoformat() if row['expires_at'] else ""
            ])
        
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=suppression_list.csv"}
        )
    else:
        return {
            "suppression_list": [
                {
                    "contact": row['contact'],
                    "contact_type": row['contact_type'],
                    "reason": row['reason'],
                    "tenant_id": row['tenant_id'],
                    "created_at": row['created_at'].isoformat(),
                    "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None
                } for row in rows
            ],
            "total_count": len(rows)
        }

@app.get("/stats")
async def get_suppression_stats(tenant: str = Depends(extract_tenant)):
    """Get suppression statistics"""
    stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_suppressions,
            COUNT(*) FILTER (WHERE contact_type = 'email') as email_suppressions,
            COUNT(*) FILTER (WHERE contact_type = 'phone') as phone_suppressions,
            COUNT(*) FILTER (WHERE contact_type = 'sms') as sms_suppressions,
            COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at > now()) as temporary_suppressions,
            COUNT(*) FILTER (WHERE created_at >= now() - INTERVAL '7 days') as recent_additions
        FROM suppressions 
        WHERE tenant_id = $1
    """, tenant)
    
    return {
        "tenant": tenant,
        "total_suppressions": stats['total_suppressions'],
        "by_type": {
            "email": stats['email_suppressions'],
            "phone": stats['phone_suppressions'],
            "sms": stats['sms_suppressions']
        },
        "temporary_suppressions": stats['temporary_suppressions'],
        "recent_additions_7d": stats['recent_additions']
    }