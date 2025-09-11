from fastapi import FastAPI, HTTPException, Response, Depends, Header
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("CHARGEBACK_ADMIN_KEY", "admin-dev-key")

# Metrics
RISK_SCORES = Histogram("chargeback_risk_scores", "Risk score distribution", buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
TRANSACTIONS_SCREENED = Counter("chargeback_transactions_screened_total", "Transactions screened", ["action"])
CHARGEBACKS_PREVENTED = Counter("chargeback_prevented_total", "Estimated chargebacks prevented")

class PaymentIntentEvent(BaseModel):
    payment_id: str
    customer_email: EmailStr
    amount_cents: int
    currency: str = "USD"
    customer_ip: Optional[str] = None
    billing_address: Optional[Dict] = {}
    payment_method: Optional[Dict] = {}
    metadata: Optional[Dict] = {}

class RiskDecision(BaseModel):
    action: str  # allow, hold, deny, alternate_rail
    risk_score: float
    reasons: list
    confidence: float

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)

@app.get("/health")
async def health():
    return {"ok": True, "service": "chargeback_shield"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

def calculate_email_risk_score(email: str) -> tuple[float, list]:
    """Calculate risk score based on email patterns"""
    risk_factors = []
    score = 0.0
    
    # Disposable email domains
    disposable_domains = {
        'tempmail.org', '10minutemail.com', 'guerrillamail.com', 
        'mailinator.com', 'yopmail.com', 'throwaway.email'
    }
    
    domain = email.split('@')[-1].lower()
    
    if domain in disposable_domains:
        score += 0.7
        risk_factors.append("disposable_email_domain")
    
    # Suspicious patterns
    if any(char.isdigit() for char in email) and email.count('+') > 0:
        score += 0.3
        risk_factors.append("suspicious_email_pattern")
    
    # Recently created domains (simplified check)
    new_domains = {'temptest.net', 'quickmail.xyz', 'fasttemp.co'}
    if domain in new_domains:
        score += 0.4
        risk_factors.append("new_domain")
    
    return min(score, 1.0), risk_factors

async def calculate_velocity_risk_score(customer_email: str, amount_cents: int, customer_ip: str = None) -> tuple[float, list]:
    """Calculate risk based on transaction velocity"""
    risk_factors = []
    score = 0.0
    
    # Check email velocity (last 24h)
    email_count = await app.state.db.fetchval("""
        SELECT COUNT(*) FROM risk_transactions 
        WHERE customer_email = $1 AND created_at >= NOW() - INTERVAL '24 hours'
    """, customer_email)
    
    if email_count >= 5:
        score += 0.6
        risk_factors.append(f"high_email_velocity_{email_count}_per_24h")
    elif email_count >= 3:
        score += 0.3
        risk_factors.append(f"medium_email_velocity_{email_count}_per_24h")
    
    # Check IP velocity if available
    if customer_ip:
        ip_count = await app.state.db.fetchval("""
            SELECT COUNT(*) FROM risk_transactions 
            WHERE customer_ip = $1 AND created_at >= NOW() - INTERVAL '1 hour'
        """, customer_ip)
        
        if ip_count >= 3:
            score += 0.4
            risk_factors.append(f"high_ip_velocity_{ip_count}_per_hour")
    
    # Amount-based risk
    if amount_cents > 50000:  # $500+
        score += 0.2
        risk_factors.append("high_amount")
    elif amount_cents > 100000:  # $1000+
        score += 0.4
        risk_factors.append("very_high_amount")
    
    return min(score, 1.0), risk_factors

async def calculate_historical_risk_score(customer_email: str) -> tuple[float, list]:
    """Calculate risk based on historical behavior"""
    risk_factors = []
    score = 0.0
    
    # Check chargeback history
    chargeback_history = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_transactions,
            COUNT(*) FILTER (WHERE final_status = 'chargeback') as chargebacks,
            COUNT(*) FILTER (WHERE final_status = 'refunded') as refunds
        FROM risk_transactions 
        WHERE customer_email = $1
    """, customer_email)
    
    if chargeback_history['total_transactions'] > 0:
        chargeback_rate = chargeback_history['chargebacks'] / chargeback_history['total_transactions']
        refund_rate = chargeback_history['refunds'] / chargeback_history['total_transactions']
        
        if chargeback_rate > 0.1:  # >10% chargeback rate
            score += 0.8
            risk_factors.append(f"high_chargeback_rate_{chargeback_rate:.1%}")
        elif chargeback_rate > 0.05:  # >5% chargeback rate
            score += 0.4
            risk_factors.append(f"medium_chargeback_rate_{chargeback_rate:.1%}")
        
        if refund_rate > 0.2:  # >20% refund rate
            score += 0.3
            risk_factors.append(f"high_refund_rate_{refund_rate:.1%}")
    
    return min(score, 1.0), risk_factors

def calculate_payment_method_risk_score(payment_method: Dict) -> tuple[float, list]:
    """Calculate risk based on payment method"""
    risk_factors = []
    score = 0.0
    
    card_type = payment_method.get('type', '').lower()
    
    # Prepaid cards higher risk
    if card_type in ['prepaid', 'gift']:
        score += 0.4
        risk_factors.append("prepaid_card")
    
    # Virtual card numbers
    if payment_method.get('virtual', False):
        score += 0.2
        risk_factors.append("virtual_card")
    
    # International cards for domestic purchases
    card_country = payment_method.get('country')
    billing_country = payment_method.get('billing_country', 'US')
    
    if card_country and card_country != billing_country:
        score += 0.3
        risk_factors.append("international_card_mismatch")
    
    return min(score, 1.0), risk_factors

@app.post("/screen")
async def screen_transaction(payment_event: PaymentIntentEvent):
    """Screen transaction and return risk decision"""
    
    # Calculate individual risk scores
    email_score, email_factors = calculate_email_risk_score(payment_event.customer_email)
    velocity_score, velocity_factors = await calculate_velocity_risk_score(
        payment_event.customer_email, 
        payment_event.amount_cents,
        payment_event.customer_ip
    )
    historical_score, historical_factors = await calculate_historical_risk_score(payment_event.customer_email)
    payment_score, payment_factors = calculate_payment_method_risk_score(payment_event.payment_method or {})
    
    # Composite risk score (weighted)
    composite_score = (
        email_score * 0.3 +
        velocity_score * 0.3 +
        historical_score * 0.3 +
        payment_score * 0.1
    )
    
    all_factors = email_factors + velocity_factors + historical_factors + payment_factors
    
    # Risk decision logic
    if composite_score >= 0.8:
        action = "deny"
        confidence = 0.9
    elif composite_score >= 0.6:
        action = "hold"
        confidence = 0.7
    elif composite_score >= 0.4:
        action = "alternate_rail"  # Use different payment processor
        confidence = 0.6
    else:
        action = "allow"
        confidence = 0.8
    
    # Store transaction for future risk scoring
    await app.state.db.execute("""
        INSERT INTO risk_transactions (
            payment_id, customer_email, customer_ip, amount_cents,
            risk_score, risk_factors, action_taken, billing_address, payment_method
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """, payment_event.payment_id, payment_event.customer_email, payment_event.customer_ip,
        payment_event.amount_cents, composite_score, all_factors, action,
        json.dumps(payment_event.billing_address), json.dumps(payment_event.payment_method))
    
    # Track metrics
    RISK_SCORES.observe(composite_score)
    TRANSACTIONS_SCREENED.labels(action=action).inc()
    
    if action in ["deny", "hold"]:
        CHARGEBACKS_PREVENTED.inc()
    
    decision = RiskDecision(
        action=action,
        risk_score=round(composite_score, 3),
        reasons=all_factors,
        confidence=confidence
    )
    
    return {
        "payment_id": payment_event.payment_id,
        "decision": decision.dict(),
        "processing_time_ms": 50  # Approximate
    }

@app.post("/feedback")
async def report_transaction_outcome(
    payment_id: str,
    final_status: str,  # completed, chargeback, refunded, fraud
    metadata: Optional[Dict] = {}
):
    """Report final transaction outcome for ML training"""
    
    # Update transaction record
    await app.state.db.execute("""
        UPDATE risk_transactions 
        SET final_status = $2, outcome_metadata = $3, outcome_updated_at = now()
        WHERE payment_id = $1
    """, payment_id, final_status, json.dumps(metadata or {}))
    
    # If chargeback, update chargeback prevention metrics
    if final_status == "chargeback":
        # Check if we correctly identified high risk
        transaction = await app.state.db.fetchrow("""
            SELECT risk_score, action_taken FROM risk_transactions WHERE payment_id = $1
        """, payment_id)
        
        if transaction and transaction['risk_score'] < 0.5:
            # We missed a chargeback - false negative
            await app.state.redis.incr("shield_false_negatives")
        elif transaction and transaction['action_taken'] in ['deny', 'hold']:
            # We correctly prevented this (though it still happened somehow)
            await app.state.redis.incr("shield_true_positives") 
    
    return {"status": "feedback_recorded", "payment_id": payment_id}

@app.get("/stats")
async def get_shield_stats():
    """Get chargeback shield performance statistics"""
    
    stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_screened,
            COUNT(*) FILTER (WHERE action_taken = 'allow') as allowed,
            COUNT(*) FILTER (WHERE action_taken = 'hold') as held,
            COUNT(*) FILTER (WHERE action_taken = 'deny') as denied,
            COUNT(*) FILTER (WHERE action_taken = 'alternate_rail') as alternate_rail,
            AVG(risk_score) as avg_risk_score,
            COUNT(*) FILTER (WHERE final_status = 'chargeback') as actual_chargebacks,
            COUNT(*) FILTER (WHERE final_status = 'completed') as completed_transactions
        FROM risk_transactions
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """)
    
    # Calculate prevention rate
    total_high_risk = stats['held'] + stats['denied']
    prevention_rate = 0.0
    if stats['total_screened'] > 0:
        # Estimate: assume 2% of high-risk transactions would have been chargebacks
        estimated_prevented = total_high_risk * 0.02
        prevention_rate = estimated_prevented / max(stats['actual_chargebacks'] + estimated_prevented, 1)
    
    # Get risk score distribution
    risk_distribution = await app.state.db.fetch("""
        SELECT 
            FLOOR(risk_score * 10) / 10 as risk_bucket,
            COUNT(*) as count
        FROM risk_transactions
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY FLOOR(risk_score * 10) / 10
        ORDER BY risk_bucket
    """)
    
    return {
        "period": "last_30_days",
        "transactions_screened": stats['total_screened'],
        "actions": {
            "allowed": stats['allowed'],
            "held": stats['held'], 
            "denied": stats['denied'],
            "alternate_rail": stats['alternate_rail']
        },
        "performance": {
            "avg_risk_score": float(stats['avg_risk_score']) if stats['avg_risk_score'] else 0.0,
            "actual_chargebacks": stats['actual_chargebacks'],
            "completed_transactions": stats['completed_transactions'],
            "estimated_prevention_rate": round(prevention_rate * 100, 2)
        },
        "risk_distribution": [
            {
                "risk_range": f"{rd['risk_bucket']:.1f}-{rd['risk_bucket'] + 0.1:.1f}",
                "count": rd['count']
            } for rd in risk_distribution
        ]
    }

@app.get("/rules", dependencies=[Depends(verify_admin)])
async def get_risk_rules():
    """Get current risk scoring rules (admin only)"""
    
    return {
        "email_rules": {
            "disposable_domains": 0.7,
            "suspicious_patterns": 0.3,
            "new_domains": 0.4
        },
        "velocity_rules": {
            "high_email_velocity_24h": 0.6,
            "medium_email_velocity_24h": 0.3,
            "high_ip_velocity_1h": 0.4,
            "high_amount_threshold_cents": 50000,
            "very_high_amount_threshold_cents": 100000
        },
        "decision_thresholds": {
            "deny_threshold": 0.8,
            "hold_threshold": 0.6,
            "alternate_rail_threshold": 0.4
        },
        "composite_weights": {
            "email_weight": 0.3,
            "velocity_weight": 0.3,
            "historical_weight": 0.3,
            "payment_method_weight": 0.1
        }
    }

@app.post("/rules/update", dependencies=[Depends(verify_admin)])
async def update_risk_rules(rules: Dict[str, Any]):
    """Update risk scoring rules (admin only)"""
    
    # Store updated rules in database
    await app.state.db.execute("""
        INSERT INTO risk_rules (rules_json, version, created_by)
        VALUES ($1, (SELECT COALESCE(MAX(version), 0) + 1 FROM risk_rules), 'admin')
    """, json.dumps(rules))
    
    return {"status": "rules_updated", "version": "next"}

@app.get("/high_risk")
async def get_high_risk_transactions(limit: int = 50):
    """Get recent high-risk transactions for review"""
    
    transactions = await app.state.db.fetch("""
        SELECT 
            payment_id,
            customer_email,
            amount_cents,
            risk_score,
            risk_factors,
            action_taken,
            final_status,
            created_at
        FROM risk_transactions
        WHERE risk_score >= 0.6
        ORDER BY created_at DESC
        LIMIT $1
    """, limit)
    
    return {
        "high_risk_transactions": [
            {
                "payment_id": t['payment_id'],
                "customer_email": t['customer_email'],
                "amount_cents": t['amount_cents'],
                "risk_score": float(t['risk_score']),
                "risk_factors": t['risk_factors'],
                "action_taken": t['action_taken'],
                "final_status": t['final_status'],
                "created_at": t['created_at'].isoformat()
            } for t in transactions
        ]
    }