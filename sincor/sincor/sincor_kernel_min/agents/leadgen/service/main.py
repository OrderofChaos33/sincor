from fastapi import FastAPI
from loguru import logger

app = FastAPI(title="LeadGen Agent Service")

@app.get("/health")
def health():
    logger.debug("LeadGen Service healthy")
    return {"status": "ok", "agent": "leadgen"}
