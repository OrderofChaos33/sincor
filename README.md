# SINCOR · Railway Build

Minimal, production-lean build of SINCOR suitable for Railway. FastAPI + Uvicorn with agents as modular async handlers.

## Quick Start (Local)
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

Open: http://localhost:8080 and health at http://localhost:8080/health

## Deploy to Railway
- Create a new Railway project and **Upload this folder** or connect to your repo containing it.
- Add environment variables defined in `.env.example` under **Variables**.
- Deploy. Health check path: `/health`

## API
- `GET /` index dashboard
- `GET /health` service status
- `POST /run` body: `{ "agent": "pricing", "payload": {...} }`
```json
{ "agent": "pricing", "result": {"base_price":199,"demand":1.2,"urgency":1.0,"price":238.8} }
```

## Structure
```
app.py
agents/            # pluggable async agents
services/          # db, cache, external clients
ui/                # minimal dashboard
tests/             # basic health test
Procfile, Dockerfile, railway.json, requirements.txt
```
