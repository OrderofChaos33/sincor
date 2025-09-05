import os, asyncio, json, yaml
from fastapi import FastAPI
from libs.pkg_bus.bus import redis, consume, xadd, STREAM_SCORED, STREAM_ROUTE, STREAM_DELIVERED
from libs.pkg_rules.engine import evaluate_rules

CONFIG_DIR = os.getenv("CONFIG_DIR","/app/config")
with open(os.path.join(CONFIG_DIR, "routing/smartlists.yaml")) as f:
    SMART = yaml.safe_load(f)

app = FastAPI()

def eligible_lists(lead: dict):
    payload = {"lead": lead}
    out = []
    for l in SMART["lists"]:
        if evaluate_rules(payload, l["rules"]):
            out.append(l["name"])
    return out

async def deliver(lead: dict, dest: str):
    # simple adapter dispatch
    if dest == "LOCAL_DETAILING_ELIGIBLE":
        from adapters.local_booking import send_to_booking
        return await send_to_booking(lead)
    elif dest == "SAAS_ELIGIBLE":
        from adapters.saas_checkout import send_to_saas
        return await send_to_saas(lead)
    else:
        from adapters.outreach_queue import enqueue_outreach
        return await enqueue_outreach(lead)

async def handler(msg):
    lead = msg["lead"]
    lists = eligible_lists(lead)
    destination = "OUTREACH" if not lists else lists[0]  # pick first match for MVP
    res = await deliver(lead, destination)
    await xadd(await redis(), STREAM_DELIVERED, {"lead_id": lead["lead_id"], "destination": destination, "result": res})

@app.get("/health")
async def health(): return {"ok": True}

async def main():
    r = await redis()
    await consume(r, STREAM_SCORED, "g.router", "router-1", handler)

if __name__ == "__main__":
    asyncio.run(main())