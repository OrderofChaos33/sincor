# SINCOR Minimal Kernel

Agent-first skeleton with:
- **Gateway** (FastAPI) for dispatching tasks
- **LeadGen Agent**: service + Redis-backed worker
- **Commons**: queue client and model router (Ollama fallback → stub)
- **Dev infra** via `docker-compose.dev.yml`: Redis, Qdrant, NATS (optional)

> Temporal/NATS can be layered in later. This runs *today* with only Redis.

## Quickstart

Terminal A – infra (optional but recommended):
```bash
cd sincor_kernel_min
cp .env.example .env
docker compose -f docker-compose.dev.yml up
```

Terminal B – gateway:
```bash
cd gateway
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Terminal C – leadgen service:
```bash
cd ../agents/leadgen/service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Terminal D – leadgen worker:
```bash
cd ../worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Dispatch a test job:
```bash
curl -X POST http://localhost:8000/dispatch \  -H "Content-Type: application/json" \  -d '{"task_type":"leadgen","payload":{"name":"John","vehicle":"Mustang GT","service":"Full detail"}}'
```

Watch the worker log for the generated blurb.

## Next steps
- Add **auth (JWT)** to gateway.
- Add **persistence** (Postgres) and a **vector layer** (Qdrant) for leads/content.
- Swap Redis queue for **NATS** or **Dramatiq** if you want typed actors.
- Add more agents: `media_pack`, `oversight`, `compliance` similarly.
