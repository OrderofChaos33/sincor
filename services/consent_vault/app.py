from fastapi import FastAPI
from pydantic import BaseModel
import asyncpg, os

DB_DSN = os.getenv("DB_DSN")
app = FastAPI()

class ConsentIn(BaseModel):
    lead_id: str
    ts: str
    ip: str | None = None
    referrer: str | None = None
    form_html: str

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)

@app.post("/consent")
async def consent(c: ConsentIn):
    from storage import store_consent
    digest = await store_consent(app.state.db, c.lead_id, c.ts, c.ip, c.referrer, c.form_html)
    return {"ok": True, "sha256": digest}

@app.get("/health")
async def health():
    return {"ok": True}