from fastapi import FastAPI, HTTPException, Response, Depends, Header
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("RECYCLING_ADMIN_KEY", "admin-dev-key")

# Metrics
LEADS_RECYCLED = Counter("recycling_leads_total", "Total leads recycled", ["vertical", "reason"])
RESALES = Counter("recycling_resales_total", "Leads resold", ["vertical"])
MARGINS = Counter("recycling_margin_cents_total", "Total margin from recycling", ["vertical"])

class ReturnedLead(BaseModel):
    lead_id: str
    buyer_id: str
    return_reason: str
    original_price_cents: int
    
class RecyclingBid(BaseModel):
    lead_id: str
    buyer_id: str
    bid_cents: int
    expires_at: Optional[datetime] = None

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)
    
    # Subscribe to lead.returned events
    await setup_event_listeners()

async def setup_event_listeners():
    """Subscribe to Redis Streams for lead returns"""
    async def process_returned_lead():
        while True:
            try:
                # Listen for lead.returned events
                streams = await app.state.redis.xread(
                    {"stream.leads.returned": "$"}, 
                    count=10, 
                    block=5000
                )
                
                for stream_name, messages in streams:
                    for message_id, fields in messages:
                        await handle_returned_lead(dict(fields))
                        
            except Exception as e:
                print(f"Error processing returned leads: {e}")
                await asyncio.sleep(5)
    
    # Start background task
    import asyncio
    asyncio.create_task(process_returned_lead())

async def handle_returned_lead(event_data: Dict):
    """Process returned lead and add to recycling exchange"""
    try:
        lead_id = event_data.get('lead_id')
        buyer_id = event_data.get('buyer_id') 
        return_reason = event_data.get('return_reason', 'unspecified')
        original_price_cents = int(event_data.get('original_price_cents', 0))
        
        # Get lead details
        lead = await app.state.db.fetchrow("""
            SELECT * FROM leads WHERE id = $1
        """, lead_id)
        
        if not lead:
            return
        
        # Calculate recycling price (discount based on return reason)
        price_multipliers = {
            'no_contact': 0.7,      # 30% discount
            'bad_data': 0.5,        # 50% discount  
            'duplicate': 0.4,       # 60% discount
            'unqualified': 0.6,     # 40% discount
            'aged': 0.3,            # 70% discount
            'default': 0.6
        }
        
        multiplier = price_multipliers.get(return_reason, price_multipliers['default'])
        recycling_price = int(original_price_cents * multiplier)
        
        # Set minimum floor price
        min_price = max(recycling_price, 500)  # $5 minimum
        
        # Add to recycling exchange
        await app.state.db.execute("""
            INSERT INTO recycling_inventory (
                lead_id, original_buyer_id, return_reason,
                original_price_cents, recycling_price_cents, 
                min_bid_cents, vertical, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'available')
            ON CONFLICT (lead_id) DO UPDATE SET
                return_reason = EXCLUDED.return_reason,
                recycling_price_cents = EXCLUDED.recycling_price_cents,
                updated_at = now()
        """, lead_id, buyer_id, return_reason, original_price_cents, 
            recycling_price, min_price, lead['vertical'])
        
        LEADS_RECYCLED.labels(vertical=lead['vertical'], reason=return_reason).inc()
        
        # Notify potential buyers
        await notify_buyers_of_recycled_lead(lead_id, lead['vertical'], min_price)
        
    except Exception as e:
        print(f"Error handling returned lead: {e}")

async def notify_buyers_of_recycled_lead(lead_id: str, vertical: str, min_price: int):
    """Notify eligible buyers about recycled lead"""
    # Find buyers interested in this vertical (excluding original buyer)
    buyers = await app.state.db.fetch("""
        SELECT DISTINCT buyer_id FROM buyer_reputation 
        WHERE score >= 60  -- Only good reputation buyers
    """)
    
    notification = {
        "type": "recycled_lead_available",
        "lead_id": lead_id,
        "vertical": vertical,
        "min_bid_cents": min_price,
        "available_until": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    # Send to notification queue (implement webhook/email as needed)
    for buyer in buyers:
        await app.state.redis.lpush(
            f"notifications:{buyer['buyer_id']}", 
            json.dumps(notification)
        )

@app.get("/health")
async def health():
    return {"ok": True, "service": "recycling_exchange"}

@app.get("/metrics") 
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/returns")
async def report_returned_lead(returned_lead: ReturnedLead):
    """Report a returned lead for recycling"""
    # Emit to Redis Streams
    event_data = {
        "lead_id": returned_lead.lead_id,
        "buyer_id": returned_lead.buyer_id,
        "return_reason": returned_lead.return_reason,
        "original_price_cents": str(returned_lead.original_price_cents),
        "timestamp": datetime.now().isoformat()
    }
    
    await app.state.redis.xadd("stream.leads.returned", event_data)
    
    return {"status": "return_processed", "lead_id": returned_lead.lead_id}

@app.get("/inventory")
async def get_recycling_inventory(
    vertical: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    limit: int = 50
):
    """Browse available recycled leads"""
    query = """
        SELECT ri.*, l.email, l.phone, l.state 
        FROM recycling_inventory ri
        JOIN leads l ON ri.lead_id = l.id
        WHERE ri.status = 'available'
    """
    params = []
    
    if vertical:
        params.append(vertical)
        query += f" AND ri.vertical = ${len(params)}"
        
    if min_price:
        params.append(min_price)
        query += f" AND ri.recycling_price_cents >= ${len(params)}"
        
    if max_price:
        params.append(max_price)
        query += f" AND ri.recycling_price_cents <= ${len(params)}"
    
    query += " ORDER BY ri.created_at DESC"
    params.append(limit)
    query += f" LIMIT ${len(params)}"
    
    rows = await app.state.db.fetch(query, *params)
    
    inventory = []
    for row in rows:
        inventory.append({
            "lead_id": row['lead_id'],
            "vertical": row['vertical'],
            "recycling_price_cents": row['recycling_price_cents'],
            "min_bid_cents": row['min_bid_cents'],
            "return_reason": row['return_reason'],
            "state": row['state'],
            "available_since": row['created_at'].isoformat(),
            "has_email": bool(row['email']),
            "has_phone": bool(row['phone'])
        })
    
    return {"inventory": inventory, "count": len(inventory)}

@app.post("/bid")
async def place_bid(bid: RecyclingBid):
    """Place bid on recycled lead"""
    # Check if lead is available
    lead_info = await app.state.db.fetchrow("""
        SELECT * FROM recycling_inventory 
        WHERE lead_id = $1 AND status = 'available'
    """, bid.lead_id)
    
    if not lead_info:
        raise HTTPException(status_code=404, detail="Lead not available")
    
    if bid.bid_cents < lead_info['min_bid_cents']:
        raise HTTPException(
            status_code=400, 
            detail=f"Bid too low. Minimum: ${lead_info['min_bid_cents']/100:.2f}"
        )
    
    # Don't allow original buyer to rebid
    if bid.buyer_id == lead_info['original_buyer_id']:
        raise HTTPException(status_code=403, detail="Original buyer cannot rebid")
    
    # Check buyer reputation
    reputation = await app.state.db.fetchval(
        "SELECT score FROM buyer_reputation WHERE buyer_id = $1",
        bid.buyer_id
    )
    
    if not reputation or reputation < 60:
        raise HTTPException(status_code=403, detail="Insufficient reputation for recycled leads")
    
    # Insert or update bid
    await app.state.db.execute("""
        INSERT INTO recycling_bids (lead_id, buyer_id, bid_cents, expires_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (lead_id, buyer_id)
        DO UPDATE SET 
            bid_cents = GREATEST(recycling_bids.bid_cents, EXCLUDED.bid_cents),
            expires_at = EXCLUDED.expires_at,
            updated_at = now()
    """, bid.lead_id, bid.buyer_id, bid.bid_cents, 
        bid.expires_at or datetime.now() + timedelta(hours=24))
    
    return {
        "lead_id": bid.lead_id,
        "bid_cents": bid.bid_cents,
        "status": "bid_placed"
    }

@app.post("/accept/{lead_id}")
async def accept_highest_bid(lead_id: str):
    """Accept highest bid for recycled lead"""
    # Get highest bid
    winner = await app.state.db.fetchrow("""
        SELECT rb.*, ri.recycling_price_cents, ri.original_price_cents
        FROM recycling_bids rb
        JOIN recycling_inventory ri ON rb.lead_id = ri.lead_id
        WHERE rb.lead_id = $1 AND ri.status = 'available'
        ORDER BY rb.bid_cents DESC
        LIMIT 1
    """, lead_id)
    
    if not winner:
        raise HTTPException(status_code=404, detail="No bids found")
    
    # Calculate margin (spread)
    margin_cents = winner['bid_cents'] - winner['recycling_price_cents']
    
    # Create delivery record
    delivery_id = await app.state.db.fetchval("""
        INSERT INTO delivery_ledger (lead_id, destination, status, meta)
        VALUES ($1, $2, 'DELIVERED', $3)
        RETURNING id
    """, lead_id, winner['buyer_id'], json.dumps({
        "recycled": True,
        "original_price_cents": winner['original_price_cents'],
        "recycling_price_cents": winner['recycling_price_cents'],
        "final_bid_cents": winner['bid_cents'],
        "margin_cents": margin_cents
    }))
    
    # Mark as sold
    await app.state.db.execute("""
        UPDATE recycling_inventory 
        SET status = 'sold', winning_bid_cents = $2, sold_at = now()
        WHERE lead_id = $1
    """, lead_id, winner['bid_cents'])
    
    # Clean up other bids
    await app.state.db.execute("""
        DELETE FROM recycling_bids WHERE lead_id = $1 AND buyer_id != $2
    """, lead_id, winner['buyer_id'])
    
    # Track metrics
    lead_info = await app.state.db.fetchrow("SELECT vertical FROM leads WHERE id = $1", lead_id)
    RESALES.labels(vertical=lead_info['vertical']).inc()
    MARGINS.labels(vertical=lead_info['vertical']).inc(margin_cents)
    
    return {
        "lead_id": lead_id,
        "winner": winner['buyer_id'],
        "winning_bid_cents": winner['bid_cents'],
        "margin_cents": margin_cents,
        "delivery_id": str(delivery_id)
    }

@app.get("/stats")
async def get_recycling_stats():
    """Get recycling exchange statistics"""
    stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_recycled,
            COUNT(*) FILTER (WHERE status = 'available') as available_leads,
            COUNT(*) FILTER (WHERE status = 'sold') as sold_leads,
            AVG(CASE WHEN status = 'sold' THEN winning_bid_cents ELSE NULL END)::INTEGER as avg_resale_price_cents,
            SUM(CASE WHEN status = 'sold' THEN (winning_bid_cents - recycling_price_cents) ELSE 0 END) as total_margin_cents
        FROM recycling_inventory
    """)
    
    # Breakdown by vertical
    vertical_stats = await app.state.db.fetch("""
        SELECT 
            vertical,
            COUNT(*) as count,
            AVG(CASE WHEN status = 'sold' THEN winning_bid_cents ELSE NULL END)::INTEGER as avg_price_cents
        FROM recycling_inventory
        GROUP BY vertical
        ORDER BY count DESC
    """)
    
    return {
        "total_recycled": stats['total_recycled'],
        "available_leads": stats['available_leads'],
        "sold_leads": stats['sold_leads'],
        "avg_resale_price_cents": stats['avg_resale_price_cents'],
        "total_margin_cents": stats['total_margin_cents'],
        "by_vertical": [
            {
                "vertical": vs['vertical'],
                "count": vs['count'],
                "avg_price_cents": vs['avg_price_cents']
            } for vs in vertical_stats
        ]
    }

@app.get("/my_bids/{buyer_id}")
async def get_my_bids(buyer_id: str):
    """Get buyer's active bids"""
    bids = await app.state.db.fetch("""
        SELECT rb.*, ri.vertical, ri.status as lead_status
        FROM recycling_bids rb
        JOIN recycling_inventory ri ON rb.lead_id = ri.lead_id
        WHERE rb.buyer_id = $1
        ORDER BY rb.created_at DESC
    """, buyer_id)
    
    return {
        "buyer_id": buyer_id,
        "active_bids": [
            {
                "lead_id": bid['lead_id'],
                "vertical": bid['vertical'],
                "bid_cents": bid['bid_cents'],
                "lead_status": bid['lead_status'],
                "expires_at": bid['expires_at'].isoformat() if bid['expires_at'] else None,
                "created_at": bid['created_at'].isoformat()
            } for bid in bids
        ],
        "total_bids": len(bids)
    }