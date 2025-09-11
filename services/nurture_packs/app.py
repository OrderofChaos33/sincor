from fastapi import FastAPI, HTTPException, Response, Depends, Header, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
import asyncpg
import os
import json
import zipfile
import tempfile
from typing import Optional, List, Dict, Any
from datetime import datetime
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
ADMIN_API_KEY = os.getenv("NURTURE_ADMIN_KEY", "admin-dev-key")

# Metrics
PACK_INSTALLS = Counter("nurture_pack_installs_total", "Pack installations", ["vertical", "pack_type"])
PACK_PURCHASES = Counter("nurture_pack_purchases_total", "Pack purchases", ["vertical"])

class NurturePack(BaseModel):
    title: str
    description: str
    vertical: str
    price_cents: int
    pack_type: str  # email_sequence, sms_campaign, ad_creatives, scripts
    components: Dict[str, Any]  # Templates, sequences, assets
    
class PackInstallRequest(BaseModel):
    pack_id: str
    tenant_id: str
    customizations: Optional[Dict[str, Any]] = {}

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)

@app.get("/health")
async def health():
    return {"ok": True, "service": "nurture_packs"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Pack Creation (Admin)
@app.post("/packs", dependencies=[Depends(verify_admin)])
async def create_nurture_pack(
    title: str = Form(...),
    description: str = Form(...), 
    vertical: str = Form(...),
    price_cents: int = Form(...),
    pack_type: str = Form(...),
    pack_file: UploadFile = File(...)
):
    """Create a new nurture pack (admin only)"""
    
    # Validate pack type
    valid_types = ['email_sequence', 'sms_campaign', 'ad_creatives', 'scripts', 'full_funnel']
    if pack_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid pack type. Must be one of: {valid_types}")
    
    try:
        # Read and parse pack file (ZIP with JSON manifest)
        pack_content = await pack_file.read()
        
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(pack_content)
            temp_file.flush()
            
            with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                # Extract manifest
                manifest = json.loads(zip_ref.read('manifest.json'))
                
                # Store components
                components = {}
                for file_info in zip_ref.filelist:
                    if file_info.filename != 'manifest.json':
                        components[file_info.filename] = zip_ref.read(file_info.filename).decode('utf-8')
        
        # Merge manifest with components
        pack_data = {
            **manifest,
            "files": components
        }
        
        # Insert pack into database
        pack_id = await app.state.db.fetchval("""
            INSERT INTO nurture_packs (title, description, vertical, price_cents, pack_type, components, active)
            VALUES ($1, $2, $3, $4, $5, $6, true)
            RETURNING id
        """, title, description, vertical, price_cents, pack_type, pack_data)
        
        return {
            "pack_id": str(pack_id),
            "title": title,
            "vertical": vertical,
            "pack_type": pack_type,
            "components_count": len(components),
            "status": "created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create pack: {str(e)}")

# Public Pack Catalog
@app.get("/catalog")
async def browse_packs(
    vertical: Optional[str] = None,
    pack_type: Optional[str] = None,
    limit: int = 20
):
    """Browse available nurture packs"""
    
    query = """
        SELECT np.*, 
               (SELECT COUNT(*) FROM pack_installs pi WHERE pi.pack_id = np.id) as install_count,
               (SELECT AVG(rating) FROM pack_reviews pr WHERE pr.pack_id = np.id) as avg_rating
        FROM nurture_packs np 
        WHERE np.active = true
    """
    params = []
    
    if vertical:
        params.append(vertical)
        query += f" AND np.vertical = ${len(params)}"
        
    if pack_type:
        params.append(pack_type)
        query += f" AND np.pack_type = ${len(params)}"
    
    query += " ORDER BY install_count DESC, np.created_at DESC"
    params.append(limit)
    query += f" LIMIT ${len(params)}"
    
    rows = await app.state.db.fetch(query, *params)
    
    packs = []
    for row in rows:
        # Get component summary without exposing full content
        components = row['components'] or {}
        component_summary = {
            "email_templates": len([k for k in components.get('files', {}) if k.endswith('.html')]),
            "sms_templates": len([k for k in components.get('files', {}) if 'sms' in k.lower()]),
            "ad_creatives": len([k for k in components.get('files', {}) if k.endswith(('.jpg', '.png', '.gif'))]),
            "scripts": len([k for k in components.get('files', {}) if k.endswith('.txt')])
        }
        
        packs.append({
            "id": str(row['id']),
            "title": row['title'],
            "description": row['description'],
            "vertical": row['vertical'],
            "pack_type": row['pack_type'],
            "price_cents": row['price_cents'],
            "install_count": row['install_count'],
            "avg_rating": float(row['avg_rating']) if row['avg_rating'] else 0.0,
            "components": component_summary,
            "preview": components.get('preview', 'No preview available')
        })
    
    return {"packs": packs, "count": len(packs)}

@app.get("/packs/{pack_id}")
async def get_pack_details(pack_id: str):
    """Get detailed pack information"""
    
    pack = await app.state.db.fetchrow("""
        SELECT np.*,
               (SELECT COUNT(*) FROM pack_installs pi WHERE pi.pack_id = np.id) as install_count
        FROM nurture_packs np 
        WHERE np.id = $1 AND np.active = true
    """, pack_id)
    
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    # Get recent reviews
    reviews = await app.state.db.fetch("""
        SELECT rating, review_text, tenant_id, created_at
        FROM pack_reviews 
        WHERE pack_id = $1
        ORDER BY created_at DESC 
        LIMIT 5
    """, pack_id)
    
    components = pack['components'] or {}
    
    return {
        "id": str(pack['id']),
        "title": pack['title'],
        "description": pack['description'],
        "vertical": pack['vertical'],
        "pack_type": pack['pack_type'],
        "price_cents": pack['price_cents'],
        "install_count": pack['install_count'],
        "components_preview": {
            k: v[:200] + "..." if len(str(v)) > 200 else v
            for k, v in components.items() if k != 'files'
        },
        "reviews": [
            {
                "rating": r['rating'],
                "text": r['review_text'][:200] + "..." if len(r['review_text']) > 200 else r['review_text'],
                "tenant_id": r['tenant_id'],
                "created_at": r['created_at'].isoformat()
            } for r in reviews
        ]
    }

# Pack Purchase & Installation
@app.post("/purchase/{pack_id}")
async def purchase_pack(pack_id: str, tenant_id: str):
    """Purchase a nurture pack"""
    
    # Get pack details
    pack = await app.state.db.fetchrow(
        "SELECT * FROM nurture_packs WHERE id = $1 AND active = true",
        pack_id
    )
    
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    # Check if already purchased
    existing = await app.state.db.fetchval("""
        SELECT id FROM pack_purchases 
        WHERE pack_id = $1 AND tenant_id = $2 AND status = 'completed'
    """, pack_id, tenant_id)
    
    if existing:
        raise HTTPException(status_code=409, detail="Pack already purchased")
    
    # Create purchase record (integrate with payment system)
    purchase_id = await app.state.db.fetchval("""
        INSERT INTO pack_purchases (pack_id, tenant_id, amount_cents, status)
        VALUES ($1, $2, $3, 'completed')
        RETURNING id
    """, pack_id, tenant_id, pack['price_cents'])
    
    PACK_PURCHASES.labels(vertical=pack['vertical']).inc()
    
    return {
        "purchase_id": str(purchase_id),
        "pack_id": pack_id,
        "status": "purchased",
        "install_url": f"/install/{pack_id}?tenant_id={tenant_id}"
    }

@app.post("/install/{pack_id}")
async def install_pack(pack_id: str, install_request: PackInstallRequest):
    """Install purchased pack to tenant's MediaPax system"""
    
    # Verify purchase
    purchase = await app.state.db.fetchrow("""
        SELECT pp.*, np.components, np.pack_type, np.vertical
        FROM pack_purchases pp
        JOIN nurture_packs np ON pp.pack_id = np.id
        WHERE pp.pack_id = $1 AND pp.tenant_id = $2 AND pp.status = 'completed'
    """, pack_id, install_request.tenant_id)
    
    if not purchase:
        raise HTTPException(status_code=403, detail="Pack not purchased or invalid tenant")
    
    try:
        # Get pack components
        components = purchase['components'] or {}
        files = components.get('files', {})
        
        # Install based on pack type
        if purchase['pack_type'] == 'email_sequence':
            await install_email_sequence(install_request.tenant_id, files, install_request.customizations)
        elif purchase['pack_type'] == 'sms_campaign':
            await install_sms_campaign(install_request.tenant_id, files, install_request.customizations)
        elif purchase['pack_type'] == 'ad_creatives':
            await install_ad_creatives(install_request.tenant_id, files, install_request.customizations)
        elif purchase['pack_type'] == 'full_funnel':
            await install_full_funnel(install_request.tenant_id, files, install_request.customizations)
        
        # Record installation
        install_id = await app.state.db.fetchval("""
            INSERT INTO pack_installs (pack_id, tenant_id, customizations, status)
            VALUES ($1, $2, $3, 'completed')
            RETURNING id
        """, pack_id, install_request.tenant_id, install_request.customizations)
        
        PACK_INSTALLS.labels(vertical=purchase['vertical'], pack_type=purchase['pack_type']).inc()
        
        return {
            "install_id": str(install_id),
            "pack_id": pack_id,
            "tenant_id": install_request.tenant_id,
            "status": "installed",
            "components_installed": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Installation failed: {str(e)}")

async def install_email_sequence(tenant_id: str, files: Dict, customizations: Dict):
    """Install email sequence templates"""
    
    # Create email campaign templates
    for filename, content in files.items():
        if filename.endswith('.html'):
            template_name = filename.replace('.html', '').replace('_', ' ').title()
            
            # Apply customizations
            customized_content = content
            for key, value in customizations.items():
                customized_content = customized_content.replace(f"{{{{{key}}}}}", str(value))
            
            # Insert into templates table (adjust based on your schema)
            await app.state.db.execute("""
                INSERT INTO email_templates (tenant_id, name, subject, html_content, template_type)
                VALUES ($1, $2, $3, $4, 'nurture_sequence')
                ON CONFLICT (tenant_id, name) 
                DO UPDATE SET html_content = EXCLUDED.html_content
            """, tenant_id, template_name, f"[{template_name}]", customized_content)

async def install_sms_campaign(tenant_id: str, files: Dict, customizations: Dict):
    """Install SMS campaign templates"""
    
    for filename, content in files.items():
        if 'sms' in filename.lower():
            template_name = filename.replace('.txt', '').replace('_', ' ').title()
            
            # Apply customizations
            customized_content = content
            for key, value in customizations.items():
                customized_content = customized_content.replace(f"{{{{{key}}}}}", str(value))
            
            await app.state.db.execute("""
                INSERT INTO sms_templates (tenant_id, name, message_content, template_type)
                VALUES ($1, $2, $3, 'nurture_campaign')
                ON CONFLICT (tenant_id, name)
                DO UPDATE SET message_content = EXCLUDED.message_content
            """, tenant_id, template_name, customized_content)

async def install_ad_creatives(tenant_id: str, files: Dict, customizations: Dict):
    """Install ad creative assets"""
    
    # Store creative assets (implement file storage as needed)
    for filename, content in files.items():
        if filename.endswith(('.jpg', '.png', '.gif', '.mp4')):
            await app.state.db.execute("""
                INSERT INTO creative_assets (tenant_id, filename, asset_type, content)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, filename)
                DO UPDATE SET content = EXCLUDED.content
            """, tenant_id, filename, 'ad_creative', content)

async def install_full_funnel(tenant_id: str, files: Dict, customizations: Dict):
    """Install complete funnel (emails + SMS + ads + scripts)"""
    await install_email_sequence(tenant_id, files, customizations)
    await install_sms_campaign(tenant_id, files, customizations)
    await install_ad_creatives(tenant_id, files, customizations)

@app.get("/my_packs/{tenant_id}")
async def get_installed_packs(tenant_id: str):
    """Get tenant's installed packs"""
    
    installs = await app.state.db.fetch("""
        SELECT pi.*, np.title, np.pack_type, np.vertical
        FROM pack_installs pi
        JOIN nurture_packs np ON pi.pack_id = np.id
        WHERE pi.tenant_id = $1 AND pi.status = 'completed'
        ORDER BY pi.created_at DESC
    """, tenant_id)
    
    return {
        "tenant_id": tenant_id,
        "installed_packs": [
            {
                "pack_id": str(install['pack_id']),
                "title": install['title'],
                "pack_type": install['pack_type'],
                "vertical": install['vertical'],
                "installed_at": install['created_at'].isoformat(),
                "customizations": install['customizations']
            } for install in installs
        ],
        "total_installed": len(installs)
    }

@app.get("/stats")
async def get_pack_stats():
    """Get nurture pack statistics"""
    
    stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_packs,
            COUNT(*) FILTER (WHERE active = true) as active_packs,
            (SELECT COUNT(*) FROM pack_purchases WHERE status = 'completed') as total_sales,
            (SELECT SUM(amount_cents) FROM pack_purchases WHERE status = 'completed') as total_revenue_cents,
            (SELECT COUNT(*) FROM pack_installs WHERE status = 'completed') as total_installs
        FROM nurture_packs
    """)
    
    # Top selling verticals
    vertical_stats = await app.state.db.fetch("""
        SELECT 
            np.vertical,
            COUNT(pp.*) as sales_count,
            SUM(pp.amount_cents) as revenue_cents
        FROM pack_purchases pp
        JOIN nurture_packs np ON pp.pack_id = np.id
        WHERE pp.status = 'completed'
        GROUP BY np.vertical
        ORDER BY sales_count DESC
        LIMIT 5
    """)
    
    return {
        "total_packs": stats['total_packs'],
        "active_packs": stats['active_packs'], 
        "total_sales": stats['total_sales'],
        "total_revenue_cents": stats['total_revenue_cents'],
        "total_installs": stats['total_installs'],
        "top_verticals": [
            {
                "vertical": vs['vertical'],
                "sales_count": vs['sales_count'],
                "revenue_cents": vs['revenue_cents']
            } for vs in vertical_stats
        ]
    }