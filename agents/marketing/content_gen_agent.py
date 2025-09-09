"""
Content Generation Agent for SINCOR Marketing Department
Generates high-value copy, scripts, and creative content based on business briefs
"""

import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentGenerationAgent:
    def __init__(self):
        self.agent_id = "content_gen"
        self.skills = {
            "copywriting": 0.92,
            "video_scripts": 0.88,
            "social_copy": 0.94,
            "email_copy": 0.90,
            "ad_copy": 0.85
        }
        
    def generate_hero_video_script(self, brand_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate professional video script"""
        business = brand_context.get("business_name", "Business")
        phone = brand_context.get("phone", "555-0123")
        services = brand_context.get("services", [])
        value_props = brand_context.get("value_props", [])
        location = brand_context.get("location", "Local Area")
        
        script = f"""
{business.upper()} - HERO VIDEO SCRIPT (30 seconds)

[SCENE 1: Problem/Before - 0-8 seconds]
VISUAL: Before shots - dirty/worn surfaces
VOICEOVER: "Your {services[0].lower() if services else 'property'} deserves more than just basic care..."

[SCENE 2: Solution/Process - 8-20 seconds]  
VISUAL: Professional work montage showing:
- {services[0] if services else 'Premium service'} in action
- {services[1] if len(services) > 1 else 'Quality materials'} being applied
- {services[2] if len(services) > 2 else 'Attention to detail'} process shots
VOICEOVER: "{business} - where expertise meets perfection"

[SCENE 3: Results/CTA - 20-30 seconds]
VISUAL: Stunning after shots, satisfied customer
TEXT OVERLAY: "{phone}"
TEXT OVERLAY: "{value_props[0] if value_props else 'Professional Results'}"
VOICEOVER: "Call {business} today. Serving {location} with pride."

[END CARD: 28-30 seconds]
LARGE TEXT: "{phone}"
SMALL TEXT: "Licensed • Insured • Satisfaction Guaranteed"
"""
        
        return {
            "asset_type": "video_script",
            "content": script.strip(),
            "duration": 30,
            "value_estimate": "$167",
            "optimization_notes": [
                "Hook within first 3 seconds",
                "Show transformation process",
                "Clear call-to-action with phone number",
                "Local trust indicators included"
            ]
        }
    
    def generate_service_flyer_copy(self, brand_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate service flyer copy and layout"""
        business = brand_context.get("business_name", "Business")
        phone = brand_context.get("phone", "555-0123")
        services = brand_context.get("services", [])
        value_props = brand_context.get("value_props", [])
        location = brand_context.get("location", "Local Area")
        
        # Generate pricing for services
        service_pricing = {
            "Paint Correction": "Starting at $150",
            "Ceramic Coating": "Starting at $400", 
            "Interior Detailing": "Starting at $75",
            "Wash & Wax": "Starting at $50",
            "Landscaping": "Starting at $100",
            "Lawn Care": "Starting at $60",
            "Plumbing Repair": "Starting at $120",
            "HVAC Service": "Starting at $150"
        }
        
        flyer_copy = f"""
{business.upper()}
{value_props[0] if value_props else 'Professional Service'} • Mobile Available

=== OUR SERVICES ===

"""
        
        for i, service in enumerate(services[:4]):  # Max 4 services for flyer
            pricing = service_pricing.get(service, "Call for pricing")
            flyer_copy += f"""
SERVICE {i+1}: {service.upper()}
• Professional grade equipment & materials
• {value_props[1] if len(value_props) > 1 else 'Expert technicians'}
• {pricing}

"""
        
        flyer_copy += f"""
=== WHY CHOOSE {business.upper()}? ===
✓ {value_props[0] if value_props else 'Years of Experience'}
✓ {value_props[1] if len(value_props) > 1 else 'Licensed & Insured'}  
✓ {value_props[2] if len(value_props) > 2 else 'Satisfaction Guaranteed'}
✓ Serving {location} and surrounding areas

=== CONTACT US TODAY ===
📞 {phone}
📍 {location}

CALL NOW FOR FREE ESTIMATE!

[DESIGN NOTES]
- Use bold, contrasting colors (blue/orange or black/gold)
- Include before/after photos for each service
- QR code linking to Google Business profile
- Professional logo placement at top
- Mobile-friendly social media handles
"""
        
        return {
            "asset_type": "service_flyer",
            "content": flyer_copy.strip(),
            "format": "print_digital",
            "value_estimate": "$167",
            "design_specs": {
                "size": "8.5x11 or 1080x1080px",
                "colors": ["#1e40af", "#f97316", "#ffffff"],
                "fonts": ["Bold sans-serif header", "Clean body text"],
                "images_needed": len(services)
            }
        }
    
    def generate_pricing_sheet_content(self, brand_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive pricing sheet"""
        business = brand_context.get("business_name", "Business")
        phone = brand_context.get("phone", "555-0123")
        services = brand_context.get("services", [])
        value_props = brand_context.get("value_props", [])
        location = brand_context.get("location", "Local Area")
        
        pricing_content = f"""
{business.upper()}
PROFESSIONAL PRICING GUIDE

Contact: {phone} | {location}

=== CORE SERVICES ===

"""
        
        # Service-specific pricing based on business type
        if "Auto Detailing" in business or any("detail" in s.lower() for s in services):
            pricing_content += """
PAINT CORRECTION SERVICES:
• Single Stage Polish: $150-200 (sedans), $200-250 (SUVs/trucks)
• Two Stage Paint Correction: $300-400 (sedans), $400-500 (SUVs)
• Multi Stage Correction (show cars): $500-700+

CERAMIC COATING PACKAGES:
• 1 Year Protection: $400-500
• 3 Year Protection: $600-800
• 5 Year Protection: $800-1200
• Paint Protection Film: $1200-2500

INTERIOR SERVICES:
• Basic Interior Detail: $75-100
• Premium Interior Detail: $150-200
• Leather Treatment: $100-150
• Full Interior Restoration: $300-500+

MAINTENANCE PACKAGES:
• Weekly Maintenance Wash: $35
• Bi-weekly Service: $40
• Monthly Wash & Wax: $50
• Seasonal Protection: $150

SPECIALTY ADD-ONS:
• Headlight Restoration: $75
• Engine Bay Detail: $100
• Convertible Top Cleaning: $125
• Pet Hair Removal: $50
"""
        else:
            # Generic service pricing
            for service in services:
                if "landscaping" in service.lower():
                    pricing_content += f"""
{service.upper()} SERVICES:
• Lawn Maintenance (weekly): $60-80
• Landscape Design: $500-2000
• Tree Trimming: $150-400
• Seasonal Cleanup: $200-500

"""
                elif "plumbing" in service.lower():
                    pricing_content += f"""
{service.upper()} SERVICES:
• Service Call/Diagnosis: $120
• Drain Cleaning: $150-300
• Pipe Repair: $200-500
• Water Heater Service: $300-800

"""
                else:
                    pricing_content += f"""
{service.upper()}:
• Basic Service: Starting at $100
• Premium Service: Starting at $200
• Emergency Service: +50% surcharge
• Maintenance Plans Available

"""
        
        pricing_content += f"""
=== SERVICE AREA & POLICIES ===

SERVICE AREA: {location} and surrounding communities
• Free estimates within 15 miles
• $25 travel fee for 15-25 mile radius
• Extended travel available (call for quote)

SATISFACTION GUARANTEE:
"{value_props[0] if value_props else 'Professional service'} - if you're not completely satisfied, we'll make it right or refund your money."

PAYMENT OPTIONS:
✓ Cash, Check, All Major Credit Cards
✓ PayPal, Venmo, Apple Pay accepted
✓ Financing available for jobs over $500
✓ Senior & Military Discounts: 10% off

SCHEDULING:
• Same-day service often available
• Online booking at [website]
• Text estimates: {phone}
• Emergency service 24/7

=== CONTACT INFORMATION ===
📞 Phone: {phone}
📍 Location: {location}
💻 Website: [coming soon]
📧 Email: info@{business.lower().replace(' ', '')}.com

Licensed • Bonded • Insured
Better Business Bureau Member
"""
        
        return {
            "asset_type": "pricing_sheet",
            "content": pricing_content.strip(),
            "format": "PDF",
            "value_estimate": "$166",
            "pages": 2,
            "usage_notes": [
                "Print on professional letterhead",
                "Include business logo and photos",
                "Leave as PDF for email sending",
                "Update seasonal pricing as needed"
            ]
        }
    
    def generate_social_media_posts(self, brand_context: Dict[str, Any], count: int = 5) -> List[Dict[str, Any]]:
        """Generate social media post content"""
        business = brand_context.get("business_name", "Business")
        phone = brand_context.get("phone", "555-0123")
        services = brand_context.get("services", [])
        location = brand_context.get("location", "Local Area")
        
        posts = []
        
        # Post templates
        post_templates = [
            {
                "type": "before_after",
                "content": f"🔥 TRANSFORMATION TUESDAY! See what {business} can do for you! Before ➡️ After magic ✨\n\n📞 {phone}\n#{location.replace(' ', '').replace(',', '')} #{services[0].replace(' ', '') if services else 'Service'}",
                "image_needed": "before_after_collage"
            },
            {
                "type": "testimonial",
                "content": f"💬 \"Absolutely amazing work! Professional, on time, and incredible results!\" - Sarah M.\n\nExperience the {business} difference! 🌟\n\n📞 {phone}\n#CustomerLove #{location.replace(' ', '').replace(',', '')}",
                "image_needed": "customer_testimonial"
            },
            {
                "type": "service_highlight", 
                "content": f"🚀 {services[0] if services else 'Our Premium Service'} Special!\n\nProfessional {services[0].lower() if services else 'service'} that transforms your property 💪\n\n✅ Licensed & Insured\n✅ Satisfaction Guaranteed\n✅ Free Estimates\n\n📞 Call {phone} today!\n#{services[0].replace(' ', '') if services else 'Service'}",
                "image_needed": "service_action_shot"
            },
            {
                "type": "local_pride",
                "content": f"🏠 Proud to serve {location}! Your local {business} has been creating happy customers and beautiful results.\n\nReady to join our family of satisfied clients?\n\n📞 {phone}\n#Local #{location.replace(' ', '').replace(',', '')} #Community",
                "image_needed": "local_area_shot"
            },
            {
                "type": "call_to_action",
                "content": f"📞 Ready for professional results? \n\n{business} offers:\n🌟 {services[0] if services else 'Premium service'}\n🌟 {services[1] if len(services) > 1 else 'Expert care'}\n🌟 {services[2] if len(services) > 2 else 'Guaranteed satisfaction'}\n\nCall NOW: {phone}\n#GetQuote #{location.replace(' ', '').replace(',', '')}",
                "image_needed": "contact_graphic"
            }
        ]
        
        for i, template in enumerate(post_templates[:count]):
            posts.append({
                "post_id": f"social_{i+1}",
                "platform": ["instagram", "facebook"],
                "content": template["content"],
                "image_needed": template["image_needed"],
                "hashtags_count": len([w for w in template["content"].split() if w.startswith('#')]),
                "optimal_post_times": ["12:00 PM", "5:00 PM", "7:00 PM"]
            })
        
        return posts
    
    def process_daily_sample_pack_trigger(self, trigger_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process daily sample pack trigger and generate content"""
        brand_id = trigger_payload.get("brand_id", "unknown")
        
        # Get brand context (in real system, this would be from database)
        brand_contexts = {
            "cad-clinton": {
                "business_name": "Clinton Auto Detailing",
                "phone": "(815) 718-8936",
                "services": ["Paint Correction", "Ceramic Coating", "Interior Detailing", "Wash & Wax"],
                "value_props": ["15+ Years Experience", "Mobile Service", "Satisfaction Guaranteed"],
                "location": "Clinton, IL"
            }
        }
        
        brand_context = brand_contexts.get(brand_id, {})
        
        if not brand_context:
            return {"error": f"Unknown brand_id: {brand_id}"}
        
        # Generate content pack
        content_pack = {
            "pack_id": f"daily_{brand_id}_{int(time.time())}",
            "brand_context": brand_context,
            "generated_at": datetime.utcnow().isoformat(),
            "assets": []
        }
        
        # Generate hero video script
        video_script = self.generate_hero_video_script(brand_context)
        content_pack["assets"].append(video_script)
        
        # Generate service flyer
        flyer_copy = self.generate_service_flyer_copy(brand_context)
        content_pack["assets"].append(flyer_copy)
        
        # Generate pricing sheet
        pricing_sheet = self.generate_pricing_sheet_content(brand_context)
        content_pack["assets"].append(pricing_sheet)
        
        # Generate social media posts
        social_posts = self.generate_social_media_posts(brand_context)
        for post in social_posts:
            content_pack["assets"].append({
                "asset_type": "social_post",
                "content": post,
                "value_estimate": "$25"
            })
        
        total_value = sum([
            167,  # video script
            167,  # flyer  
            166,  # pricing sheet
            25 * len(social_posts)  # social posts
        ])
        
        content_pack["total_value"] = f"${total_value}"
        content_pack["status"] = "ready_for_distribution"
        
        logger.info(f"Generated content pack {content_pack['pack_id']} worth {content_pack['total_value']}")
        
        return content_pack

if __name__ == "__main__":
    # Test the agent
    agent = ContentGenerationAgent()
    
    test_trigger = {
        "brand_id": "cad-clinton",
        "mode": "daily_sample",
        "target_value": "$500"
    }
    
    result = agent.process_daily_sample_pack_trigger(test_trigger)
    print(f"Generated pack: {result['pack_id']}")
    print(f"Total value: {result['total_value']}")
    print(f"Assets: {len(result['assets'])}")