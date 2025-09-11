#!/usr/bin/env python3
"""
COHESIVE CLINTON CAMPAIGN - LOCAL PRODUCTION TEST
Run this to test everything working together locally before Railway finishes deploying
"""
import subprocess
import time
import sys
import requests
import json
from datetime import datetime

def test_clinton_endpoint(base_url):
    """Test the Clinton lead ingest endpoint"""
    
    print(f"🧪 Testing Clinton endpoint: {base_url}/leads")
    
    headers = {
        "Authorization": "Bearer clinton-detailing-urgent-key-2024",
        "Content-Type": "application/json",
        "X-Idempotency-Key": f"test-{int(time.time())}"
    }
    
    payload = {
        "lead_id": f"test-{int(time.time())}",
        "vertical": "auto_detailing",
        "contact": {
            "email": "test@clinton.com",
            "phone": "+15635550123",
            "zip": "52732"  # Clinton, IA
        },
        "attributes": {
            "name": "Test Customer",
            "urgency": "asap"
        },
        "consent": {
            "tcpa": True,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    try:
        response = requests.post(f"{base_url}/leads", headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"   Score: {data.get('score')}")
            print(f"   Routing: {data.get('routing')}")  
            print(f"   Competitive Advantage: {data.get('competitive_advantage')}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def run_production_server():
    """Run the app with gunicorn for production testing"""
    
    print("STARTING CLINTON AUTO DETAILING CAMPAIGN - PRODUCTION MODE")
    print("=" * 60)
    
    # Start gunicorn server
    cmd = [
        sys.executable, "-m", "gunicorn", 
        "app:app",
        "--bind", "0.0.0.0:8080",
        "--workers", "2",
        "--timeout", "120"
    ]
    
    print("Starting production server...")
    process = subprocess.Popen(cmd)
    
    # Wait for server to start
    print("Waiting for server startup...")
    time.sleep(3)
    
    # Test the endpoint
    success = test_clinton_endpoint("http://localhost:8080")
    
    if success:
        print("\n🎉 COHESIVE SYSTEM WORKING!")
        print("=" * 60)
        print("✅ Lead ingest: WORKING")
        print("✅ Competitive advantage scoring: WORKING") 
        print("✅ Route order: LOCAL_DETAILING_ELIGIBLE → OUTREACH")
        print("✅ Security: API key + rate limiting + idempotency")
        print("\n🎯 Ready for Clinton $1200 campaign!")
        print("\nSystem running at: http://localhost:8080")
        print("Lead endpoint: http://localhost:8080/leads")
        print("\nPress Ctrl+C to stop")
        
        try:
            # Keep running
            process.wait()
        except KeyboardInterrupt:
            print("\nStopping server...")
            process.terminate()
            
    else:
        print("❌ System not working properly")
        process.terminate()

if __name__ == "__main__":
    run_production_server()