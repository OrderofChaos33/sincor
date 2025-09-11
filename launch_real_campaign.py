#!/usr/bin/env python3
"""
REAL CLINTON CAMPAIGN - DRIVE TO ACTUAL BOOKING PAGE
All traffic goes to clintondetailing.com/booking (your Square system)
"""
import webbrowser
import json

def main():
    phone = "(815) 718-8936"
    booking_url = "https://clintondetailing.com/booking"  # REAL conversion page
    
    print("CLINTON CAMPAIGN - REAL BOOKING PAGE")
    print("=" * 50)
    print(f"Phone: {phone}")
    print(f"REAL Booking Page: {booking_url}")
    print()
    
    # Test the real booking page
    print("Opening REAL booking page...")
    webbrowser.open(booking_url)
    
    # Open Google Business for manual post
    print("Opening Google Business...")
    webbrowser.open("https://business.google.com/")
    
    print()
    print("GOOGLE BUSINESS POST (copy this exactly):")
    print("-" * 40)
    print("WEEKEND SPECIAL: $25 OFF Auto Detailing")
    print("Licensed & Insured - Clinton's Only Professional")
    print("Mobile service - we come to you")
    print("Only 6 slots available this weekend")
    print(f"Call: {phone}")
    print(f"Book online: {booking_url}")
    print("Offer ends Sunday 11:59 PM")
    print("-" * 40)
    print()
    
    # Facebook Lead Ad config - sends to REAL booking page
    fb_config = {
        "campaign_name": "Clinton Auto Detailing - Weekend Special",
        "objective": "LEAD_GENERATION",
        "budget": 20,  # $20/day
        "targeting": {
            "location": "Clinton, IA",
            "radius": 15,
            "interests": ["Car ownership", "Auto services"]
        },
        "ad_copy": {
            "headline": "Licensed Auto Detail Pro - $25 OFF",
            "text": "Clinton's only licensed & insured auto detailing. Weekend special - $25 off full detail. Mobile service available.",
            "cta": "Learn More"
        },
        "lead_form": {
            "fields": ["Name", "Phone", "Email"],
            "thank_you_url": booking_url,  # Redirect to REAL booking
            "privacy_policy": "https://clintondetailing.com/privacy"
        }
    }
    
    # Save FB config
    with open("facebook_real_campaign.json", "w") as f:
        json.dump(fb_config, f, indent=2)
    
    print("FACEBOOK SETUP:")
    print("1. Go to facebook.com/adsmanager")
    print("2. Create Lead Generation campaign")
    print(f"3. Target: Clinton, IA + 15 miles, Budget: ${fb_config['budget']}/day")
    print(f"4. Headline: '{fb_config['ad_copy']['headline']}'")
    print(f"5. Text: '{fb_config['ad_copy']['text']}'")
    print("6. Lead form: Name, Phone, Email required")
    print(f"7. Thank you page: {booking_url}")
    print()
    print("RESULT: All leads go straight to your Square booking system!")

if __name__ == "__main__":
    main()