"""
SINCOR Production Scheduler
Real scheduler implementation using croniter and Redis streams
Runs daily triggers for content generation, health checks, and syndication
"""

import redis
import json
import time
import logging
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from croniter import croniter
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SincorScheduler:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.timezone = pytz.timezone('America/Chicago')  # Central time
        self.lock_key = "sincor:scheduler:lock"
        self.lock_timeout = 300  # 5 minutes
        
        # Define scheduled jobs with cron expressions
        self.jobs = {
            "daily_sample_pack": {
                "cron": "0 8 * * 1-5",  # 8 AM, Monday-Friday
                "description": "Generate daily sample content pack",
                "enabled": True
            },
            "daily_health_check": {
                "cron": "0 9 * * 1-5",  # 9 AM, Monday-Friday  
                "description": "Run system health diagnostics",
                "enabled": True
            },
            "syndication_retry": {
                "cron": "0 */4 * * *",  # Every 4 hours
                "description": "Retry failed syndication tasks",
                "enabled": True
            },
            "prospect_discovery": {
                "cron": "0 10 * * 1,3,5",  # 10 AM, Mon/Wed/Fri
                "description": "Discover new service business prospects",
                "enabled": True
            },
            "revenue_optimization": {
                "cron": "0 17 * * 1-5",  # 5 PM, Monday-Friday
                "description": "Optimize pricing and revenue metrics",
                "enabled": True
            }
        }
        
    def acquire_lock(self) -> bool:
        """Acquire distributed lock to prevent multiple schedulers"""
        identifier = str(uuid.uuid4())
        end_time = time.time() + self.lock_timeout
        
        while time.time() < end_time:
            if self.redis_client.set(self.lock_key, identifier, nx=True, ex=self.lock_timeout):
                return True
            time.sleep(0.001)
        return False
    
    def release_lock(self):
        """Release distributed lock"""
        self.redis_client.delete(self.lock_key)
    
    def get_next_run_times(self) -> Dict[str, datetime]:
        """Calculate next run times for all jobs"""
        now = datetime.now(self.timezone)
        next_runs = {}
        
        for job_id, job_config in self.jobs.items():
            if not job_config["enabled"]:
                continue
                
            cron = croniter(job_config["cron"], now)
            next_run = cron.get_next(datetime)
            next_runs[job_id] = next_run
            
        return next_runs
    
    def should_run_job(self, job_id: str, job_config: Dict[str, Any]) -> bool:
        """Check if job should run now"""
        if not job_config["enabled"]:
            return False
            
        now = datetime.now(self.timezone)
        
        # Check last run time
        last_run_key = f"sincor:scheduler:last_run:{job_id}"
        last_run_str = self.redis_client.get(last_run_key)
        
        if last_run_str:
            last_run = datetime.fromisoformat(last_run_str)
            # Don't run if we ran in the last 30 minutes
            if (now - last_run).total_seconds() < 1800:
                return False
        
        # Check if cron schedule says we should run
        cron = croniter(job_config["cron"], now)
        next_run = cron.get_next(datetime)
        prev_run = cron.get_prev(datetime)
        
        # Run if we're within 5 minutes of scheduled time and haven't run since then
        time_diff = abs((now - prev_run).total_seconds())
        should_run = time_diff < 300  # 5 minutes
        
        if should_run and last_run_str:
            last_run = datetime.fromisoformat(last_run_str)
            should_run = last_run < prev_run
            
        return should_run
    
    def mark_job_run(self, job_id: str):
        """Mark job as completed"""
        now = datetime.now(self.timezone)
        last_run_key = f"sincor:scheduler:last_run:{job_id}"
        self.redis_client.set(last_run_key, now.isoformat(), ex=86400)  # Expire after 24h
    
    def create_trigger_message(self, job_id: str, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create trigger message for job"""
        now = datetime.now(timezone.utc)
        trace_id = f"scheduler-{job_id}-{int(now.timestamp())}"
        correlation_id = f"job_{job_id}_{now.strftime('%Y%m%d_%H%M')}"
        
        # Create idempotency key based on job and date
        date_str = now.strftime('%Y-%m-%d')
        idempotency_key = hashlib.md5(f"{job_id}|{date_str}".encode()).hexdigest()
        
        # Job-specific payloads
        payloads = {
            "daily_sample_pack": {
                "mode": "daily_sample",
                "publish_live": True,
                "brand_id": "cad-clinton",
                "brief_source": "default:detailing:v3", 
                "channel_whitelist": ["instagram_feed", "google_business_profile"],
                "target_value": "$500"
            },
            "daily_health_check": {
                "check_type": "full_system",
                "components": ["agents", "queues", "revenue", "api_health"],
                "alert_threshold": 0.8
            },
            "syndication_retry": {
                "retry_failed_only": True,
                "max_retries": 3,
                "channels": ["instagram", "facebook", "google_business", "tiktok"]
            },
            "prospect_discovery": {
                "search_radius_miles": 50,
                "business_types": ["auto_detailing", "landscaping", "plumbing", "hvac"],
                "min_rating": 4.0,
                "location_center": "Clinton, IL"
            },
            "revenue_optimization": {
                "optimize_pricing": True,
                "analyze_margins": True,
                "update_ab_variants": True,
                "period_days": 7
            }
        }
        
        return {
            "type": "TRIGGER",
            "topic": job_id,
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
            "timestamp": now.isoformat(),
            "payload": payloads.get(job_id, {"job": job_id})
        }
    
    def publish_trigger(self, message: Dict[str, Any]):
        """Publish trigger message to Redis stream"""
        try:
            stream_name = "sincor.triggers"
            self.redis_client.xadd(stream_name, message)
            logger.info(f"Published trigger: {message['topic']} - {message['correlation_id']}")
        except Exception as e:
            logger.error(f"Failed to publish trigger {message['topic']}: {e}")
    
    def run_tick(self):
        """Single scheduler tick - check and run due jobs"""
        if not self.acquire_lock():
            logger.debug("Could not acquire scheduler lock, skipping tick")
            return
        
        try:
            jobs_run = 0
            for job_id, job_config in self.jobs.items():
                if self.should_run_job(job_id, job_config):
                    logger.info(f"Running scheduled job: {job_id}")
                    
                    # Create and publish trigger
                    message = self.create_trigger_message(job_id, job_config)
                    self.publish_trigger(message)
                    
                    # Mark as run
                    self.mark_job_run(job_id)
                    jobs_run += 1
            
            if jobs_run > 0:
                logger.info(f"Scheduler tick complete - ran {jobs_run} jobs")
            else:
                logger.debug("Scheduler tick complete - no jobs due")
                
        finally:
            self.release_lock()
    
    def run_daemon(self, tick_interval: int = 60):
        """Run scheduler daemon - tick every minute"""
        logger.info("SINCOR Scheduler daemon starting...")
        logger.info(f"Timezone: {self.timezone}")
        logger.info(f"Enabled jobs: {[j for j, c in self.jobs.items() if c['enabled']]}")
        
        while True:
            try:
                self.run_tick()
                time.sleep(tick_interval)
            except KeyboardInterrupt:
                logger.info("Scheduler daemon stopping...")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(tick_interval)
    
    def status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        now = datetime.now(self.timezone)
        next_runs = self.get_next_run_times()
        
        status = {
            "current_time": now.isoformat(),
            "timezone": str(self.timezone),
            "lock_acquired": bool(self.redis_client.exists(self.lock_key)),
            "jobs": {}
        }
        
        for job_id, job_config in self.jobs.items():
            last_run_key = f"sincor:scheduler:last_run:{job_id}"
            last_run_str = self.redis_client.get(last_run_key)
            
            status["jobs"][job_id] = {
                "enabled": job_config["enabled"],
                "cron": job_config["cron"],
                "description": job_config["description"],
                "last_run": last_run_str,
                "next_run": next_runs.get(job_id, "").isoformat() if next_runs.get(job_id) else None
            }
        
        return status

def main():
    """Main entry point for scheduler daemon"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SINCOR Scheduler")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--tick-interval", type=int, default=60, help="Tick interval in seconds")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--run-once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    scheduler = SincorScheduler(args.redis_url)
    
    if args.status:
        status = scheduler.status()
        print(json.dumps(status, indent=2))
        return
    
    if args.run_once:
        scheduler.run_tick()
        return
    
    # Run daemon
    scheduler.run_daemon(args.tick_interval)

if __name__ == "__main__":
    main()