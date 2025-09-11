from fastapi import FastAPI, HTTPException, Response, Depends, Header, BackgroundTasks
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import asyncio

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("LTV_ADMIN_KEY", "admin-dev-key")

# Metrics
LTV_PREDICTIONS = Counter("ltv_predictions_total", "LTV predictions made", ["vertical", "tier"])
MODEL_RETRAINS = Counter("ltv_model_retrains_total", "Model retraining events")
LTV_ACCURACY = Histogram("ltv_prediction_accuracy", "LTV prediction accuracy", buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

class LTVPredictionRequest(BaseModel):
    lead_id: Optional[str] = None
    customer_email: Optional[str] = None
    vertical: str
    lead_attributes: Dict[str, Any] = {}
    subscription_plan: Optional[str] = None

class LTVModelConfig(BaseModel):
    vertical: str
    features: List[str]
    lookback_days: int = 365
    prediction_horizon_days: int = 365
    min_training_samples: int = 50

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

def extract_features(lead_data: Dict, historical_data: Dict) -> Dict[str, float]:
    """Extract features for LTV prediction"""
    features = {}
    
    # Lead quality features
    features['lead_score'] = float(lead_data.get('lead_score', 50))
    features['source_quality'] = float(lead_data.get('source_quality', 0.5))
    
    # Demographic features
    state = lead_data.get('state', '').upper()
    high_value_states = {'CA', 'NY', 'TX', 'FL', 'WA'}
    features['high_value_location'] = 1.0 if state in high_value_states else 0.0
    
    # Engagement features
    features['email_opens'] = float(historical_data.get('email_opens', 0))
    features['email_clicks'] = float(historical_data.get('email_clicks', 0))
    features['website_visits'] = float(historical_data.get('website_visits', 0))
    features['booking_attempts'] = float(historical_data.get('booking_attempts', 0))
    
    # Temporal features
    hour = datetime.now().hour
    features['is_business_hours'] = 1.0 if 9 <= hour <= 17 else 0.0
    features['is_weekend'] = 1.0 if datetime.now().weekday() >= 5 else 0.0
    
    # Service-specific features
    if lead_data.get('requested_service'):
        service = lead_data['requested_service'].lower()
        features['premium_service'] = 1.0 if any(word in service for word in ['premium', 'deluxe', 'full']) else 0.0
    else:
        features['premium_service'] = 0.0
    
    # Historical transaction features
    features['avg_order_value'] = float(historical_data.get('avg_order_value', 0))
    features['transaction_frequency'] = float(historical_data.get('transaction_count', 0))
    features['days_since_last_purchase'] = float(historical_data.get('days_since_last_purchase', 999))
    
    return features

def simple_linear_model(features: Dict[str, float], coefficients: Dict[str, float]) -> float:
    """Simple linear regression for LTV prediction"""
    ltv = coefficients.get('intercept', 0.0)
    
    for feature, value in features.items():
        coeff = coefficients.get(feature, 0.0)
        ltv += coeff * value
    
    return max(0.0, ltv)  # LTV can't be negative

async def get_model_coefficients(vertical: str, db) -> Dict[str, float]:
    """Get trained model coefficients for vertical"""
    model = await db.fetchrow("""
        SELECT coefficients FROM ltv_models 
        WHERE vertical = $1 AND active = true
        ORDER BY created_at DESC LIMIT 1
    """, vertical)
    
    if model:
        return json.loads(model['coefficients'])
    else:
        # Default coefficients (based on domain knowledge)
        return {
            'intercept': 50.0,
            'lead_score': 2.0,
            'source_quality': 100.0,
            'high_value_location': 25.0,
            'email_opens': 5.0,
            'email_clicks': 15.0,
            'website_visits': 3.0,
            'booking_attempts': 50.0,
            'is_business_hours': 10.0,
            'premium_service': 75.0,
            'avg_order_value': 0.1,
            'transaction_frequency': 30.0,
            'days_since_last_purchase': -0.2
        }

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)
    
    # Schedule model retraining
    asyncio.create_task(scheduled_model_training())

async def scheduled_model_training():
    """Background task for weekly model retraining"""
    while True:
        try:
            await asyncio.sleep(24 * 3600)  # Daily check
            
            # Check if it's Sunday (retraining day)
            if datetime.now().weekday() == 6:  # Sunday
                await retrain_all_models()
        except Exception as e:
            print(f"Error in scheduled training: {e}")
            await asyncio.sleep(3600)  # Retry in 1 hour

@app.get("/health")
async def health():
    return {"ok": True, "service": "ltv_forecaster"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/predict")
async def predict_ltv(request: LTVPredictionRequest):
    """Predict customer lifetime value"""
    
    # Get lead/customer data
    if request.lead_id:
        lead = await app.state.db.fetchrow("""
            SELECT * FROM leads WHERE id = $1
        """, request.lead_id)
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        lead_data = {
            'lead_score': lead.get('payload', {}).get('score', 50),
            'state': lead.get('state'),
            'vertical': lead.get('vertical'),
            'requested_service': lead.get('payload', {}).get('service'),
            'source_quality': 0.7  # Default
        }
        customer_email = lead.get('email')
        
    else:
        lead_data = {
            'lead_score': request.lead_attributes.get('lead_score', 50),
            'state': request.lead_attributes.get('state'),
            'vertical': request.vertical,
            'requested_service': request.lead_attributes.get('service'),
            'source_quality': request.lead_attributes.get('source_quality', 0.5)
        }
        customer_email = request.customer_email
    
    # Get historical engagement data
    historical_data = {}
    if customer_email:
        history = await app.state.db.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE event_type = 'email_open') as email_opens,
                COUNT(*) FILTER (WHERE event_type = 'email_click') as email_clicks,
                COUNT(*) FILTER (WHERE event_type = 'website_visit') as website_visits,
                COUNT(*) FILTER (WHERE event_type = 'booking_attempt') as booking_attempts,
                AVG(CASE WHEN p.amount_cents IS NOT NULL THEN p.amount_cents ELSE 0 END) as avg_order_value,
                COUNT(DISTINCT p.id) as transaction_count,
                COALESCE(MIN(EXTRACT(EPOCH FROM (NOW() - p.created_at))/86400), 999) as days_since_last_purchase
            FROM engagement_events ee
            FULL OUTER JOIN purchases p ON p.customer_email = ee.customer_email
            WHERE ee.customer_email = $1 OR p.customer_email = $1
        """, customer_email)
        
        if history:
            historical_data = {
                'email_opens': history['email_opens'] or 0,
                'email_clicks': history['email_clicks'] or 0,
                'website_visits': history['website_visits'] or 0,
                'booking_attempts': history['booking_attempts'] or 0,
                'avg_order_value': history['avg_order_value'] or 0,
                'transaction_count': history['transaction_count'] or 0,
                'days_since_last_purchase': history['days_since_last_purchase'] or 999
            }
    
    # Extract features
    features = extract_features(lead_data, historical_data)
    
    # Get model coefficients
    coefficients = await get_model_coefficients(request.vertical, app.state.db)
    
    # Predict LTV
    predicted_ltv = simple_linear_model(features, coefficients)
    
    # Determine LTV tier
    if predicted_ltv >= 500:
        ltv_tier = "high"
    elif predicted_ltv >= 200:
        ltv_tier = "medium"
    else:
        ltv_tier = "low"
    
    # Store prediction for model improvement
    await app.state.db.execute("""
        INSERT INTO ltv_predictions (
            lead_id, customer_email, vertical, predicted_ltv, 
            ltv_tier, features, model_version
        ) VALUES ($1, $2, $3, $4, $5, $6, 
            (SELECT COALESCE(MAX(version), 1) FROM ltv_models WHERE vertical = $3))
    """, request.lead_id, customer_email, request.vertical, 
        predicted_ltv, ltv_tier, json.dumps(features))
    
    LTV_PREDICTIONS.labels(vertical=request.vertical, tier=ltv_tier).inc()
    
    return {
        "predicted_ltv": round(predicted_ltv, 2),
        "ltv_tier": ltv_tier,
        "confidence": 0.75,  # Static for now
        "features_used": list(features.keys()),
        "recommendation": {
            "suggested_bid_ceiling": round(predicted_ltv * 0.3, 2),  # 30% of LTV
            "priority_score": min(100, int(predicted_ltv / 5)),
            "nurture_campaign": "premium" if ltv_tier == "high" else "standard"
        }
    }

@app.post("/batch_predict")
async def batch_predict_ltv(requests: List[LTVPredictionRequest]):
    """Batch LTV prediction for efficiency"""
    
    if len(requests) > 100:
        raise HTTPException(status_code=400, detail="Batch size limited to 100 requests")
    
    predictions = []
    
    for req in requests:
        try:
            # Call individual prediction (could be optimized with bulk queries)
            pred = await predict_ltv(req)
            predictions.append({
                "lead_id": req.lead_id,
                "customer_email": req.customer_email,
                **pred
            })
        except Exception as e:
            predictions.append({
                "lead_id": req.lead_id,
                "customer_email": req.customer_email,
                "error": str(e)
            })
    
    return {"predictions": predictions, "batch_size": len(predictions)}

@app.post("/feedback")
async def record_ltv_feedback(
    lead_id: Optional[str] = None,
    customer_email: Optional[str] = None,
    actual_ltv: float = 0,
    timeframe_days: int = 365
):
    """Record actual LTV for model improvement"""
    
    # Find prediction to update
    if lead_id:
        await app.state.db.execute("""
            UPDATE ltv_predictions 
            SET actual_ltv = $2, feedback_date = now(), timeframe_days = $3
            WHERE lead_id = $1
        """, lead_id, actual_ltv, timeframe_days)
    elif customer_email:
        await app.state.db.execute("""
            UPDATE ltv_predictions 
            SET actual_ltv = $2, feedback_date = now(), timeframe_days = $3
            WHERE customer_email = $1
        """, customer_email, actual_ltv, timeframe_days)
    else:
        raise HTTPException(status_code=400, detail="Must provide lead_id or customer_email")
    
    return {"status": "feedback_recorded", "actual_ltv": actual_ltv}

@app.post("/train", dependencies=[Depends(verify_admin)])
async def train_model(config: LTVModelConfig, background_tasks: BackgroundTasks):
    """Train LTV model for vertical (admin only)"""
    
    background_tasks.add_task(train_model_background, config)
    
    return {
        "status": "training_started",
        "vertical": config.vertical,
        "estimated_completion": "5-10 minutes"
    }

async def train_model_background(config: LTVModelConfig):
    """Background model training"""
    try:
        # Get training data
        training_data = await app.state.db.fetch("""
            SELECT 
                p.predicted_ltv,
                p.actual_ltv,
                p.features,
                p.ltv_tier
            FROM ltv_predictions p
            WHERE p.vertical = $1 
            AND p.actual_ltv IS NOT NULL
            AND p.feedback_date >= NOW() - INTERVAL '%s days'
            ORDER BY p.feedback_date DESC
            LIMIT 1000
        """ % config.lookback_days, config.vertical)
        
        if len(training_data) < config.min_training_samples:
            print(f"Insufficient training data for {config.vertical}: {len(training_data)} samples")
            return
        
        # Simple linear regression training
        X = []  # Feature matrix
        y = []  # Target LTV values
        feature_names = []
        
        for row in training_data:
            features = json.loads(row['features'])
            if not feature_names:
                feature_names = list(features.keys())
            
            feature_vector = [features.get(fname, 0.0) for fname in feature_names]
            X.append([1.0] + feature_vector)  # Add intercept term
            y.append(float(row['actual_ltv']))
        
        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)
        
        # Simple least squares solution: θ = (X^T X)^-1 X^T y
        try:
            coefficients = np.linalg.solve(X.T @ X, X.T @ y)
            
            # Create coefficient dictionary
            coeff_dict = {'intercept': float(coefficients[0])}
            for i, fname in enumerate(feature_names):
                coeff_dict[fname] = float(coefficients[i + 1])
            
            # Calculate model accuracy on training data
            predictions = X @ coefficients
            mse = np.mean((predictions - y) ** 2)
            r_squared = 1 - (mse / np.var(y))
            
            # Store model
            await app.state.db.execute("""
                INSERT INTO ltv_models (
                    vertical, coefficients, features, 
                    training_samples, mse, r_squared, active
                ) VALUES ($1, $2, $3, $4, $5, $6, true)
            """, config.vertical, json.dumps(coeff_dict), config.features,
                len(training_data), float(mse), float(r_squared))
            
            # Deactivate old models
            await app.state.db.execute("""
                UPDATE ltv_models SET active = false 
                WHERE vertical = $1 AND id != (
                    SELECT id FROM ltv_models 
                    WHERE vertical = $1 
                    ORDER BY created_at DESC LIMIT 1
                )
            """, config.vertical)
            
            MODEL_RETRAINS.inc()
            
            print(f"Model trained for {config.vertical}: R² = {r_squared:.3f}, MSE = {mse:.2f}")
            
        except np.linalg.LinAlgError:
            print(f"Linear algebra error training model for {config.vertical}")
            
    except Exception as e:
        print(f"Error training model for {config.vertical}: {e}")

async def retrain_all_models():
    """Retrain all active models"""
    verticals = await app.state.db.fetch("""
        SELECT DISTINCT vertical FROM ltv_predictions 
        WHERE actual_ltv IS NOT NULL
    """)
    
    for vertical_row in verticals:
        vertical = vertical_row['vertical']
        config = LTVModelConfig(
            vertical=vertical,
            features=['lead_score', 'source_quality', 'email_opens', 'transaction_frequency']
        )
        await train_model_background(config)

@app.get("/models")
async def list_models():
    """List available LTV models"""
    
    models = await app.state.db.fetch("""
        SELECT 
            vertical,
            training_samples,
            r_squared,
            mse,
            created_at,
            active
        FROM ltv_models
        WHERE active = true
        ORDER BY vertical, created_at DESC
    """)
    
    return {
        "models": [
            {
                "vertical": m['vertical'],
                "training_samples": m['training_samples'],
                "r_squared": float(m['r_squared']) if m['r_squared'] else 0,
                "mse": float(m['mse']) if m['mse'] else 0,
                "accuracy": "good" if (m['r_squared'] or 0) > 0.7 else "fair" if (m['r_squared'] or 0) > 0.5 else "poor",
                "last_trained": m['created_at'].isoformat(),
                "active": m['active']
            } for m in models
        ]
    }

@app.get("/stats")
async def get_ltv_stats():
    """Get LTV forecaster statistics"""
    
    stats = await app.state.db.fetchrow("""
        SELECT 
            COUNT(*) as total_predictions,
            COUNT(*) FILTER (WHERE actual_ltv IS NOT NULL) as predictions_with_feedback,
            AVG(predicted_ltv) as avg_predicted_ltv,
            AVG(actual_ltv) as avg_actual_ltv,
            COUNT(*) FILTER (WHERE ltv_tier = 'high') as high_ltv_predictions,
            COUNT(*) FILTER (WHERE ltv_tier = 'medium') as medium_ltv_predictions,
            COUNT(*) FILTER (WHERE ltv_tier = 'low') as low_ltv_predictions
        FROM ltv_predictions
        WHERE created_at >= NOW() - INTERVAL '30 days'
    """)
    
    # Calculate accuracy for predictions with feedback
    accuracy_stats = await app.state.db.fetchrow("""
        SELECT 
            AVG(ABS(predicted_ltv - actual_ltv) / GREATEST(actual_ltv, 1)) as mape,
            STDDEV(predicted_ltv - actual_ltv) as prediction_std
        FROM ltv_predictions
        WHERE actual_ltv IS NOT NULL AND actual_ltv > 0
    """)
    
    return {
        "period": "last_30_days",
        "total_predictions": stats['total_predictions'],
        "predictions_with_feedback": stats['predictions_with_feedback'],
        "average_predicted_ltv": round(stats['avg_predicted_ltv'] or 0, 2),
        "average_actual_ltv": round(stats['avg_actual_ltv'] or 0, 2),
        "tier_distribution": {
            "high": stats['high_ltv_predictions'],
            "medium": stats['medium_ltv_predictions'],
            "low": stats['low_ltv_predictions']
        },
        "model_accuracy": {
            "mape": round((accuracy_stats['mape'] or 0) * 100, 2),  # Mean Absolute Percentage Error
            "prediction_std": round(accuracy_stats['prediction_std'] or 0, 2)
        }
    }