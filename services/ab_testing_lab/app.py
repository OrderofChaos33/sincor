from fastapi import FastAPI, HTTPException, Response, Depends, Header
from pydantic import BaseModel, EmailStr
import asyncpg
import aioredis
import os
import json
import random
import math
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
ADMIN_API_KEY = os.getenv("AB_ADMIN_KEY", "admin-dev-key")

# Metrics
EXPERIMENTS_STARTED = Counter("ab_experiments_started_total", "Experiments started", ["template_type"])
VARIANT_ASSIGNMENTS = Counter("ab_variant_assignments_total", "Variant assignments", ["experiment", "variant"])
CONVERSIONS_TRACKED = Counter("ab_conversions_total", "Conversions tracked", ["experiment", "variant"])

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    template_type: str  # email_subject, email_body, sms_message, ad_creative
    control_template: str
    variants: List[Dict[str, Any]]  # [{"name": "variant_a", "template": "..."}]
    traffic_split: Optional[float] = 0.5  # % traffic to experiment
    success_metric: str = "open_rate"  # open_rate, click_rate, conversion_rate
    min_sample_size: Optional[int] = 100
    max_duration_days: Optional[int] = 30

class VariantAssignment(BaseModel):
    experiment_id: str
    user_id: str  # lead_id, contact_id, etc.
    context: Optional[Dict] = {}

class ConversionEvent(BaseModel):
    experiment_id: str
    user_id: str
    event_type: str  # open, click, convert
    variant_id: str
    value: Optional[float] = 1.0
    metadata: Optional[Dict] = {}

async def verify_admin(authorization: str = Header(None)):
    """Admin authentication"""
    if authorization != f"Bearer {ADMIN_API_KEY}":
        raise HTTPException(status_code=403, detail="Admin access required")

def calculate_statistical_significance(control_conversions: int, control_impressions: int,
                                     variant_conversions: int, variant_impressions: int) -> Dict:
    """Calculate statistical significance using two-proportion z-test"""
    
    if control_impressions == 0 or variant_impressions == 0:
        return {"significant": False, "p_value": 1.0, "confidence": 0.0}
    
    p1 = control_conversions / control_impressions
    p2 = variant_conversions / variant_impressions
    
    # Pooled proportion
    p_pool = (control_conversions + variant_conversions) / (control_impressions + variant_impressions)
    
    if p_pool == 0 or p_pool == 1:
        return {"significant": False, "p_value": 1.0, "confidence": 0.0}
    
    # Standard error
    se = math.sqrt(p_pool * (1 - p_pool) * (1/control_impressions + 1/variant_impressions))
    
    if se == 0:
        return {"significant": False, "p_value": 1.0, "confidence": 0.0}
    
    # Z-score
    z = (p2 - p1) / se
    
    # P-value (two-tailed test)
    p_value = 2 * (1 - stats_norm_cdf(abs(z)))
    
    # Effect size (relative lift)
    lift = ((p2 - p1) / p1 * 100) if p1 > 0 else 0
    
    return {
        "significant": p_value < 0.05,
        "p_value": p_value,
        "confidence": (1 - p_value) * 100,
        "lift_percent": lift,
        "control_rate": p1,
        "variant_rate": p2
    }

def stats_norm_cdf(x):
    """Approximate normal CDF (simplified for basic stats)"""
    return (1 + math.erf(x / math.sqrt(2))) / 2

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)

@app.get("/health")
async def health():
    return {"ok": True, "service": "ab_testing_lab"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Experiment Management
@app.post("/experiments", dependencies=[Depends(verify_admin)])
async def create_experiment(experiment: ExperimentCreate):
    """Create new A/B test experiment"""
    
    # Insert experiment
    experiment_id = await app.state.db.fetchval("""
        INSERT INTO ab_experiments (
            name, description, template_type, control_template, 
            variants, traffic_split, success_metric, min_sample_size, 
            max_duration_days, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'active')
        RETURNING id
    """, experiment.name, experiment.description, experiment.template_type, 
        experiment.control_template, json.dumps(experiment.variants),
        experiment.traffic_split, experiment.success_metric, 
        experiment.min_sample_size, experiment.max_duration_days)
    
    EXPERIMENTS_STARTED.labels(template_type=experiment.template_type).inc()
    
    return {
        "experiment_id": str(experiment_id),
        "name": experiment.name,
        "status": "active",
        "variants_count": len(experiment.variants),
        "expected_duration": f"{experiment.max_duration_days} days"
    }

@app.get("/experiments")
async def list_experiments(status: Optional[str] = None):
    """List all experiments"""
    
    query = """
        SELECT 
            e.*,
            COUNT(DISTINCT a.user_id) as participants,
            COUNT(c.*) as total_events
        FROM ab_experiments e
        LEFT JOIN ab_assignments a ON e.id = a.experiment_id
        LEFT JOIN ab_conversions c ON e.id = c.experiment_id
        WHERE 1=1
    """
    params = []
    
    if status:
        params.append(status)
        query += f" AND e.status = ${len(params)}"
    
    query += " GROUP BY e.id ORDER BY e.created_at DESC"
    
    experiments = await app.state.db.fetch(query, *params)
    
    return {
        "experiments": [
            {
                "id": str(exp['id']),
                "name": exp['name'],
                "template_type": exp['template_type'],
                "status": exp['status'],
                "participants": exp['participants'],
                "total_events": exp['total_events'],
                "traffic_split": float(exp['traffic_split']),
                "created_at": exp['created_at'].isoformat(),
                "variants_count": len(json.loads(exp['variants'])) if exp['variants'] else 0
            } for exp in experiments
        ]
    }

@app.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get detailed experiment results"""
    
    experiment = await app.state.db.fetchrow("""
        SELECT * FROM ab_experiments WHERE id = $1
    """, experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Get variant performance
    variant_stats = await app.state.db.fetch("""
        SELECT 
            a.variant_id,
            COUNT(DISTINCT a.user_id) as impressions,
            COUNT(c.*) as conversions,
            COUNT(c.*) FILTER (WHERE c.event_type = 'open') as opens,
            COUNT(c.*) FILTER (WHERE c.event_type = 'click') as clicks,
            COUNT(c.*) FILTER (WHERE c.event_type = 'convert') as converts
        FROM ab_assignments a
        LEFT JOIN ab_conversions c ON a.experiment_id = c.experiment_id 
            AND a.user_id = c.user_id
        WHERE a.experiment_id = $1
        GROUP BY a.variant_id
    """, experiment_id)
    
    # Calculate stats for each variant
    variants = json.loads(experiment['variants']) if experiment['variants'] else []
    variant_results = []
    
    control_stats = None
    for stat in variant_stats:
        if stat['variant_id'] == 'control':
            control_stats = stat
            break
    
    for stat in variant_stats:
        variant_name = stat['variant_id']
        impressions = stat['impressions']
        conversions = stat['conversions']
        
        # Calculate rates
        open_rate = (stat['opens'] / impressions) if impressions > 0 else 0
        click_rate = (stat['clicks'] / impressions) if impressions > 0 else 0
        conversion_rate = (stat['converts'] / impressions) if impressions > 0 else 0
        
        # Statistical significance (compare to control)
        significance = {"significant": False, "p_value": 1.0, "confidence": 0.0}
        if control_stats and stat['variant_id'] != 'control':
            significance = calculate_statistical_significance(
                control_stats['converts'], control_stats['impressions'],
                stat['converts'], impressions
            )
        
        variant_results.append({
            "variant_id": variant_name,
            "impressions": impressions,
            "conversions": conversions,
            "rates": {
                "open_rate": round(open_rate * 100, 2),
                "click_rate": round(click_rate * 100, 2), 
                "conversion_rate": round(conversion_rate * 100, 2)
            },
            "statistical_significance": significance
        })
    
    return {
        "experiment": {
            "id": str(experiment['id']),
            "name": experiment['name'],
            "description": experiment['description'],
            "template_type": experiment['template_type'],
            "status": experiment['status'],
            "success_metric": experiment['success_metric'],
            "created_at": experiment['created_at'].isoformat(),
            "control_template": experiment['control_template'],
            "variants": variants
        },
        "results": variant_results,
        "summary": {
            "total_participants": sum(v["impressions"] for v in variant_results),
            "total_conversions": sum(v["conversions"] for v in variant_results),
            "duration_days": (datetime.now() - experiment['created_at']).days,
            "has_winner": any(v["statistical_significance"]["significant"] for v in variant_results)
        }
    }

# Assignment & Tracking
@app.post("/assign")
async def assign_variant(assignment: VariantAssignment):
    """Assign user to experiment variant"""
    
    # Get experiment
    experiment = await app.state.db.fetchrow("""
        SELECT * FROM ab_experiments 
        WHERE id = $1 AND status = 'active'
    """, assignment.experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Active experiment not found")
    
    # Check if user already assigned
    existing = await app.state.db.fetchrow("""
        SELECT variant_id FROM ab_assignments 
        WHERE experiment_id = $1 AND user_id = $2
    """, assignment.experiment_id, assignment.user_id)
    
    if existing:
        return {
            "experiment_id": assignment.experiment_id,
            "user_id": assignment.user_id,
            "variant_id": existing['variant_id'],
            "template": await get_template_for_variant(experiment, existing['variant_id'])
        }
    
    # Traffic split check
    if random.random() > experiment['traffic_split']:
        # User not in experiment
        return {
            "experiment_id": assignment.experiment_id,
            "user_id": assignment.user_id,
            "variant_id": "control",
            "template": experiment['control_template'],
            "in_experiment": False
        }
    
    # Assign variant (simple random for now)
    variants = json.loads(experiment['variants']) if experiment['variants'] else []
    
    if not variants:
        variant_id = "control"
        template = experiment['control_template']
    else:
        # Random assignment between control and variants
        all_options = ['control'] + [v['name'] for v in variants]
        variant_id = random.choice(all_options)
        template = await get_template_for_variant(experiment, variant_id)
    
    # Record assignment
    await app.state.db.execute("""
        INSERT INTO ab_assignments (experiment_id, user_id, variant_id, context)
        VALUES ($1, $2, $3, $4)
    """, assignment.experiment_id, assignment.user_id, variant_id, 
        json.dumps(assignment.context or {}))
    
    VARIANT_ASSIGNMENTS.labels(experiment=experiment['name'], variant=variant_id).inc()
    
    return {
        "experiment_id": assignment.experiment_id,
        "user_id": assignment.user_id,
        "variant_id": variant_id,
        "template": template,
        "in_experiment": True
    }

async def get_template_for_variant(experiment, variant_id: str) -> str:
    """Get template content for variant"""
    if variant_id == "control":
        return experiment['control_template']
    
    variants = json.loads(experiment['variants']) if experiment['variants'] else []
    for variant in variants:
        if variant['name'] == variant_id:
            return variant.get('template', experiment['control_template'])
    
    return experiment['control_template']

@app.post("/track")
async def track_conversion(event: ConversionEvent):
    """Track conversion event"""
    
    # Verify assignment exists
    assignment = await app.state.db.fetchrow("""
        SELECT * FROM ab_assignments 
        WHERE experiment_id = $1 AND user_id = $2
    """, event.experiment_id, event.user_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Record conversion
    await app.state.db.execute("""
        INSERT INTO ab_conversions (
            experiment_id, user_id, variant_id, event_type, value, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6)
    """, event.experiment_id, event.user_id, assignment['variant_id'],
        event.event_type, event.value, json.dumps(event.metadata or {}))
    
    # Get experiment name for metrics
    experiment = await app.state.db.fetchval(
        "SELECT name FROM ab_experiments WHERE id = $1",
        event.experiment_id
    )
    
    CONVERSIONS_TRACKED.labels(
        experiment=experiment or "unknown",
        variant=assignment['variant_id']
    ).inc()
    
    return {
        "experiment_id": event.experiment_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "variant_id": assignment['variant_id'],
        "status": "tracked"
    }

# Admin Controls
@app.post("/experiments/{experiment_id}/stop", dependencies=[Depends(verify_admin)])
async def stop_experiment(experiment_id: str):
    """Stop experiment and declare winner"""
    
    # Get current results
    results = await get_experiment(experiment_id)
    
    # Find best performing variant
    best_variant = None
    best_rate = 0
    
    for variant in results["results"]:
        rate = variant["rates"]["conversion_rate"]
        if rate > best_rate and variant.get("statistical_significance", {}).get("significant", False):
            best_rate = rate
            best_variant = variant["variant_id"]
    
    # Update experiment status
    await app.state.db.execute("""
        UPDATE ab_experiments 
        SET status = 'completed', winner_variant = $2, completed_at = now()
        WHERE id = $1
    """, experiment_id, best_variant)
    
    return {
        "experiment_id": experiment_id,
        "status": "stopped",
        "winner": best_variant,
        "winning_rate": best_rate,
        "total_participants": results["summary"]["total_participants"]
    }

@app.get("/templates/{template_type}")
async def get_optimized_template(
    template_type: str,
    fallback_template: str,
    user_id: Optional[str] = None
):
    """Get optimized template based on completed experiments"""
    
    # Find completed experiments for this template type with winners
    winner = await app.state.db.fetchrow("""
        SELECT e.winner_variant, e.variants, e.control_template
        FROM ab_experiments e
        WHERE e.template_type = $1 
        AND e.status = 'completed' 
        AND e.winner_variant IS NOT NULL
        ORDER BY e.completed_at DESC
        LIMIT 1
    """, template_type)
    
    if not winner:
        return {
            "template": fallback_template,
            "source": "fallback",
            "optimized": False
        }
    
    # Get winning template
    if winner['winner_variant'] == 'control':
        winning_template = winner['control_template']
    else:
        variants = json.loads(winner['variants']) if winner['variants'] else []
        winning_template = fallback_template
        
        for variant in variants:
            if variant['name'] == winner['winner_variant']:
                winning_template = variant.get('template', fallback_template)
                break
    
    return {
        "template": winning_template,
        "source": "experiment_winner",
        "winning_variant": winner['winner_variant'],
        "optimized": True
    }