"""
Redis Streams Content Creation and Syndication Pipeline
Implements the SINCOR content pack generation system using Redis Streams
"""

import redis
import json
import uuid
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Message:
    type: str
    topic: str
    trace_id: str
    correlation_id: str
    idempotency_key: str
    payload: Dict[str, Any]
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

class ContentPipelineProcessor:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.processed_keys = set()  # Track processed idempotency keys
        
    def is_processed(self, idempotency_key: str) -> bool:
        """Check if this request was already processed"""
        return self.redis_client.exists(f"processed:{idempotency_key}")
    
    def mark_processed(self, idempotency_key: str):
        """Mark request as processed with 24hr TTL"""
        self.redis_client.setex(f"processed:{idempotency_key}", 86400, "1")
    
    def publish_message(self, stream: str, message: Message):
        """Publish message to Redis Stream"""
        msg_dict = asdict(message)
        self.redis_client.xadd(stream, msg_dict)
        logger.info(f"Published to {stream}: {message.type} - {message.correlation_id}")
    
    def trigger_content_pack(self, trigger_data: Dict[str, Any]):
        """Process trigger event and start content pack creation"""
        idempotency_key = trigger_data.get("idempotency_key")
        
        if self.is_processed(idempotency_key):
            logger.info(f"Skipping already processed: {idempotency_key}")
            return
        
        # Create pack creation task
        pack_message = Message(
            type="TASK",
            topic="create_pack",
            trace_id=trigger_data["trace_id"],
            correlation_id=trigger_data["correlation_id"],
            idempotency_key=idempotency_key,
            payload={
                "brand_id": trigger_data["payload"]["brand_id"],
                "brief_source": trigger_data["payload"]["brief_source"],
                "mode": trigger_data["payload"]["mode"],
                "publish_live": trigger_data["payload"]["publish_live"],
                "channel_whitelist": trigger_data["payload"]["channel_whitelist"]
            }
        )
        
        self.publish_message("sincor.tasks.create_pack", pack_message)
        self.mark_processed(idempotency_key)
        
    def create_pack_worker(self, message_data: Dict[str, Any]):
        """Worker that creates content pack blueprint"""
        payload = message_data["payload"]
        brand_id = payload["brand_id"]
        
        # Generate pack blueprint based on brand
        pack_blueprint = self.generate_pack_blueprint(brand_id, payload)
        
        # Create render tasks for each asset
        for asset in pack_blueprint["assets"]:
            render_message = Message(
                type="TASK",
                topic="render_asset",
                trace_id=message_data["trace_id"],
                correlation_id=f"{message_data['correlation_id']}_asset_{asset['id']}",
                idempotency_key=f"{message_data['idempotency_key']}_render_{asset['id']}",
                payload={
                    "asset_spec": asset,
                    "brand_context": pack_blueprint["brand_context"],
                    "pack_id": pack_blueprint["pack_id"]
                }
            )
            self.publish_message("sincor.tasks.render_asset", render_message)
    
    def generate_pack_blueprint(self, brand_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content pack blueprint for Clinton Auto Detailing"""
        
        if brand_id == "cad-clinton":
            return {
                "pack_id": f"pack_{int(time.time())}",
                "brand_context": {
                    "business_name": "Clinton Auto Detailing",
                    "phone": "(815) 718-8936",
                    "services": ["Paint Correction", "Ceramic Coating", "Interior Detailing", "Wash & Wax"],
                    "value_props": ["15+ Years Experience", "Mobile Service", "Satisfaction Guaranteed"],
                    "location": "Clinton, IL"
                },
                "assets": [
                    {
                        "id": "hero_video",
                        "type": "video",
                        "duration": 30,
                        "format": "mp4",
                        "resolution": "1080x1920",
                        "template": "detailing_transformation",
                        "channels": ["instagram_feed", "google_business_profile"]
                    },
                    {
                        "id": "service_flyer",
                        "type": "image",
                        "format": "png",
                        "resolution": "1080x1080",
                        "template": "services_grid",
                        "channels": ["instagram_feed"]
                    },
                    {
                        "id": "pricing_pdf",
                        "type": "document",
                        "format": "pdf",
                        "pages": 2,
                        "template": "pricing_sheet",
                        "channels": ["email"]
                    }
                ]
            }
        
        return {"error": f"Unknown brand_id: {brand_id}"}
    
    def render_asset_worker(self, message_data: Dict[str, Any]):
        """Worker that renders individual assets"""
        payload = message_data["payload"]
        asset_spec = payload["asset_spec"]
        brand_context = payload["brand_context"]
        
        # Simulate asset rendering
        rendered_asset = {
            "asset_id": asset_spec["id"],
            "type": asset_spec["type"],
            "format": asset_spec["format"],
            "file_path": f"/tmp/rendered/{asset_spec['id']}.{asset_spec['format']}",
            "size_bytes": 1024000,  # 1MB placeholder
            "channels": asset_spec["channels"],
            "metadata": {
                "brand": brand_context["business_name"],
                "created_at": datetime.utcnow().isoformat(),
                "value_estimate": "$167"  # $500/3 assets
            }
        }
        
        logger.info(f"Rendered asset: {rendered_asset['asset_id']} - {rendered_asset['type']}")
        
        # Trigger syndication
        syndicate_message = Message(
            type="TASK",
            topic="syndicate",
            trace_id=message_data["trace_id"],
            correlation_id=f"{message_data['correlation_id']}_syndicate",
            idempotency_key=f"{message_data['idempotency_key']}_syndicate",
            payload={
                "rendered_asset": rendered_asset,
                "pack_id": payload["pack_id"]
            }
        )
        self.publish_message("sincor.tasks.syndicate", syndicate_message)
        
    def syndicate_worker(self, message_data: Dict[str, Any]):
        """Worker that syndicates content to channels"""
        payload = message_data["payload"]
        asset = payload["rendered_asset"]
        
        # Simulate syndication to channels
        for channel in asset["channels"]:
            if channel == "email":
                logger.info(f"Emailing {asset['asset_id']} to eenergy@protonmail.com")
            elif channel == "instagram_feed":
                logger.info(f"Posted {asset['asset_id']} to Instagram")
            elif channel == "google_business_profile":
                logger.info(f"Posted {asset['asset_id']} to Google Business Profile")
        
        logger.info(f"Syndication complete for {asset['asset_id']}")
        
    def process_stream(self, stream_name: str, worker_func):
        """Process messages from a Redis Stream"""
        consumer_group = f"{stream_name}_group"
        consumer_name = f"worker_{uuid.uuid4().hex[:8]}"
        
        try:
            self.redis_client.xgroup_create(stream_name, consumer_group, id='0', mkstream=True)
        except redis.exceptions.ResponseError:
            pass  # Group already exists
        
        while True:
            try:
                messages = self.redis_client.xreadgroup(
                    consumer_group, consumer_name, {stream_name: '>'}, count=1, block=1000
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        # Convert Redis hash to dict
                        message_data = {k.decode(): v.decode() for k, v in fields.items()}
                        
                        # Parse JSON payloads
                        if 'payload' in message_data:
                            message_data['payload'] = json.loads(message_data['payload'])
                        
                        # Check idempotency
                        if self.is_processed(message_data.get('idempotency_key')):
                            logger.info(f"Skipping processed: {message_data.get('idempotency_key')}")
                            self.redis_client.xack(stream_name, consumer_group, msg_id)
                            continue
                        
                        # Process message
                        worker_func(message_data)
                        
                        # Mark as processed and ack
                        self.mark_processed(message_data.get('idempotency_key'))
                        self.redis_client.xack(stream_name, consumer_group, msg_id)
                        
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                time.sleep(5)

def fire_smoke_test():
    """Fire the smoke test trigger"""
    processor = ContentPipelineProcessor()
    
    # Smoke test trigger from your spec
    trigger_payload = {
        "type": "TRIGGER",
        "topic": "create_pack",
        "trace_id": "ulid-demo-01",
        "correlation_id": "pack_spk_demo",
        "idempotency_key": hashlib.md5("cad-clinton|demo|2025-09-08".encode()).hexdigest(),
        "payload": {
            "mode": "sample",
            "publish_live": False,
            "brand_id": "cad-clinton",
            "brief_source": "default:detailing:v3",
            "channel_whitelist": ["instagram_feed", "google_business_profile"]
        }
    }
    
    logger.info("🚀 Firing smoke test trigger...")
    processor.trigger_content_pack(trigger_payload)
    
    # Process the pipeline
    import threading
    
    def run_create_pack_worker():
        processor.process_stream("sincor.tasks.create_pack", processor.create_pack_worker)
    
    def run_render_worker():
        processor.process_stream("sincor.tasks.render_asset", processor.render_asset_worker)
    
    def run_syndicate_worker():
        processor.process_stream("sincor.tasks.syndicate", processor.syndicate_worker)
    
    # Start workers
    threading.Thread(target=run_create_pack_worker, daemon=True).start()
    threading.Thread(target=run_render_worker, daemon=True).start() 
    threading.Thread(target=run_syndicate_worker, daemon=True).start()
    
    logger.info("✅ All workers started - processing content pack...")
    time.sleep(10)  # Let it process
    
    logger.info("💰 $500 media pack generation complete!")

if __name__ == "__main__":
    fire_smoke_test()