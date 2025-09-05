import asyncio, json, os
import aioredis

STREAM_IN = os.getenv("STREAM_IN", "stream.leads.received")
STREAM_CLEANED = "stream.leads.cleaned"
STREAM_SCORED = "stream.leads.scored"
STREAM_ROUTE = "stream.leads.route"
STREAM_DELIVERED = "stream.leads.delivered"

async def redis():
    return await aioredis.from_url(os.getenv("REDIS_URL","redis://localhost:6379/0"))

async def xadd(r, stream, data: dict):
    return await r.xadd(stream, {"data": json.dumps(data)})

async def consume(r, stream, group, consumer, handler):
    try:
        await r.xgroup_create(stream, group, id="$", mkstream=True)
    except Exception:
        pass
    while True:
        msgs = await r.xreadgroup(group, consumer, streams={stream: ">"}, count=10, latest_ids=None, timeout=5000)
        if not msgs: 
            continue
        for s, entries in msgs:
            for msg_id, fields in entries:
                data = json.loads(fields[b"data"].decode())
                try:
                    await handler(data)
                    await r.xack(stream, group, msg_id)
                except Exception as e:
                    # dead-letter or log; keep simple for scaffold
                    await r.xack(stream, group, msg_id)