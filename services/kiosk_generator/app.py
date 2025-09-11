from fastapi import FastAPI, HTTPException, Response, Depends, Header, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
import hashlib
import qrcode
import base64
from io import BytesIO
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("KIOSK_ADMIN_KEY", "admin-dev-key")
BASE_URL = os.getenv("KIOSK_BASE_URL", "https://app.sincor.com")

# Metrics
QR_GENERATED = Counter("qr_codes_generated_total", "QR codes generated", ["type", "vertical"])
QR_SCANNED = Counter("qr_codes_scanned_total", "QR codes scanned", ["type", "vertical"])
KIOSK_CONVERSIONS = Counter("kiosk_conversions_total", "Kiosk conversions", ["type"])

class KioskCampaignCreate(BaseModel):
    name: str
    tenant_id: str
    vertical: str
    campaign_type: str  # book_now, gift_card, lead_capture, survey
    offer_title: str
    offer_description: str
    redirect_url: Optional[str] = None
    gift_card_value_cents: Optional[int] = None
    expiry_days: Optional[int] = 30
    customization: Optional[Dict] = {}

class QRGenerationRequest(BaseModel):
    campaign_id: str
    location: Optional[str] = None
    size: Optional[int] = 200  # QR code size in pixels
    include_logo: Optional[bool] = False

class KioskInteraction(BaseModel):
    campaign_id: str
    qr_code: str
    user_data: Dict[str, Any] = {}
    interaction_type: str  # scan, form_submit, booking, purchase

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

def generate_qr_code(data: str, size: int = 200, include_logo: bool = False) -> str:
    """Generate QR code and return as base64 encoded PNG"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize image
    img = img.resize((size, size))
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def generate_short_code(campaign_id: str, location: str = "") -> str:
    """Generate short alphanumeric code for QR"""
    data = f"{campaign_id}:{location}:{datetime.now().timestamp()}"
    hash_obj = hashlib.md5(data.encode())
    return hash_obj.hexdigest()[:8].upper()

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)

@app.get("/health")
async def health():
    return {"ok": True, "service": "kiosk_generator"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Campaign Management
@app.post("/campaigns", dependencies=[Depends(verify_admin)])
async def create_kiosk_campaign(campaign: KioskCampaignCreate):
    """Create new kiosk campaign"""
    
    campaign_id = await app.state.db.fetchval("""
        INSERT INTO kiosk_campaigns (
            name, tenant_id, vertical, campaign_type, offer_title,
            offer_description, redirect_url, gift_card_value_cents,
            expiry_days, customization, active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true)
        RETURNING id
    """, campaign.name, campaign.tenant_id, campaign.vertical, campaign.campaign_type,
        campaign.offer_title, campaign.offer_description, campaign.redirect_url,
        campaign.gift_card_value_cents, campaign.expiry_days, 
        json.dumps(campaign.customization))
    
    return {
        "campaign_id": str(campaign_id),
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "qr_generation_url": f"/qr/generate",
        "landing_page_url": f"/k/{campaign_id}"
    }

@app.get("/campaigns")
async def list_campaigns(tenant_id: Optional[str] = None):
    """List kiosk campaigns"""
    
    query = "SELECT * FROM kiosk_campaigns WHERE active = true"
    params = []
    
    if tenant_id:
        params.append(tenant_id)
        query += f" AND tenant_id = ${len(params)}"
    
    query += " ORDER BY created_at DESC"
    
    campaigns = await app.state.db.fetch(query, *params)
    
    return {
        "campaigns": [
            {
                "id": str(c['id']),
                "name": c['name'],
                "tenant_id": c['tenant_id'],
                "vertical": c['vertical'],
                "campaign_type": c['campaign_type'],
                "offer_title": c['offer_title'],
                "active": c['active'],
                "created_at": c['created_at'].isoformat(),
                "landing_url": f"{BASE_URL}/k/{c['id']}"
            } for c in campaigns
        ]
    }

# QR Code Generation
@app.post("/qr/generate")
async def generate_qr(request: QRGenerationRequest):
    """Generate QR code for kiosk campaign"""
    
    # Get campaign
    campaign = await app.state.db.fetchrow("""
        SELECT * FROM kiosk_campaigns WHERE id = $1 AND active = true
    """, request.campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Generate short code
    short_code = generate_short_code(request.campaign_id, request.location or "")
    
    # Create QR record
    qr_id = await app.state.db.fetchval("""
        INSERT INTO qr_codes (
            campaign_id, short_code, location, size, 
            include_logo, scan_count
        ) VALUES ($1, $2, $3, $4, $5, 0)
        RETURNING id
    """, request.campaign_id, short_code, request.location,
        request.size, request.include_logo)
    
    # Generate landing URL
    landing_url = f"{BASE_URL}/k/{short_code}"
    
    # Generate QR code image
    qr_image = generate_qr_code(landing_url, request.size, request.include_logo)
    
    QR_GENERATED.labels(type=campaign['campaign_type'], vertical=campaign['vertical']).inc()
    
    return {
        "qr_id": str(qr_id),
        "short_code": short_code,
        "landing_url": landing_url,
        "qr_image": qr_image,
        "campaign": {
            "name": campaign['name'],
            "type": campaign['campaign_type'],
            "offer_title": campaign['offer_title']
        },
        "location": request.location
    }

# Landing Pages & Interactions  
@app.get("/k/{short_code}", response_class=HTMLResponse)
async def kiosk_landing_page(short_code: str, request: Request):
    """Serve kiosk landing page"""
    
    # Get QR code and campaign
    qr_data = await app.state.db.fetchrow("""
        SELECT qr.*, kc.* FROM qr_codes qr
        JOIN kiosk_campaigns kc ON qr.campaign_id = kc.id
        WHERE qr.short_code = $1 AND kc.active = true
    """, short_code)
    
    if not qr_data:
        return HTMLResponse("<h1>Invalid or expired link</h1>", status_code=404)
    
    # Update scan count
    await app.state.db.execute("""
        UPDATE qr_codes SET scan_count = scan_count + 1, last_scanned = now()
        WHERE short_code = $1
    """, short_code)
    
    QR_SCANNED.labels(type=qr_data['campaign_type'], vertical=qr_data['vertical']).inc()
    
    # Record interaction
    await app.state.db.execute("""
        INSERT INTO kiosk_interactions (
            campaign_id, qr_short_code, interaction_type, 
            user_agent, ip_address
        ) VALUES ($1, $2, 'scan', $3, $4)
    """, qr_data['campaign_id'], short_code,
        request.headers.get("user-agent", ""), request.client.host)
    
    # Generate landing page based on campaign type
    customization = json.loads(qr_data['customization'] or '{}')
    
    if qr_data['campaign_type'] == 'book_now':
        html = generate_booking_page(qr_data, customization)
    elif qr_data['campaign_type'] == 'gift_card':
        html = generate_gift_card_page(qr_data, customization)
    elif qr_data['campaign_type'] == 'lead_capture':
        html = generate_lead_capture_page(qr_data, customization)
    else:  # survey
        html = generate_survey_page(qr_data, customization)
    
    return HTMLResponse(content=html)

def generate_booking_page(campaign_data, customization: Dict) -> str:
    """Generate booking landing page"""
    
    primary_color = customization.get('primary_color', '#667eea')
    business_name = customization.get('business_name', 'Our Business')
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{campaign_data['offer_title']}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                margin: 0; padding: 20px;
                background: linear-gradient(135deg, {primary_color} 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
            }}
            .container {{ max-width: 400px; margin: 0 auto; text-align: center; }}
            .card {{
                background: rgba(255,255,255,0.95);
                border-radius: 20px;
                padding: 30px;
                margin: 20px 0;
                color: #333;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            .offer-title {{ font-size: 24px; font-weight: bold; margin-bottom: 15px; color: {primary_color}; }}
            .offer-description {{ font-size: 16px; margin-bottom: 25px; line-height: 1.5; }}
            .cta-button {{
                background: {primary_color};
                color: white;
                border: none;
                border-radius: 50px;
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                width: 100%;
                margin: 10px 0;
                transition: transform 0.2s;
            }}
            .cta-button:hover {{ transform: scale(1.05); }}
            .business-info {{ font-size: 14px; color: #666; margin-top: 20px; }}
            .form-group {{ margin: 15px 0; text-align: left; }}
            .form-group label {{ display: block; margin-bottom: 5px; font-weight: 500; }}
            .form-group input {{
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="offer-title">{campaign_data['offer_title']}</div>
                <div class="offer-description">{campaign_data['offer_description']}</div>
                
                <form id="bookingForm" method="post" action="/k/{campaign_data['short_code']}/book">
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Phone Number</label>
                        <input type="tel" name="phone" required>
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label>Preferred Date/Time</label>
                        <input type="datetime-local" name="preferred_time">
                    </div>
                    
                    <button type="submit" class="cta-button">Book Now - FREE</button>
                </form>
                
                <div class="business-info">
                    Powered by {business_name}<br>
                    Scan • Book • Save
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('bookingForm').onsubmit = function(e) {{
                // Basic form validation and submission
                const name = document.querySelector('input[name="name"]').value;
                const phone = document.querySelector('input[name="phone"]').value;
                const email = document.querySelector('input[name="email"]').value;
                
                if (!name || !phone || !email) {{
                    alert('Please fill in all required fields');
                    e.preventDefault();
                    return false;
                }}
            }};
        </script>
    </body>
    </html>
    """
    
    return html

def generate_gift_card_page(campaign_data, customization: Dict) -> str:
    """Generate gift card purchase page"""
    
    primary_color = customization.get('primary_color', '#28a745')
    value_cents = campaign_data['gift_card_value_cents'] or 5000
    value_dollars = value_cents / 100
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gift Card - ${value_dollars:.0f}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                margin: 0; padding: 20px;
                background: linear-gradient(135deg, {primary_color} 0%, #20c997 100%);
                min-height: 100vh; color: white;
            }}
            .container {{ max-width: 400px; margin: 0 auto; text-align: center; }}
            .gift-card {{
                background: linear-gradient(45deg, #ffd700, #ffed4e);
                border-radius: 15px; padding: 30px; margin: 20px 0;
                color: #333; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            .value {{ font-size: 48px; font-weight: bold; color: {primary_color}; }}
            .cta-button {{
                background: {primary_color}; color: white; border: none;
                border-radius: 50px; padding: 15px 30px; font-size: 18px;
                font-weight: bold; cursor: pointer; width: 100%;
                margin: 10px 0; transition: transform 0.2s;
            }}
            .cta-button:hover {{ transform: scale(1.05); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="gift-card">
                <div style="font-size: 24px; margin-bottom: 10px;">{campaign_data['offer_title']}</div>
                <div class="value">${value_dollars:.0f}</div>
                <div style="margin: 15px 0;">{campaign_data['offer_description']}</div>
                <button class="cta-button" onclick="purchaseGiftCard()">Purchase Gift Card</button>
            </div>
        </div>
        
        <script>
            function purchaseGiftCard() {{
                // Redirect to payment or booking system
                window.location.href = '{campaign_data['redirect_url'] or f"/booking?gift_card={value_cents}"}';
            }}
        </script>
    </body>
    </html>
    """
    
    return html

def generate_lead_capture_page(campaign_data, customization: Dict) -> str:
    """Generate lead capture page"""
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{campaign_data['offer_title']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; }}
            .container {{ max-width: 400px; margin: 0 auto; }}
            .form-card {{
                background: white; border-radius: 10px; padding: 30px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .title {{ font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #333; }}
            .subtitle {{ color: #666; margin-bottom: 25px; }}
            .form-group {{ margin: 15px 0; }}
            .form-group input {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; }}
            .submit-btn {{
                background: #007bff; color: white; border: none;
                padding: 12px 20px; border-radius: 6px; width: 100%;
                font-size: 16px; cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="form-card">
                <div class="title">{campaign_data['offer_title']}</div>
                <div class="subtitle">{campaign_data['offer_description']}</div>
                
                <form method="post" action="/k/{campaign_data.get('short_code', '')}/capture">
                    <div class="form-group">
                        <input type="text" name="name" placeholder="Full Name" required>
                    </div>
                    <div class="form-group">
                        <input type="email" name="email" placeholder="Email Address" required>
                    </div>
                    <div class="form-group">
                        <input type="tel" name="phone" placeholder="Phone Number" required>
                    </div>
                    <button type="submit" class="submit-btn">Get Started</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_survey_page(campaign_data, customization: Dict) -> str:
    """Generate survey page"""
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Quick Survey</title>
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px; background: #f8f9fa;">
        <div style="max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
            <h2>{campaign_data['offer_title']}</h2>
            <p>{campaign_data['offer_description']}</p>
            <form method="post" action="/k/{campaign_data.get('short_code', '')}/survey">
                <div style="margin: 15px 0;">
                    <label>How satisfied are you with our service?</label><br>
                    <input type="radio" name="satisfaction" value="5"> Very Satisfied<br>
                    <input type="radio" name="satisfaction" value="4"> Satisfied<br>
                    <input type="radio" name="satisfaction" value="3"> Neutral<br>
                    <input type="radio" name="satisfaction" value="2"> Dissatisfied<br>
                    <input type="radio" name="satisfaction" value="1"> Very Dissatisfied
                </div>
                <div style="margin: 15px 0;">
                    <label>Comments:</label><br>
                    <textarea name="comments" style="width: 100%; height: 80px; padding: 10px;"></textarea>
                </div>
                <button type="submit" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; width: 100%;">
                    Submit Survey
                </button>
            </form>
        </div>
    </body>
    </html>
    """
    
    return html

# Form Submissions
@app.post("/k/{short_code}/book")
async def handle_booking(short_code: str, request: Request):
    """Handle booking form submission"""
    
    form = await request.form()
    
    # Get campaign
    campaign = await app.state.db.fetchrow("""
        SELECT kc.* FROM qr_codes qr
        JOIN kiosk_campaigns kc ON qr.campaign_id = kc.id
        WHERE qr.short_code = $1
    """, short_code)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Record interaction and create lead
    interaction_data = {
        "name": form.get("name"),
        "phone": form.get("phone"), 
        "email": form.get("email"),
        "preferred_time": form.get("preferred_time"),
        "form_type": "booking"
    }
    
    await app.state.db.execute("""
        INSERT INTO kiosk_interactions (
            campaign_id, qr_short_code, interaction_type, interaction_data
        ) VALUES ($1, $2, 'form_submit', $3)
    """, campaign['id'], short_code, json.dumps(interaction_data))
    
    # Create lead in main system
    lead_id = await app.state.db.fetchval("""
        INSERT INTO leads (
            id, vertical, email, phone, contact, attributes, payload
        ) VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6)
        RETURNING id
    """, campaign['vertical'], form.get("email"), form.get("phone"),
        json.dumps({"email": form.get("email"), "phone": form.get("phone")}),
        json.dumps({"name": form.get("name"), "source": "kiosk_qr"}),
        json.dumps({"kiosk_campaign": campaign['name'], "preferred_time": form.get("preferred_time")}))
    
    KIOSK_CONVERSIONS.labels(type="booking").inc()
    
    # Redirect to success or booking system
    if campaign['redirect_url']:
        return RedirectResponse(url=campaign['redirect_url'])
    else:
        return HTMLResponse(f"""
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>Booking Request Received!</h2>
            <p>Thank you {form.get('name')}! We'll contact you shortly at {form.get('phone')} to confirm your appointment.</p>
            <p>Lead ID: {lead_id}</p>
        </body>
        </html>
        """)

# Analytics
@app.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str):
    """Get campaign performance analytics"""
    
    # Campaign overview
    campaign = await app.state.db.fetchrow("""
        SELECT * FROM kiosk_campaigns WHERE id = $1
    """, campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # QR code stats
    qr_stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_qr_codes,
            SUM(scan_count) as total_scans,
            AVG(scan_count) as avg_scans_per_qr
        FROM qr_codes WHERE campaign_id = $1
    """, campaign_id)
    
    # Interaction stats
    interaction_stats = await app.state.db.fetch("""
        SELECT 
            interaction_type,
            COUNT(*) as count
        FROM kiosk_interactions 
        WHERE campaign_id = $1
        GROUP BY interaction_type
        ORDER BY count DESC
    """, campaign_id)
    
    # Conversion funnel
    funnel = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) FILTER (WHERE interaction_type = 'scan') as scans,
            COUNT(*) FILTER (WHERE interaction_type = 'form_submit') as form_submits,
            COUNT(*) FILTER (WHERE interaction_type = 'purchase') as purchases
        FROM kiosk_interactions 
        WHERE campaign_id = $1
    """, campaign_id)
    
    return {
        "campaign": {
            "id": str(campaign['id']),
            "name": campaign['name'],
            "type": campaign['campaign_type'],
            "vertical": campaign['vertical']
        },
        "qr_performance": {
            "total_qr_codes": qr_stats['total_qr_codes'],
            "total_scans": qr_stats['total_scans'] or 0,
            "avg_scans_per_qr": round(qr_stats['avg_scans_per_qr'] or 0, 1)
        },
        "interactions": [
            {
                "type": stat['interaction_type'],
                "count": stat['count']
            } for stat in interaction_stats
        ],
        "conversion_funnel": {
            "scans": funnel['scans'] or 0,
            "form_submits": funnel['form_submits'] or 0,
            "purchases": funnel['purchases'] or 0,
            "scan_to_form_rate": round((funnel['form_submits'] or 0) / max(funnel['scans'] or 1, 1) * 100, 2),
            "form_to_purchase_rate": round((funnel['purchases'] or 0) / max(funnel['form_submits'] or 1, 1) * 100, 2)
        }
    }

@app.get("/stats")
async def get_kiosk_stats():
    """Get overall kiosk generator statistics"""
    
    stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(DISTINCT kc.id) as total_campaigns,
            COUNT(DISTINCT qr.id) as total_qr_codes,
            SUM(qr.scan_count) as total_scans,
            COUNT(DISTINCT ki.id) as total_interactions
        FROM kiosk_campaigns kc
        LEFT JOIN qr_codes qr ON kc.id = qr.campaign_id
        LEFT JOIN kiosk_interactions ki ON kc.id = ki.campaign_id
        WHERE kc.created_at >= NOW() - INTERVAL '30 days'
    """)
    
    # Top performing campaigns
    top_campaigns = await app.state.db.fetch("""
        SELECT 
            kc.name,
            kc.campaign_type,
            kc.vertical,
            SUM(qr.scan_count) as total_scans,
            COUNT(ki.*) as interactions
        FROM kiosk_campaigns kc
        LEFT JOIN qr_codes qr ON kc.id = qr.campaign_id
        LEFT JOIN kiosk_interactions ki ON kc.id = ki.campaign_id
        WHERE kc.active = true
        GROUP BY kc.id, kc.name, kc.campaign_type, kc.vertical
        ORDER BY total_scans DESC NULLS LAST
        LIMIT 5
    """)
    
    return {
        "period": "last_30_days",
        "overview": {
            "total_campaigns": stats['total_campaigns'],
            "total_qr_codes": stats['total_qr_codes'],
            "total_scans": stats['total_scans'] or 0,
            "total_interactions": stats['total_interactions']
        },
        "top_campaigns": [
            {
                "name": tc['name'],
                "type": tc['campaign_type'],
                "vertical": tc['vertical'],
                "total_scans": tc['total_scans'] or 0,
                "interactions": tc['interactions']
            } for tc in top_campaigns
        ]
    }