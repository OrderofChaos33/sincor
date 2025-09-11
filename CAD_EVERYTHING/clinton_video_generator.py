"""
Clinton Auto Detailing Video Generator
Creates actual MP4 video files using AI video generation APIs
"""

import requests
import json
import time
import os
from datetime import datetime

class ClintonVideoGenerator:
    def __init__(self):
        self.business_name = "Clinton Auto Detailing"
        self.phone = "(815) 718-8936"
        self.location = "Clinton, IL"
        self.services = ["Paint Correction", "Ceramic Coating", "Interior Detailing", "Wash & Wax"]
        
        # Video specifications
        self.videos = {
            "business_intro": {
                "duration": 90,
                "title": "Business Introduction Video",
                "script": self.get_business_intro_script()
            },
            "service_showcase": {
                "duration": 60,
                "title": "Service Showcase Reel",
                "script": self.get_service_showcase_script()
            },
            "customer_testimonial": {
                "duration": 45,
                "title": "Customer Testimonial Story",
                "script": self.get_testimonial_script()
            },
            "before_after": {
                "duration": 30,
                "title": "Before/After Transformation",
                "script": self.get_before_after_script()
            },
            "behind_scenes": {
                "duration": 60,
                "title": "Behind-the-Scenes Process",
                "script": self.get_behind_scenes_script()
            },
            "call_to_action": {
                "duration": 30,
                "title": "Call-to-Action Conversion Video",
                "script": self.get_cta_script()
            }
        }

    def get_business_intro_script(self):
        return f"""
        Welcome to {self.business_name}, your premier auto detailing service in {self.location}.

        For over a decade, we've been transforming vehicles with our professional detailing services. 
        Our team specializes in paint correction, ceramic coating, interior detailing, and complete wash and wax services.

        At {self.business_name}, we don't just clean your car - we restore its beauty and protect your investment. 
        Every vehicle receives our signature attention to detail, using only premium products and proven techniques.

        Whether you drive a luxury sedan, family SUV, or classic car, our experienced technicians treat every vehicle 
        like it's our own. We take pride in delivering results that exceed your expectations.

        Ready to experience the {self.business_name} difference? Call us today at {self.phone} to schedule your appointment. 
        Your car deserves the best, and that's exactly what we deliver - every single time.

        {self.business_name} - Where Excellence Meets Your Expectations.
        """

    def get_service_showcase_script(self):
        return f"""
        Discover the complete range of premium services at {self.business_name}.

        Paint Correction: Our certified technicians remove swirl marks, scratches, and oxidation, 
        restoring your vehicle's paint to showroom condition.

        Ceramic Coating: Protect your investment with our professional-grade ceramic coating. 
        Long-lasting protection against UV rays, chemicals, and environmental contaminants.

        Interior Detailing: From leather conditioning to carpet deep cleaning, we revitalize every 
        surface inside your vehicle with meticulous care.

        Wash & Wax: Our signature service combines thorough exterior cleaning with premium wax protection, 
        leaving your car with an incredible shine.

        Every service is performed by trained professionals using top-tier products and equipment. 
        We guarantee satisfaction with every detail.

        Experience the difference professional detailing makes. Call {self.phone} today.
        {self.business_name} - Premium Care for Your Vehicle.
        """

    def get_testimonial_script(self):
        return f"""
        "I've been taking my cars to {self.business_name} for three years now, and they never disappoint. 
        The team is professional, thorough, and truly cares about the quality of their work.

        My BMW was looking tired after years of daily driving. The paint correction service they provided 
        was incredible - it looks better than when I bought it new. The attention to detail is unmatched.

        What sets {self.business_name} apart is their commitment to customer satisfaction. They explain 
        every step of the process and always deliver on their promises. 

        The ceramic coating has been worth every penny. Six months later, my car still looks amazing 
        and cleaning is so much easier. I recommend {self.business_name} to everyone I know.

        If you want the best auto detailing in {self.location}, there's only one choice. 
        Call {self.phone} and experience the difference for yourself."

        - Satisfied Customer, {self.business_name}
        """

    def get_before_after_script(self):
        return f"""
        This is the power of professional detailing at {self.business_name}.

        Before: Oxidized paint, swirl marks, and years of neglect. This vehicle had lost its original beauty.

        After: Complete transformation through our paint correction and ceramic coating process. 
        The results speak for themselves.

        Our systematic approach removes imperfections while protecting your vehicle for the future. 
        Every scratch tells a story, but it doesn't have to be permanent.

        See what {self.business_name} can do for your vehicle. 
        Call {self.phone} to schedule your transformation today.

        {self.business_name} - Bringing Your Car Back to Life.
        """

    def get_behind_scenes_script(self):
        return f"""
        Go behind the scenes at {self.business_name} and discover our meticulous process.

        Step 1: Thorough inspection and documentation. We assess every detail before we begin.

        Step 2: Safe washing using the two-bucket method and premium microfiber towels. 
        Protecting your paint starts with proper technique.

        Step 3: Clay bar treatment removes bonded contaminants that washing can't eliminate.

        Step 4: Paint correction using professional-grade compounds and polishes. 
        Our certified technicians have years of experience perfecting this art.

        Step 5: Protection application - whether ceramic coating, sealant, or premium wax. 
        We use only the finest products for long-lasting results.

        Quality takes time, and we never rush the process. Every step is performed with precision 
        because your vehicle deserves nothing less than perfection.

        Experience the {self.business_name} difference. Call {self.phone} today.
        """

    def get_cta_script(self):
        return f"""
        Don't let another day pass with a vehicle that doesn't reflect your standards.

        {self.business_name} is ready to transform your car with our premium detailing services. 
        Paint correction, ceramic coating, interior detailing - we do it all.

        Call NOW at {self.phone} to schedule your appointment. 
        Our calendar fills up fast, so don't wait.

        Located in {self.location}, we're your local experts in automotive perfection.

        {self.business_name} - Call today, drive away amazed.
        {self.phone}
        """

    def create_synthesia_video(self, video_key, api_key):
        """
        Creates video using Synthesia API
        """
        url = "https://api.synthesia.io/v2/videos"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        video_data = self.videos[video_key]
        
        payload = {
            "test": False,
            "visibility": "private",
            "templateId": "professional_presenter",
            "templateData": {
                "script": video_data["script"],
                "avatar": "professional_male_01",
                "voiceover": "en-US-Standard-J",
                "background": "office_modern",
                "title": f"{self.business_name} - {video_data['title']}"
            },
            "callbackId": f"clinton_auto_{video_key}"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Error creating video {video_key}: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"Exception creating video {video_key}: {str(e)}")
            return None

    def create_runway_video(self, video_key, api_key):
        """
        Creates video using RunwayML API
        """
        url = "https://api.dev.runwayml.com/v1/image_to_video"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        video_data = self.videos[video_key]
        
        payload = {
            "promptText": f"Professional auto detailing business video: {video_data['script'][:500]}",
            "model": "gen3a_turbo",
            "watermark": False,
            "duration": min(video_data["duration"], 10),  # RunwayML has limits
            "ratio": "16:9",
            "seed": 123456789
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error creating video {video_key}: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"Exception creating video {video_key}: {str(e)}")
            return None

    def download_video(self, video_url, filename):
        """
        Downloads the generated video file
        """
        try:
            response = requests.get(video_url)
            if response.status_code == 200:
                with open(f"C:/Users/cjay4/OneDrive/Desktop/sincor-clean/clinton_videos/{filename}", "wb") as f:
                    f.write(response.content)
                print(f"Downloaded: {filename}")
                return True
            else:
                print(f"Failed to download {filename}")
                return False
        except Exception as e:
            print(f"Exception downloading {filename}: {str(e)}")
            return False

    def generate_all_videos(self, api_key, platform="synthesia"):
        """
        Generates all 6 videos for Clinton Auto Detailing
        """
        # Create output directory
        os.makedirs("C:/Users/cjay4/OneDrive/Desktop/sincor-clean/clinton_videos", exist_ok=True)
        
        print(f"Starting video generation for {self.business_name}")
        print(f"Platform: {platform.title()}")
        print(f"Total videos to create: {len(self.videos)}")
        
        results = {}
        
        for video_key, video_info in self.videos.items():
            print(f"\nCreating: {video_info['title']} ({video_info['duration']}s)")
            
            if platform == "synthesia":
                result = self.create_synthesia_video(video_key, api_key)
            elif platform == "runway":
                result = self.create_runway_video(video_key, api_key)
            
            if result:
                results[video_key] = result
                print(f"✓ Video creation initiated for {video_key}")
            else:
                print(f"✗ Failed to create {video_key}")
            
            # Small delay between requests
            time.sleep(2)
        
        return results

    def check_video_status(self, video_id, api_key, platform="synthesia"):
        """
        Checks the status of video generation
        """
        if platform == "synthesia":
            url = f"https://api.synthesia.io/v2/videos/{video_id}"
            headers = {"Authorization": f"Bearer {api_key}"}
        elif platform == "runway":
            url = f"https://api.dev.runwayml.com/v1/tasks/{video_id}"
            headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Error checking status: {str(e)}")
            return None

def main():
    print("=" * 60)
    print("CLINTON AUTO DETAILING VIDEO GENERATOR")
    print("Creating actual MP4 files for marketing use")
    print("=" * 60)
    
    generator = ClintonVideoGenerator()
    
    # Display video specifications
    print("\nVideo Specifications:")
    for key, video in generator.videos.items():
        print(f"- {video['title']}: {video['duration']} seconds")
    
    print("\nTo generate actual videos, you need to:")
    print("1. Sign up for Synthesia (recommended): https://synthesia.io/pricing")
    print("2. Or sign up for RunwayML: https://runwayml.com/pricing")
    print("3. Get your API key from the platform")
    print("4. Run this script with your API key")
    
    print("\nExample usage:")
    print("generator.generate_all_videos('your-api-key-here', 'synthesia')")
    
    return generator

if __name__ == "__main__":
    generator = main()