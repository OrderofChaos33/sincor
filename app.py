from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

APP_NAME = os.getenv("APP_NAME", "SINCOR")
VERSION = os.getenv("VERSION", "0.1.0")

app = FastAPI(title=APP_NAME, version=VERSION)

# Static + Templates (with error handling)
try:
    app.mount("/static", StaticFiles(directory="ui/static"), name="static")
    templates = Jinja2Templates(directory="ui/templates")
except Exception:
    # Fallback if directories don't exist
    templates = None

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Simple HTML response if templates fail
    if templates is None:
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>{APP_NAME}</title></head>
        <body>
            <h1>{APP_NAME} v{VERSION}</h1>
            <p>Status: Running</p>
            <p><a href="/health">Health Check</a></p>
        </body>
        </html>
        """)

    try:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "app_name": APP_NAME,
            "version": VERSION
        })
    except Exception:
        # Fallback HTML
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>{APP_NAME}</title></head>
        <body>
            <h1>{APP_NAME} v{VERSION}</h1>
            <p>Status: Running</p>
            <p><a href="/health">Health Check</a></p>
        </body>
        </html>
        """)

@app.get("/status")
async def status():
    return {"app": APP_NAME, "version": VERSION, "status": "running"}

# Uvicorn entry if run locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
