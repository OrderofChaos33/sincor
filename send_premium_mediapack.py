#!/usr/bin/env python3
"""
Send $500 Premium Media Pack to eenergy@protonmail.com
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_premium_mediapack():
    # Premium $500 Media Pack Content
    premium_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>$500 Premium Media Pack - SINCOR</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }
        .value-box { background: #f8f9fa; border: 3px solid #28a745; padding: 20px; margin: 20px 0; border-radius: 10px; }
        .deliverable { background: white; border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 8px; }
        .video-preview { background: #000; color: #fff; padding: 15px; border-radius: 5px; font-family: monospace; }
        .flyer-preview { display: inline-block; background: linear-gradient(45deg, #ff6b6b, #4ecdc4); color: white; padding: 20px; margin: 5px; border-radius: 8px; font-weight: bold; text-align: center; width: 120px; }
        .social-preview { background: #1da1f2; color: white; padding: 10px; margin: 5px 0; border-radius: 20px; }
        .cta { background: #ff4757; color: white; padding: 20px 40px; text-decoration: none; border-radius: 50px; font-size: 18px; font-weight: bold; display: inline-block; margin: 20px 0; }
        .pricing { font-size: 24px; color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎁 $500 PREMIUM MEDIA PACK</h1>
        <h2>Complete Professional Marketing Suite</h2>
        <p><strong>SINCOR - We Make Service Businesses Famous</strong></p>
    </div>

    <div class="value-box">
        <h2>🔥 TOTAL VALUE: $2,500+ → YOUR PRICE: $500</h2>
        <p><strong>Everything you need to dominate your market professionally</strong></p>
    </div>

    <div class="deliverable">
        <h3>🎬 6 PROFESSIONAL VIDEOS ($800 value)</h3>
        <div class="video-preview">
            ▶️ Business Introduction Video (90 seconds)<br>
            ▶️ Service Showcase Reel (60 seconds)<br>
            ▶️ Customer Testimonial Story (45 seconds)<br>
            ▶️ Before/After Transformation (30 seconds)<br>
            ▶️ Behind-the-Scenes Process (60 seconds)<br>
            ▶️ Call-to-Action Conversion Video (30 seconds)
        </div>
        <p><strong>✅ 4K Quality ✅ Professional Voiceover ✅ Licensed Music</strong></p>
    </div>

    <div class="deliverable">
        <h3>📄 12 CUSTOM FLYER DESIGNS ($600 value)</h3>
        <div>
            <div class="flyer-preview">GRAND<br>OPENING<br>50% OFF</div>
            <div class="flyer-preview">SPRING<br>SPECIAL<br>$99</div>
            <div class="flyer-preview">PREMIUM<br>SERVICE<br>$199</div>
            <div class="flyer-preview">EMERGENCY<br>24/7<br>CALL NOW</div>
            <div class="flyer-preview">FREE<br>ESTIMATE<br>TODAY</div>
            <div class="flyer-preview">FAMILY<br>OWNED<br>TRUSTED</div>
        </div>
        <p><strong>✅ Print-Ready PDFs ✅ Social Media Sizes ✅ Editable Templates</strong></p>
    </div>

    <div class="deliverable">
        <h3>💳 COMPLETE BRAND IDENTITY ($400 value)</h3>
        <ul>
            <li>✅ Professional Logo Design (5 variations)</li>
            <li>✅ Business Card Templates (10 designs)</li>
            <li>✅ Letterhead & Invoice Templates</li>
            <li>✅ Vehicle Wrap Mockups</li>
            <li>✅ Uniform/Shirt Design Templates</li>
        </ul>
    </div>

    <div class="deliverable">
        <h3>📱 30-DAY SOCIAL MEDIA CALENDAR ($300 value)</h3>
        <div class="social-preview">🔥 Monday Motivation: "Transform your space today!"</div>
        <div class="social-preview">💡 Tip Tuesday: "3 signs you need professional service..."</div>
        <div class="social-preview">🏆 Win Wednesday: "Customer spotlight success story"</div>
        <div class="social-preview">🔧 Throwback Thursday: "How we've grown over the years"</div>
        <div class="social-preview">🎉 Feature Friday: "Weekend special announcement"</div>
        <p><strong>✅ Instagram Posts ✅ Facebook Content ✅ TikTok Scripts</strong></p>
    </div>

    <div class="deliverable">
        <h3>📧 EMAIL MARKETING SEQUENCE ($250 value)</h3>
        <ul>
            <li>✅ Welcome Series (5 emails)</li>
            <li>✅ Seasonal Promotions (12 campaigns)</li>
            <li>✅ Customer Follow-up Templates</li>
            <li>✅ Referral Request Series</li>
            <li>✅ Re-engagement Campaign</li>
        </ul>
    </div>

    <div class="deliverable">
        <h3>🎯 GOOGLE ADS TEMPLATES ($200 value)</h3>
        <ul>
            <li>✅ 25 High-Converting Ad Headlines</li>
            <li>✅ 15 Proven Ad Descriptions</li>
            <li>✅ Keyword Research (100+ keywords)</li>
            <li>✅ Landing Page Copy Templates</li>
            <li>✅ Campaign Setup Guide</li>
        </ul>
    </div>

    <div style="background: #2c3e50; color: white; padding: 30px; text-align: center; border-radius: 10px; margin: 30px 0;">
        <h2>🚀 BONUS: "DONE FOR YOU" UPGRADE</h2>
        <p class="pricing">Add $200 - WE IMPLEMENT EVERYTHING!</p>
        <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
            <li>✅ We post all social media content for 30 days</li>
            <li>✅ We set up your Google Ads campaigns</li>
            <li>✅ We design and print 500 flyers</li>
            <li>✅ We create your business cards</li>
            <li>✅ Weekly performance reports</li>
        </ul>
    </div>

    <div style="text-align: center;">
        <a href="mailto:sales@getsincor.com?subject=I WANT THE $500 PREMIUM PACK&body=Hi, I want the complete $500 Premium Media Pack. Please send payment details and delivery timeline." class="cta">
            🔥 GET THIS PREMIUM PACK NOW - $500
        </a>
    </div>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; margin: 30px 0;">
        <h3>💪 30-DAY MONEY-BACK GUARANTEE</h3>
        <p>If you don't see improvement in your leads within 30 days, full refund - no questions asked!</p>
    </div>

    <div style="border-top: 2px solid #e0e0e0; padding-top: 20px; color: #666; text-align: center;">
        <p><strong>SINCOR Marketing Team</strong><br>
        Call/Text: (815) 718-8936<br>
        Email: sales@getsincor.com<br>
        <em>"We Make Service Businesses Famous"</em></p>
    </div>
</body>
</html>
"""

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🎁 Your $500 Premium Media Pack is Ready - SINCOR"
        msg['From'] = "SINCOR Marketing <sales@getsincor.com>"
        msg['To'] = "eenergy@protonmail.com"
        
        # Add HTML content
        html_part = MIMEText(premium_content, 'html')
        msg.attach(html_part)
        
        # For now, save to file since we don't have SMTP configured
        with open("premium_mediapack_email.html", "w", encoding="utf-8") as f:
            f.write(premium_content)
        
        print("SUCCESS: $500 Premium Media Pack created and ready to send to eenergy@protonmail.com")
        print("Email content saved to: premium_mediapack_email.html")
        print("")
        print("PREMIUM PACK INCLUDES:")
        print("✅ 6 Professional Videos ($800 value)")
        print("✅ 12 Custom Flyer Designs ($600 value)")
        print("✅ Complete Brand Identity ($400 value)")
        print("✅ 30-Day Social Media Calendar ($300 value)")
        print("✅ Email Marketing Sequence ($250 value)")
        print("✅ Google Ads Templates ($200 value)")
        print("✅ Done-For-You Upgrade Available (+$200)")
        print("")
        print("TOTAL VALUE: $2,550 → PRICE: $500")
        
        return True
        
    except Exception as e:
        print(f"Error creating premium pack: {e}")
        return False

if __name__ == "__main__":
    send_premium_mediapack()