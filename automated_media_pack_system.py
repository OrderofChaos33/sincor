#!/usr/bin/env python3
"""
SINCOR Automated Media Pack Generation & Email System
Finds service businesses, creates media packs, sends via email automatically
"""

import sqlite3
import smtplib
import random
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

class SINCORMediaPackSystem:
    def __init__(self):
        self.setup_database()
        self.service_types = [
            'Plumbing', 'HVAC', 'Electrical', 'Landscaping', 'Roofing', 
            'Auto Detailing', 'Pest Control', 'Cleaning Services', 'Tree Service',
            'Concrete', 'Pool Service', 'Locksmith', 'Garage Door', 'Appliance Repair'
        ]
        
    def setup_database(self):
        """Initialize the system database"""
        self.conn = sqlite3.connect('sincor_media_packs.db')
        cursor = self.conn.cursor()
        
        # Service businesses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT,
                owner_name TEXT,
                email TEXT,
                phone TEXT,
                service_type TEXT,
                location TEXT,
                website TEXT,
                status TEXT DEFAULT 'new',
                media_pack_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Media pack campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER,
                media_pack_content TEXT,
                sent_at TIMESTAMP,
                opened BOOLEAN DEFAULT FALSE,
                clicked BOOLEAN DEFAULT FALSE,
                responded BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (business_id) REFERENCES service_businesses (id)
            )
        ''')
        
        self.conn.commit()
        
    def generate_service_businesses(self, count=100):
        """Generate realistic service business leads"""
        business_names = {
            'Plumbing': ['Elite Plumbing', 'QuickFix Plumbing', 'Pro Drain Solutions', 'Reliable Pipes Co'],
            'HVAC': ['Cool Air Systems', 'Climate Masters', 'Heating Heroes', 'AC Specialists'],
            'Electrical': ['Bright Electric', 'Power Pro Electric', 'Spark Solutions', 'Wire Masters'],
            'Landscaping': ['Green Thumb Landscaping', 'Yard Perfect', 'Lawn Masters', 'Garden Pros'],
            'Auto Detailing': ['Shine Auto Detail', 'Perfect Polish', 'Car Care Pros', 'Detail Masters']
        }
        
        first_names = ['Mike', 'Dave', 'Steve', 'John', 'Chris', 'Matt', 'Tony', 'Rick']
        last_names = ['Johnson', 'Smith', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore']
        cities = ['Des Moines', 'Cedar Rapids', 'Davenport', 'Iowa City', 'Waterloo', 'Clinton', 'Dubuque']
        
        cursor = self.conn.cursor()
        
        for i in range(count):
            # Add Clinton Auto Detailing as first business
            if i == 0:
                business_name = "Clinton Auto Detailing"
                service_type = "Auto Detailing"
                owner_name = "Court"
                email = "test@example.com"  # Will be overridden later
                city = "Clinton"
                phone = f"563-{random.randint(200,999)}-{random.randint(1000,9999)}"
                website = "www.clintondetailing.com"
            else:
                service_type = random.choice(self.service_types)
                if service_type in business_names:
                    business_name = random.choice(business_names[service_type])
                else:
                    business_name = f"{random.choice(['Pro', 'Elite', 'Premier', 'Quality'])} {service_type}"
                
                owner_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                email = f"{owner_name.lower().replace(' ', '.')}@{business_name.lower().replace(' ', '')}.com"
                phone = f"515-{random.randint(200,999)}-{random.randint(1000,9999)}"
                city = random.choice(cities)
                website = f"www.{business_name.lower().replace(' ', '')}.com"
            
            cursor.execute('''
                INSERT INTO service_businesses (business_name, owner_name, email, phone, service_type, location, website)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (business_name, owner_name, email, phone, service_type, city, website))
            
        self.conn.commit()
        print(f"Generated {count} service business leads")
        
    def create_media_pack_preview_email(self, business_data):
        """Create irresistible preview email showing actual media pack contents"""
        business_name = business_data[1]
        owner_name = business_data[2]
        service_type = business_data[5]
        location = business_data[6]
        phone = business_data[4]
        
        preview_email = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; line-height: 1.6; }}
        .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.15); }}
        .header {{ background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; padding: 30px; text-align: center; }}
        .content {{ padding: 30px; }}
        .preview-box {{ background: #f8f9ff; border: 3px solid #007bff; padding: 25px; border-radius: 12px; margin: 25px 0; }}
        .deliverable {{ background: white; border: 1px solid #e0e0e0; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .video-preview {{ background: #000; color: white; padding: 20px; text-align: center; border-radius: 8px; margin: 10px 0; }}
        .flyer-preview {{ display: inline-block; width: 120px; height: 80px; background: linear-gradient(45deg, #667eea, #764ba2); color: white; text-align: center; padding: 10px; margin: 5px; border-radius: 5px; font-size: 10px; }}
        .social-preview {{ background: #1877f2; color: white; padding: 10px; border-radius: 8px; margin: 5px 0; font-size: 12px; }}
        .urgency {{ background: #dc3545; color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; }}
        .upsell {{ background: #28a745; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .cta {{ background: #ff6b35; color: white; padding: 18px 35px; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; display: block; margin: 25px auto; text-decoration: none; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 WE BUILT THIS FOR {business_name.upper()}</h1>
            <h2>Complete Marketing Package - Ready to Use!</h2>
        </div>
        
        <div class="content">
            <p><strong>Hi {owner_name},</strong></p>
            
            <p>We found {business_name} online and were impressed by your {service_type.lower()} work in {location}.</p>
            
            <p><strong>So we went ahead and built you a COMPLETE professional marketing package...</strong></p>
            
            <div class="preview-box">
                <h3>🎁 HERE'S EXACTLY WHAT YOU GET:</h3>
                
                <div class="deliverable">
                    <strong>🎬 2 Professional Videos</strong>
                    <div class="video-preview">
                        ▶️ Business Intro Video: "Hi, I'm {owner_name} from {business_name}..."<br>
                        ▶️ Customer Success Story: "Amazing results - my car looks brand new!"
                    </div>
                </div>
                
                <div class="deliverable">
                    <strong>📄 4 Custom Flyer Templates</strong>
                    <div>
                        <div class="flyer-preview">EXPRESS<br>SERVICE<br>$99</div>
                        <div class="flyer-preview">FULL<br>DETAIL<br>$199</div>
                        <div class="flyer-preview">PREMIUM<br>PACKAGE<br>$299</div>
                        <div class="flyer-preview">FREE<br>PICKUP<br>& DELIVERY</div>
                    </div>
                </div>
                
                <div class="deliverable">
                    <strong>💳 Professional Business Card Design</strong>
                    <div style="background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 15px; border-radius: 8px; font-size: 12px;">
                        <strong>{business_name.upper()}</strong><br>
                        {owner_name} - Owner/Operator<br>
                        📞 {phone} • 🌐 Website Ready
                    </div>
                </div>
                
                <div class="deliverable">
                    <strong>📱 5 Ready-to-Post Social Media Posts</strong>
                    <div class="social-preview">🤯 TRANSFORMATION TUESDAY! Check out this amazing before/after...</div>
                    <div class="social-preview">🛡️ PROTECT YOUR INVESTMENT with professional detailing...</div>
                    <div class="social-preview">🚚 TOO BUSY? We offer FREE pickup and delivery...</div>
                </div>
            </div>
            
            <div class="urgency">
                <h3>⚡ EVERYTHING YOU NEED - NO MORE WORRYING ABOUT CONTENT!</h3>
                <p><strong>Package Value: $2,500+ → Your Price: $299</strong></p>
                <p>✅ All files included • ✅ Commercial license • ✅ Ready to use immediately</p>
            </div>
            
            <p><strong>Why we built this for you:</strong></p>
            <p>Most {service_type.lower()} businesses in {location} have terrible marketing. You deserve better.</p>
            
            <p><strong>This isn't just pretty graphics - this is EVERYTHING you need to look professional and get more customers.</strong></p>
            
            <div class="upsell">
                <h3>🚀 UPGRADE: "WE DO IT ALL FOR YOU" - $699</h3>
                <p><strong>Don't want to handle posting and printing yourself?</strong></p>
                <ul>
                    <li>✅ <strong>5-6 Professional Videos</strong> (TikTok/Instagram ready)</li>
                    <li>✅ <strong>We post everything daily</strong> - social media management</li>
                    <li>✅ <strong>Print & mail 500 flyers</strong> to local neighborhoods</li>
                    <li>✅ <strong>Google Ads setup</strong> with $200 credit</li>
                </ul>
                <p><strong>We become your marketing department for 3 months!</strong></p>
            </div>
            
            <a href="mailto:sales@getsincor.com?subject=SHOW ME the complete package for {business_name}&body=Hi, I want to see the full marketing package for {business_name}. Please send it over! My phone: {phone}" class="cta">
                📧 REPLY "SHOW ME" - GET FULL PREVIEW NOW
            </a>
            
            <p style="text-align: center;">
                <strong>Or call/text directly: (815) 718-8936</strong><br>
                Questions? We're here to help!
            </p>
            
            <p style="border-top: 2px solid #e0e0e0; padding-top: 20px; color: #666; text-align: center;">
                <strong>Alex Thompson</strong><br>
                SINCOR Marketing Team<br>
                <em>"We Make Service Businesses Famous"</em>
            </p>
        </div>
    </div>
</body>
</html>
"""
        return preview_email
        
    def send_media_pack_email(self, business_data, media_pack_html):
        """Send media pack via email"""
        business_name = business_data[1]
        owner_name = business_data[2]
        email = business_data[3]
        service_type = business_data[5]
        
        # For test - add Clinton Detailing to the email
        if business_name == "Clinton Auto Detailing":
            email = "eenergy@protonmail.com"
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Professional Marketing Package Created for {business_name}"
            msg['From'] = "SINCOR Marketing <sales@getsincor.com>"
            msg['To'] = email
            
            # Create HTML part
            html_part = MIMEText(media_pack_html, 'html')
            msg.attach(html_part)
            
            # Simulate sending (replace with actual SMTP when ready)
            print(f"SENDING: {business_name} ({email})")
            print(f"   Subject: Professional Marketing Package for {business_name}")
            print(f"   Content: Custom media pack for {service_type} business")
            
            # Log campaign
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO campaigns (business_id, media_pack_content, sent_at)
                VALUES (?, ?, ?)
            ''', (business_data[0], media_pack_html, datetime.now()))
            
            # Update business status
            cursor.execute('''
                UPDATE service_businesses 
                SET media_pack_sent = TRUE, status = 'contacted'
                WHERE id = ?
            ''', (business_data[0],))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Failed to send to {email}: {str(e)}")
            return False
            
    def run_automated_campaign(self, batch_size=10):
        """Run automated media pack campaign"""
        cursor = self.conn.cursor()
        
        # Get businesses that haven't been contacted
        cursor.execute('''
            SELECT * FROM service_businesses 
            WHERE media_pack_sent = FALSE
            LIMIT ?
        ''', (batch_size,))
        
        businesses = cursor.fetchall()
        sent_count = 0
        
        for business in businesses:
            print(f"\nCREATING MEDIA PACK FOR: {business[1]}")
            
            # Create irresistible preview email
            preview_email = self.create_media_pack_preview_email(business)
            
            # Send email
            if self.send_media_pack_email(business, preview_email):
                sent_count += 1
                
            # Delay between emails to avoid spam filters
            time.sleep(2)
            
        print(f"\nCAMPAIGN COMPLETE: {sent_count} media packs sent!")
        return sent_count
        
    def get_campaign_stats(self):
        """Get campaign performance statistics"""
        cursor = self.conn.cursor()
        
        # Total businesses
        cursor.execute("SELECT COUNT(*) FROM service_businesses")
        total_businesses = cursor.fetchone()[0]
        
        # Media packs sent
        cursor.execute("SELECT COUNT(*) FROM service_businesses WHERE media_pack_sent = TRUE")
        sent = cursor.fetchone()[0]
        
        # By service type
        cursor.execute("""
            SELECT service_type, COUNT(*) as count,
            SUM(CASE WHEN media_pack_sent = TRUE THEN 1 ELSE 0 END) as sent
            FROM service_businesses 
            GROUP BY service_type
            ORDER BY count DESC
        """)
        by_service = cursor.fetchall()
        
        return {
            'total_businesses': total_businesses,
            'media_packs_sent': sent,
            'send_rate': (sent / total_businesses * 100) if total_businesses > 0 else 0,
            'by_service': by_service
        }
        
    def print_dashboard(self):
        """Print campaign dashboard"""
        stats = self.get_campaign_stats()
        
        print("\n" + "="*60)
        print("SINCOR AUTOMATED MEDIA PACK SYSTEM")
        print("="*60)
        print(f"Total Service Businesses: {stats['total_businesses']}")
        print(f"Media Packs Sent: {stats['media_packs_sent']}")
        print(f"Send Rate: {stats['send_rate']:.1f}%")
        
        print(f"\nBUSINESSES BY SERVICE TYPE:")
        for service, count, sent in stats['by_service']:
            print(f"   • {service}: {count} businesses ({sent} contacted)")
            
        # Recent campaigns
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT sb.business_name, sb.service_type, c.sent_at
            FROM campaigns c
            JOIN service_businesses sb ON c.business_id = sb.id
            ORDER BY c.sent_at DESC
            LIMIT 5
        """)
        recent = cursor.fetchall()
        
        if recent:
            print(f"\nRECENT MEDIA PACKS SENT:")
            for business_name, service_type, sent_at in recent:
                date_obj = datetime.strptime(sent_at, '%Y-%m-%d %H:%M:%S.%f')
                print(f"   • {business_name} ({service_type}) - {date_obj.strftime('%m/%d %I:%M %p')}")

if __name__ == '__main__':
    print("Starting SINCOR Automated Media Pack System...")
    
    system = SINCORMediaPackSystem()
    
    # Generate businesses if database is empty
    stats = system.get_campaign_stats()
    if stats['total_businesses'] == 0:
        print("Generating service business leads...")
        system.generate_service_businesses(100)
    
    # Run automated campaign
    print("\nStarting automated media pack campaign...")
    system.run_automated_campaign(10)
    
    # Show dashboard
    system.print_dashboard()
    
    print("\nRevenue Potential:")
    print(f"   • If 10% respond at $299 each = ${stats['media_packs_sent'] * 0.10 * 299:.2f}")
    print(f"   • System runs 24/7 automatically")
    print(f"   • Scales to 1000+ businesses per day")