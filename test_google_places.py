#!/usr/bin/env python3
"""
Test Google Places API for SINCOR Business Prospecting
"""
import requests
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def test_google_places():
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in .env file")
        return
    
    # Test search for service businesses
    search_queries = [
        "auto detailing Clinton Iowa",
        "HVAC repair Iowa", 
        "plumbing services Illinois",
        "roofing contractor Quad Cities"
    ]
    
    print("TESTING GOOGLE PLACES API FOR SINCOR BUSINESS PROSPECTING")
    print("=" * 60)
    
    for query in search_queries:
        print(f"\nSearching: {query}")
        
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": api_key,
            "type": "establishment"
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data["status"] == "OK":
                results = data["results"][:3]  # First 3 results
                print(f"  Found {len(data['results'])} businesses")
                
                for business in results:
                    name = business.get("name")
                    address = business.get("formatted_address", "No address")
                    rating = business.get("rating", "No rating")
                    
                    print(f"    - {name}")
                    print(f"      {address}")
                    print(f"      Rating: {rating}")
                    
                    # Get place details for phone/website
                    place_id = business.get("place_id")
                    if place_id:
                        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                        details_params = {
                            "place_id": place_id,
                            "fields": "formatted_phone_number,website,business_status",
                            "key": api_key
                        }
                        
                        details_response = requests.get(details_url, params=details_params)
                        details_data = details_response.json()
                        
                        if details_data["status"] == "OK":
                            result = details_data["result"]
                            phone = result.get("formatted_phone_number", "No phone")
                            website = result.get("website", "No website")
                            status = result.get("business_status", "Unknown")
                            
                            print(f"      Phone: {phone}")
                            print(f"      Website: {website}")
                            print(f"      Status: {status}")
                            print()
            else:
                print(f"  ERROR: {data['status']}")
                if "error_message" in data:
                    print(f"  Message: {data['error_message']}")
        
        except Exception as e:
            print(f"  Exception: {e}")
    
    print("=" * 60)
    print("✅ Google Places API test complete!")
    print("🎯 Ready to prospect service businesses automatically!")

if __name__ == "__main__":
    test_google_places()