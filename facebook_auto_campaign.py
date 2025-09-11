#!/usr/bin/env python3
"""
AUTO-CREATE FACEBOOK LEAD AD CAMPAIGN
This will automatically create the Facebook campaign if you have API access
"""
import os
import requests
import json
from datetime import datetime, timedelta

def create_facebook_campaign():
    # Get tokens from environment or prompt
    access_token = os.getenv("FB_ACCESS_TOKEN", "")
    ad_account_id = os.getenv("FB_AD_ACCOUNT_ID", "")
    page_id = os.getenv("FB_PAGE_ID", "")
    
    if not access_token or not ad_account_id or not page_id:
        print("FACEBOOK API SETUP NEEDED:")
        print("1. Go to https://developers.facebook.com/tools/explorer/")
        print("2. Get access token with ads_management permission")
        print("3. Set environment variables:")
        print("   set FB_ACCESS_TOKEN=your_token")
        print("   set FB_AD_ACCOUNT_ID=act_your_account_id")  
        print("   set FB_PAGE_ID=your_page_id")
        print()
        print("OR manually create at facebook.com/adsmanager")
        return False
    
    base_url = "https://graph.facebook.com/v18.0"
    
    # 1. Create Campaign
    campaign_data = {
        "name": f"Clinton Auto Detailing - Weekend Special - {datetime.now().strftime('%m/%d')}",
        "objective": "LEAD_GENERATION",
        "status": "ACTIVE",
        "access_token": access_token
    }
    
    try:
        campaign_response = requests.post(f"{base_url}/{ad_account_id}/campaigns", data=campaign_data)
        campaign_id = campaign_response.json().get("id")
        
        if not campaign_id:
            print(f"Campaign creation failed: {campaign_response.text}")
            return False
            
        print(f"Campaign created: {campaign_id}")
        
        # 2. Create Ad Set
        end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        adset_data = {
            "name": "Clinton IA Auto Detailing - 15 mile radius",
            "campaign_id": campaign_id,
            "daily_budget": 2000,  # $20.00 in cents
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "LEAD_GENERATION",
            "targeting": json.dumps({
                "geo_locations": {
                    "custom_locations": [{
                        "latitude": 41.8444,
                        "longitude": -90.1887,
                        "radius": 15,
                        "distance_unit": "mile"
                    }]
                },
                "age_min": 25,
                "age_max": 65,
                "interests": [
                    {"id": "6003107902433", "name": "Cars"},
                    {"id": "6004037777609", "name": "Automotive industry"}
                ]
            }),
            "status": "ACTIVE",
            "start_time": (datetime.now().replace(hour=8, minute=0, second=0) + timedelta(days=1 if datetime.now().hour >= 20 else 0)).strftime('%Y-%m-%dT%H:%M:%S'),
            "end_time": f"{end_date}T20:00:00",
            "access_token": access_token
        }
        
        adset_response = requests.post(f"{base_url}/{ad_account_id}/adsets", data=adset_data)
        adset_id = adset_response.json().get("id")
        
        if not adset_id:
            print(f"Ad Set creation failed: {adset_response.text}")
            return False
            
        print(f"Ad Set created: {adset_id}")
        
        # 3. Create Lead Form
        leadform_data = {
            "name": "Clinton Auto Detailing - Contact Form",
            "questions": json.dumps([
                {"type": "FULL_NAME"},
                {"type": "PHONE"},
                {"type": "EMAIL"}
            ]),
            "privacy_policy_url": "https://clintondetailing.com/privacy",
            "follow_up_action_url": "https://clintondetailing.com/booking",
            "page_id": page_id,
            "access_token": access_token
        }
        
        leadform_response = requests.post(f"{base_url}/{page_id}/leadgen_forms", data=leadform_data)
        leadform_id = leadform_response.json().get("id")
        
        if not leadform_id:
            print(f"Lead Form creation failed: {leadform_response.text}")
            return False
            
        print(f"Lead Form created: {leadform_id}")
        
        # 4. Create Ad Creative
        creative_data = {
            "name": "Clinton Auto Detailing - Weekend Special",
            "object_story_spec": json.dumps({
                "page_id": page_id,
                "link_data": {
                    "message": "Clinton's only licensed & insured auto detailing. Weekend special - $25 off full detail. Mobile service available.",
                    "name": "Licensed Auto Detail Pro - $25 OFF",
                    "description": "Book your weekend detail now - only 6 slots available!",
                    "call_to_action": {
                        "type": "LEARN_MORE"
                    }
                }
            }),
            "degrees_of_freedom_spec": json.dumps({
                "creative_features_spec": {
                    "standard_enhancements": {
                        "enroll_status": "OPT_IN"
                    }
                }
            }),
            "access_token": access_token
        }
        
        creative_response = requests.post(f"{base_url}/{ad_account_id}/adcreatives", data=creative_data)
        creative_id = creative_response.json().get("id")
        
        if not creative_id:
            print(f"Creative creation failed: {creative_response.text}")
            return False
            
        print(f"Ad Creative created: {creative_id}")
        
        # 5. Create Ad
        ad_data = {
            "name": "Clinton Auto Detailing - Weekend Special Ad",
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "ACTIVE",
            "access_token": access_token
        }
        
        ad_response = requests.post(f"{base_url}/{ad_account_id}/ads", data=ad_data)
        ad_id = ad_response.json().get("id")
        
        if not ad_id:
            print(f"Ad creation failed: {ad_response.text}")
            return False
            
        print(f"Ad created: {ad_id}")
        print()
        print("FACEBOOK CAMPAIGN LIVE!")
        print(f"Campaign ID: {campaign_id}")
        print("Budget: $20/day")
        print("Target: Clinton, IA + 15 miles")
        print("All leads go to: https://clintondetailing.com/booking")
        
        return True
        
    except Exception as e:
        print(f"Error creating campaign: {e}")
        return False

if __name__ == "__main__":
    success = create_facebook_campaign()
    if not success:
        print()
        print("MANUAL SETUP REQUIRED:")
        print("Go to facebook.com/adsmanager and create manually")