from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

from agents import registry as agent_registry
from services.database import get_db_status
from services.cache import get_cache_status

APP_NAME = os.getenv("APP_NAME", "SINCOR")
VERSION = os.getenv("VERSION", "0.1.0")

app = FastAPI(title=APP_NAME, version=VERSION)

# Static + Templates
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
templates = Jinja2Templates(directory="ui/templates")

# Routers
router = APIRouter()

@router.get("/health", response_class=JSONResponse)
async def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": VERSION,
        "db": await get_db_status(),
        "cache": await get_cache_status(),
        "agents": list(agent_registry.keys())
    }

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": APP_NAME,
        "version": VERSION,
        "agents": agent_registry
    })

class AgentRunRequest(BaseModel):
    agent: str
    payload: dict = {}

@router.post("/run", response_class=JSONResponse)
async def run_agent(req: AgentRunRequest):
    name = req.agent
    if name not in agent_registry:
        return JSONResponse({"error": f"Unknown agent '{name}'"}, status_code=404)
    agent = agent_registry[name]
    result = await agent.handle(req.payload)
    return {"agent": name, "result": result}

app.include_router(router)

# Uvicorn entry if run locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
