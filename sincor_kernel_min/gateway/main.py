from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger
from commons.queue import get_queue

app = FastAPI(title="SINCOR Gateway", version="0.1.0")

class Dispatch(BaseModel):
    task_type: str
    payload: dict

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/dispatch")
def dispatch(req: Dispatch):
    qname = f"{req.task_type}:queue"
    try:
        queue = get_queue(qname)
        queue.push(req.payload)
        logger.info(f"Enqueued task to {qname}: {req.payload}")
        return {"enqueued": True, "queue": qname}
    except Exception as e:
        logger.exception("Enqueue failed")
        raise HTTPException(status_code=500, detail=str(e))
