"""
Test SINCOR Scheduler without Redis
Demonstrates scheduler functionality and trigger generation
"""

import json
from datetime import datetime
import pytz
from sincor_scheduler import SincorScheduler

class MockRedis:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        self.streams = {}
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, nx=None, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True
    
    def delete(self, key):
        self.data.pop(key, None)
    
    def exists(self, key):
        return key in self.data
    
    def xadd(self, stream, message):
        if stream not in self.streams:
            self.streams[stream] = []
        self.streams[stream].append(message)
        print(f"TRIGGER PUBLISHED to {stream}:")
        print(json.dumps(message, indent=2))

def test_scheduler():
    """Test scheduler trigger generation"""
    print("Testing SINCOR Scheduler...")
    
    # Create scheduler with mock Redis
    scheduler = SincorScheduler()
    scheduler.redis_client = MockRedis()
    
    # Show status
    print("\nScheduler Status:")
    status = scheduler.status()
    for job_id, job_info in status["jobs"].items():
        if job_info["enabled"]:
            print(f"  {job_id}: {job_info['description']}")
            print(f"   Cron: {job_info['cron']}")
            print(f"   Next: {job_info['next_run']}")
    
    # Test trigger creation for each job type
    print("\nTesting Trigger Generation:")
    
    for job_id, job_config in scheduler.jobs.items():
        if job_config["enabled"]:
            print(f"\n--- {job_id.upper()} TRIGGER ---")
            message = scheduler.create_trigger_message(job_id, job_config)
            scheduler.publish_trigger(message)
    
    print("\nScheduler test complete!")
    
    # Show what would be published
    print(f"\nMock streams contain {len(scheduler.redis_client.streams.get('sincor.triggers', []))} triggers")

if __name__ == "__main__":
    test_scheduler()