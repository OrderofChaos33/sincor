from fastapi import FastAPI, Response
import asyncpg, os
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)

@app.get("/health")
async def health():
    return {"ok": True, "service": "dashboard"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def kpis():
    # toy KPIs for now; wire to real aggregates later
    rows = await app.state.db.fetch("SELECT count(*) as leads FROM leads")
    return {"leads_total": rows[0]["leads"] if rows else 0}