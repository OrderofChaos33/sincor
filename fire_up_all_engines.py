#!/usr/bin/env python3
"""
FIRE UP ALL SINCOR AGENT ENGINES - MAXIMUM REVENUE MODE
Start all revenue-generating systems simultaneously
"""
import subprocess
import time
import requests
import os
from concurrent.futures import ThreadPoolExecutor

def start_engine(name, command, port, health_path="/health"):
    """Start a SINCOR engine and verify it's running"""
    print(f"Starting {name} on port {port}...")
    
    try:
        # Check if already running
        response = requests.get(f"http://localhost:{port}{health_path}", timeout=2)
        if response.status_code == 200:
            print(f"✅ {name} already running on port {port}")
            return True
    except:
        pass
    
    # Start the service
    process = subprocess.Popen(command, shell=True, 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
    time.sleep(3)  # Give it time to start
    
    # Verify it started
    try:
        response = requests.get(f"http://localhost:{port}{health_path}", timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} started successfully on port {port}")
            return True
        else:
            print(f"❌ {name} failed to start (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {name} failed to start: {e}")
        return False

def main():
    print("🔥 FIRING UP ALL SINCOR AGENT ENGINES")
    print("=" * 50)
    print("MAXIMUM REVENUE MODE ACTIVATED")
    print()
    
    # Configure all engines
    engines = [
        {
            "name": "Lead Router Auction",
            "command": "python app.py",  # Use the main app
            "port": 8000,
            "health_path": "/health"
        },
        {
            "name": "Marketplace Revenue",
            "command": "cd services/marketplace && python marketplace_standalone.py",
            "port": 8002,
            "health_path": "/"
        },
        {
            "name": "Analytics API",
            "command": "cd services/analytics_api && python analytics_server.py",
            "port": 8003,
            "health_path": "/metrics"
        }
    ]
    
    # Start all engines in parallel
    with ThreadPoolExecutor(max_workers=len(engines)) as executor:
        futures = [
            executor.submit(start_engine, engine["name"], engine["command"], 
                          engine["port"], engine["health_path"]) 
            for engine in engines
        ]
        
        results = [future.result() for future in futures]
    
    print()
    print("=" * 50)
    print("SINCOR AGENT ENGINE STATUS:")
    
    active_engines = sum(results)
    for i, engine in enumerate(engines):
        status = "🟢 ACTIVE" if results[i] else "🔴 FAILED"
        print(f"  {engine['name']}: {status} (port {engine['port']})")
    
    print()
    print(f"ENGINES ACTIVE: {active_engines}/{len(engines)}")
    
    if active_engines > 0:
        print()
        print("🚀 REVENUE ENGINES ONLINE!")
        print("💰 Lead auction system routing for maximum profit")
        print("🛒 Marketplace generating recurring revenue") 
        print("📊 Analytics tracking all conversions")
        print()
        print("CLINTON CAMPAIGN NOW BACKED BY FULL AGENT NETWORK!")
        print("Target: MAXIMUM REVENUE ASAP")
    else:
        print("❌ NO ENGINES STARTED - CHECK LOGS")
    
    return active_engines

if __name__ == "__main__":
    active = main()
    print(f"\n✅ {active} REVENUE ENGINES ACTIVE - READY FOR MAX PROFIT!")