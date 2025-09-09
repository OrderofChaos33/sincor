from fastapi import FastAPI, HTTPException, Response, Query, Depends, Header
from fastapi.responses import StreamingResponse
import asyncpg
import os
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from libs.pkg_guard.pii import safe_log

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
ANALYTICS_ACCESS_KEY = os.getenv("ANALYTICS_ACCESS_KEY", "analytics-dev-key")

# Metrics
ANALYTICS_REQUESTS = Counter("analytics_requests_total", "Analytics API requests", ["endpoint", "tenant"])
DATA_EXPORTS = Counter("analytics_exports_total", "Data exports", ["format", "type"])

async def verify_access(authorization: str = Header(None)):
    """Analytics API authentication"""
    if authorization != f"Bearer {ANALYTICS_ACCESS_KEY}":
        raise HTTPException(status_code=403, detail="Analytics access required")

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)

@app.get("/health")
async def health():
    return {"ok": True, "service": "analytics_api"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Funnel Analytics
@app.get("/reports/funnel", dependencies=[Depends(verify_access)])
async def get_funnel_report(
    from_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(..., description="End date (YYYY-MM-DD)"), 
    tenant: Optional[str] = Query(None, description="Filter by tenant/vertical")
):
    """Get conversion funnel analytics"""
    
    ANALYTICS_REQUESTS.labels(endpoint="funnel", tenant=tenant or "all").inc()
    
    # Parse dates
    try:
        start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Build query
    query = """
        SELECT 
            date,
            SUM(received) as total_received,
            SUM(cleaned) as total_cleaned, 
            SUM(scored) as total_scored,
            SUM(delivered) as total_delivered,
            ROUND(SUM(cleaned)::decimal / NULLIF(SUM(received), 0) * 100, 2) as clean_rate,
            ROUND(SUM(scored)::decimal / NULLIF(SUM(cleaned), 0) * 100, 2) as score_rate,
            ROUND(SUM(delivered)::decimal / NULLIF(SUM(scored), 0) * 100, 2) as delivery_rate,
            ROUND(SUM(delivered)::decimal / NULLIF(SUM(received), 0) * 100, 2) as overall_conversion_rate
        FROM mv_funnel_daily 
        WHERE date >= $1 AND date <= $2
    """
    params = [start_date, end_date]
    
    if tenant:
        query += " AND tenant = $3"
        params.append(tenant)
    
    query += " GROUP BY date ORDER BY date"
    
    rows = await app.state.db.fetch(query, *params)
    
    # Calculate totals
    totals = {
        'total_received': sum(row['total_received'] for row in rows),
        'total_cleaned': sum(row['total_cleaned'] for row in rows),
        'total_scored': sum(row['total_scored'] for row in rows), 
        'total_delivered': sum(row['total_delivered'] for row in rows)
    }
    
    if totals['total_received'] > 0:
        totals['overall_clean_rate'] = round(totals['total_cleaned'] / totals['total_received'] * 100, 2)
        totals['overall_score_rate'] = round(totals['total_scored'] / totals['total_cleaned'] * 100, 2) if totals['total_cleaned'] else 0
        totals['overall_delivery_rate'] = round(totals['total_delivered'] / totals['total_scored'] * 100, 2) if totals['total_scored'] else 0
        totals['overall_conversion_rate'] = round(totals['total_delivered'] / totals['total_received'] * 100, 2)
    
    return {
        "date_range": {"from": from_date, "to": to_date},
        "tenant": tenant,
        "totals": totals,
        "daily_breakdown": [
            {
                "date": row['date'].isoformat(),
                "received": row['total_received'],
                "cleaned": row['total_cleaned'],
                "scored": row['total_scored'],
                "delivered": row['total_delivered'],
                "rates": {
                    "clean_rate": float(row['clean_rate']) if row['clean_rate'] else 0,
                    "score_rate": float(row['score_rate']) if row['score_rate'] else 0,
                    "delivery_rate": float(row['delivery_rate']) if row['delivery_rate'] else 0,
                    "overall_conversion_rate": float(row['overall_conversion_rate']) if row['overall_conversion_rate'] else 0
                }
            } for row in rows
        ]
    }

# ROI Analytics  
@app.get("/reports/roi", dependencies=[Depends(verify_access)])
async def get_roi_report(
    group_by: str = Query("vertical", description="Group by: vertical, source, tenant"),
    days: int = Query(30, description="Days to look back"),
    tenant: Optional[str] = Query(None)
):
    """Get ROI analytics grouped by specified dimension"""
    
    ANALYTICS_REQUESTS.labels(endpoint="roi", tenant=tenant or "all").inc()
    
    if group_by not in ["vertical", "source", "tenant"]:
        raise HTTPException(status_code=400, detail="group_by must be: vertical, source, or tenant")
    
    start_date = datetime.now().date() - timedelta(days=days)
    
    # Revenue data
    revenue_query = """
        SELECT 
            tenant,
            SUM(gross_cents) as total_revenue_cents,
            SUM(returns) as total_returns,
            SUM(total_transactions) as total_transactions
        FROM mv_revenue_daily 
        WHERE date >= $1
    """
    revenue_params = [start_date]
    
    if tenant:
        revenue_query += " AND tenant = $2"
        revenue_params.append(tenant)
    
    revenue_query += " GROUP BY tenant ORDER BY total_revenue_cents DESC"
    
    revenue_rows = await app.state.db.fetch(revenue_query, *revenue_params)
    
    # Lead volume data
    leads_query = """
        SELECT 
            tenant,
            SUM(received) as total_leads,
            SUM(delivered) as total_delivered
        FROM mv_funnel_daily
        WHERE date >= $1
    """
    leads_params = [start_date]
    
    if tenant:
        leads_query += " AND tenant = $2" 
        leads_params.append(tenant)
        
    leads_query += " GROUP BY tenant"
    
    leads_rows = await app.state.db.fetch(leads_query, *leads_params)
    
    # Combine data
    results = []
    leads_dict = {row['tenant']: row for row in leads_rows}
    
    for rev_row in revenue_rows:
        tenant_name = rev_row['tenant']
        leads_data = leads_dict.get(tenant_name, {'total_leads': 0, 'total_delivered': 0})
        
        revenue_per_lead = 0
        if leads_data['total_delivered'] > 0:
            revenue_per_lead = rev_row['total_revenue_cents'] / leads_data['total_delivered']
        
        conversion_rate = 0
        if leads_data['total_leads'] > 0:
            conversion_rate = leads_data['total_delivered'] / leads_data['total_leads'] * 100
            
        results.append({
            group_by: tenant_name,
            "total_revenue_cents": rev_row['total_revenue_cents'],
            "total_revenue_dollars": round(rev_row['total_revenue_cents'] / 100, 2),
            "total_leads": leads_data['total_leads'],
            "total_delivered": leads_data['total_delivered'],
            "revenue_per_delivered_lead_cents": round(revenue_per_lead, 0),
            "revenue_per_delivered_lead_dollars": round(revenue_per_lead / 100, 2),
            "conversion_rate_percent": round(conversion_rate, 2),
            "total_transactions": rev_row['total_transactions'],
            "total_returns": rev_row['total_returns'],
            "return_rate_percent": round(rev_row['total_returns'] / max(rev_row['total_transactions'], 1) * 100, 2)
        })
    
    return {
        "group_by": group_by,
        "date_range_days": days,
        "tenant_filter": tenant,
        "results": results,
        "summary": {
            "total_revenue_cents": sum(r['total_revenue_cents'] for r in results),
            "total_leads": sum(r['total_leads'] for r in results),
            "average_revenue_per_lead": round(
                sum(r['total_revenue_cents'] for r in results) / max(sum(r['total_delivered'] for r in results), 1), 2
            )
        }
    }

# Benchmark Data Export
@app.get("/exports/benchmarks.csv", dependencies=[Depends(verify_access)])
async def export_benchmarks():
    """Export anonymized industry benchmarks as CSV"""
    
    DATA_EXPORTS.labels(format="csv", type="benchmarks").inc()
    
    # Get aggregated benchmark data (anonymized)
    benchmarks_query = """
        SELECT 
            'industry_avg' as segment,
            AVG(CASE WHEN received > 0 THEN cleaned::decimal / received * 100 END) as avg_clean_rate,
            AVG(CASE WHEN cleaned > 0 THEN scored::decimal / cleaned * 100 END) as avg_score_rate,
            AVG(CASE WHEN scored > 0 THEN delivered::decimal / scored * 100 END) as avg_delivery_rate,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY CASE WHEN received > 0 THEN delivered::decimal / received * 100 END) as p25_conversion_rate,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY CASE WHEN received > 0 THEN delivered::decimal / received * 100 END) as p50_conversion_rate,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY CASE WHEN received > 0 THEN delivered::decimal / received * 100 END) as p75_conversion_rate
        FROM mv_funnel_daily
        WHERE date >= CURRENT_DATE - INTERVAL '90 days'
    """
    
    benchmark_row = await app.state.db.fetchrow(benchmarks_query)
    
    # Revenue benchmarks
    revenue_query = """
        SELECT
            'industry_avg' as segment,
            AVG(gross_cents / 100.0) as avg_revenue_per_day,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY gross_cents / 100.0) as median_daily_revenue
        FROM mv_revenue_daily
        WHERE date >= CURRENT_DATE - INTERVAL '90 days'
    """
    
    revenue_row = await app.state.db.fetchrow(revenue_query)
    
    # Create CSV data
    csv_data = [
        ["metric", "value", "percentile", "description"],
        ["avg_clean_rate", round(float(benchmark_row['avg_clean_rate'] or 0), 2), "mean", "Average email/phone validation rate"],
        ["avg_score_rate", round(float(benchmark_row['avg_score_rate'] or 0), 2), "mean", "Average lead scoring rate"],  
        ["avg_delivery_rate", round(float(benchmark_row['avg_delivery_rate'] or 0), 2), "mean", "Average delivery success rate"],
        ["p25_conversion_rate", round(float(benchmark_row['p25_conversion_rate'] or 0), 2), "p25", "25th percentile overall conversion rate"],
        ["p50_conversion_rate", round(float(benchmark_row['p50_conversion_rate'] or 0), 2), "p50", "50th percentile overall conversion rate"],
        ["p75_conversion_rate", round(float(benchmark_row['p75_conversion_rate'] or 0), 2), "p75", "75th percentile overall conversion rate"],
        ["avg_daily_revenue", round(float(revenue_row['avg_revenue_per_day'] or 0), 2), "mean", "Average daily revenue (USD)"],
        ["median_daily_revenue", round(float(revenue_row['median_daily_revenue'] or 0), 2), "p50", "Median daily revenue (USD)"]
    ]
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    for row in csv_data:
        writer.writerow(row)
    
    csv_content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lead_gen_benchmarks.csv"}
    )

# Data Freshness
@app.post("/refresh", dependencies=[Depends(verify_access)])
async def refresh_analytics():
    """Refresh materialized views for latest data"""
    
    try:
        await app.state.db.execute("SELECT refresh_analytics_views()")
        return {"status": "success", "message": "Analytics views refreshed", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh views: {str(e)}")

# Health Check with Data Freshness
@app.get("/status")
async def get_status():
    """Get service status and data freshness"""
    
    # Check data freshness
    latest_lead = await app.state.db.fetchrow("SELECT MAX(created_at) as latest FROM leads")
    latest_funnel = await app.state.db.fetchrow("SELECT MAX(date) as latest FROM mv_funnel_daily")
    latest_revenue = await app.state.db.fetchrow("SELECT MAX(date) as latest FROM mv_revenue_daily")
    
    return {
        "service": "analytics_api",
        "status": "healthy",
        "data_freshness": {
            "latest_lead_timestamp": latest_lead['latest'].isoformat() if latest_lead['latest'] else None,
            "latest_funnel_date": latest_funnel['latest'].isoformat() if latest_funnel['latest'] else None,
            "latest_revenue_date": latest_revenue['latest'].isoformat() if latest_revenue['latest'] else None
        },
        "endpoints": [
            "/reports/funnel",
            "/reports/roi", 
            "/exports/benchmarks.csv",
            "/refresh"
        ]
    }