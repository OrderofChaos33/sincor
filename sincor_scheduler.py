#!/usr/bin/env python3
"""
SINCOR SYSTEM SCHEDULER - 8AM-5PM M-F EASTERN TIME
"""
import schedule
import time
import subprocess
import os
from datetime import datetime
import pytz

def start_sincor_system():
    """Start all SINCOR outreach engines at 8 AM Eastern"""
    eastern = pytz.timezone('US/Eastern')
    current_time = datetime.now(eastern).strftime('%H:%M:%S EST')
    print(f"[{current_time}] STARTING SINCOR SYSTEM - BUSINESS HOURS ACTIVE")
    
    # Start all engines
    try:
        subprocess.Popen(["python", "automated_media_pack_system.py"])
        subprocess.Popen(["python", "services/voice_hub/app.py"])  
        print(f"[{current_time}] All SINCOR engines started")
    except Exception as e:
        print(f"[{current_time}] Error starting engines: {e}")

def stop_sincor_system():
    """Stop SINCOR system at 5 PM Eastern"""
    eastern = pytz.timezone('US/Eastern')
    current_time = datetime.now(eastern).strftime('%H:%M:%S EST')
    print(f"[{current_time}] STOPPING SINCOR SYSTEM - END OF BUSINESS HOURS")

def main():
    print("SINCOR AUTOMATED SCHEDULER")
    print("=" * 40)
    print("Schedule: 8:00 AM - 5:00 PM Eastern Time, Monday-Friday")
    print("Current time:", datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S EST'))
    print()
    
    # Schedule SINCOR to run business hours only
    schedule.every().monday.at("08:00").do(start_sincor_system)
    schedule.every().tuesday.at("08:00").do(start_sincor_system)
    schedule.every().wednesday.at("08:00").do(start_sincor_system)
    schedule.every().thursday.at("08:00").do(start_sincor_system)
    schedule.every().friday.at("08:00").do(start_sincor_system)
    
    schedule.every().monday.at("17:00").do(stop_sincor_system)
    schedule.every().tuesday.at("17:00").do(stop_sincor_system)
    schedule.every().wednesday.at("17:00").do(stop_sincor_system)
    schedule.every().thursday.at("17:00").do(stop_sincor_system)
    schedule.every().friday.at("17:00").do(stop_sincor_system)
    
    print("SINCOR scheduler running... Press Ctrl+C to stop")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSINCOR Scheduler stopped.")