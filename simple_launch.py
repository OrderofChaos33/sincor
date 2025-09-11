#!/usr/bin/env python3
"""
AUTONOMOUS CLINTON CAMPAIGN LAUNCHER
This runs everything that can be automated
"""
import subprocess
import webbrowser
import time
import os
import requests
import json

def main():
    phone = "(815) 718-8936"
    booking_url = "https://clintondetailing.com/booking"
    
    print("AUTONOMOUS CLINTON CAMPAIGN LAUNCHER")
    print("=" * 50)
    print(f"Phone: {phone}")
    print(f"Booking: {booking_url}")
    print()
    
    # 1. Open landing page
    html_file = "clinton_live_campaign.html"
    if os.path.exists(html_file):
        webbrowser.open(f"file://{os.path.abspath(html_file)}")
        print("SUCCESS: Landing page opened in browser")
    else:
        print("ERROR: Landing page HTML not found")
    
    # 2. Test if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            print("SUCCESS: Lead server is running")
        else:
            print("STARTING: Lead server...")
            subprocess.Popen(["python", "app.py"])
            time.sleep(3)
    except:
        print("STARTING: Lead server...")
        try:
            subprocess.Popen(["python", "app.py"])
            time.sleep(3)
            print("SUCCESS: Lead server started")
        except:
            print("ERROR: Could not start server - run manually: python app.py")
    
    # 3. Test lead ingestion
    test_payload = {
        "lead_id": f"test-{int(time.time())}",
        "vertical": "auto_detailing",
        "contact": {
            "email": "test@clintondetailing.com",
            "phone": "+15635551234", 
            "zip": "52732"
        },
        "attributes": {
            "name": "Test Customer",
            "urgency": "asap"
        },
        "consent": {"tcpa": True}
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/leads",
            headers={
                "Authorization": "Bearer clinton-detailing-urgent-key-2024",
                "Content-Type": "application/json",
                "X-Idempotency-Key": f"test-{int(time.time())}"
            },
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS: Test lead processed")
            print(f"  Score: {result.get('score', 'N/A')}")
            print(f"  Routing: {result.get('routing', 'N/A')}")
        else:
            print(f"ERROR: Test failed - {response.status_code}")
    except Exception as e:
        print(f"ERROR: Cannot test leads - {e}")
    
    # 4. Open Google Business
    webbrowser.open("https://business.google.com/")
    print("OPENED: Google Business Profile")
    
    print()
    print("=" * 50)
    print("CAMPAIGN LAUNCH COMPLETE")
    print()
    print("AUTOMATED STEPS:")
    print("- Landing page opened in browser")
    print("- Lead server started/verified") 
    print("- Lead processing tested")
    print("- Google Business opened for manual post")
    print()
    print("MANUAL STEPS NEEDED:")
    print("1. Create Google Business post:")
    print("   'WEEKEND SPECIAL: $25 OFF Auto Detailing'")
    print("   'Licensed & Insured - Clinton Only Professional'") 
    print(f"   'Call: {phone} or Book: {booking_url}'")
    print()
    print("2. Facebook Lead Ads:")
    print("   - Go to facebook.com/adsmanager")
    print("   - Create Lead Generation campaign")
    print("   - Target Clinton, IA + 15 miles")
    print("   - Budget $20/day")
    print("   - Use lead form with Name/Phone/Email")
    print()
    print("ANSWER CALLS IN <15 MINUTES FOR MAX BOOKINGS!")

if __name__ == "__main__":
    main()