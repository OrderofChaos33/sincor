#!/usr/bin/env python3
"""
SCHEDULE FACEBOOK ADS - AUTO START 8AM, STOP 8PM
"""
import schedule
import time
from datetime import datetime
import subprocess
import os

def start_ads():
    """Start Facebook ads at 8 AM"""
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] STARTING Facebook ads...")
    
    # Set environment variable to enable ads
    os.environ["ADS_ENABLED"] = "true"
    
    # Run the Facebook campaign script
    try:
        result = subprocess.run(["python", "facebook_auto_campaign.py"], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"[{current_time}] Facebook ads STARTED successfully")
        else:
            print(f"[{current_time}] Facebook ads start FAILED: {result.stderr}")
    except Exception as e:
        print(f"[{current_time}] Error starting ads: {e}")

def stop_ads():
    """Stop Facebook ads at 8 PM"""
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] STOPPING Facebook ads...")
    
    # Set environment variable to disable ads
    os.environ["ADS_ENABLED"] = "false"
    
    # You would need to implement ad pausing logic here
    # For now, just log the stop time
    print(f"[{current_time}] Facebook ads scheduled to STOP")

def main():
    print("CLINTON FACEBOOK ADS SCHEDULER")
    print("=" * 40)
    print("Schedule: 8:00 AM - 8:00 PM daily")
    print("Current time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()
    
    # Schedule daily start and stop
    schedule.every().day.at("08:00").do(start_ads)
    schedule.every().day.at("20:00").do(stop_ads)
    
    print("Scheduler running... Press Ctrl+C to stop")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")