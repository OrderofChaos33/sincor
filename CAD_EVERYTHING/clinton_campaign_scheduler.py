#!/usr/bin/env python3
"""
Clinton Detailing Automated Campaign Scheduler
Runs lead generation and outreach campaigns automatically
"""

import schedule
import time
from datetime import datetime
from clinton_detailing_leads import ClintonDetailingLeads
import sqlite3
import json

class ClintonCampaignScheduler:
    def __init__(self):
        self.leads_system = ClintonDetailingLeads()
        self.campaign_active = True
        
    def morning_lead_scan(self):
        """Run morning lead generation scan"""
        print(f"🌅 Morning lead scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = self.leads_system.run_daily_lead_generation()
        
        if results['leads_found'] > 0:
            print(f"✅ Found {results['leads_found']} new leads!")
            print(f"📞 Ready for outreach calls")
            print(f"🔗 Booking URL: {results['booking_url']}")
            
            # Log campaign activity
            self.log_campaign_activity('morning_scan', results['leads_found'])
            
    def afternoon_follow_up(self):
        """Run afternoon follow-up activities"""
        print(f"☀️ Afternoon follow-up - {datetime.now().strftime('%H:%M:%S')}")
        
        # Get today's uncalled leads
        uncalled_leads = self.get_uncalled_leads()
        
        if uncalled_leads:
            print(f"📞 {len(uncalled_leads)} leads ready for calls:")
            for lead in uncalled_leads[:5]:  # Show top 5
                print(f"   • {lead['business_name']} - Score: {lead['lead_score']}")
                
        self.log_campaign_activity('afternoon_followup', len(uncalled_leads))
        
    def evening_summary(self):
        """Generate evening campaign summary"""
        print(f"🌙 Evening summary - {datetime.now().strftime('%H:%M:%S')}")
        
        daily_stats = self.get_daily_stats()
        print(f"📊 Today's Activity:")
        print(f"   • Leads generated: {daily_stats['leads_generated']}")
        print(f"   • Calls needed: {daily_stats['calls_needed']}")
        print(f"   • Bookings: {daily_stats['bookings']}")
        
    def get_uncalled_leads(self):
        """Get leads that haven't been contacted"""
        conn = sqlite3.connect('clinton_leads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT business_name, phone, lead_score, address
            FROM local_leads 
            WHERE contact_attempted = FALSE 
            AND created_at >= date('now', '-7 days')
            ORDER BY lead_score DESC
            LIMIT 20
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'business_name': row[0],
                'phone': row[1], 
                'lead_score': row[2],
                'address': row[3]
            }
            for row in results
        ]
    
    def get_daily_stats(self):
        """Get today's campaign statistics"""
        conn = sqlite3.connect('clinton_leads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as leads_generated,
                COUNT(CASE WHEN contact_attempted = FALSE THEN 1 END) as calls_needed,
                COUNT(CASE WHEN booking_scheduled = TRUE THEN 1 END) as bookings
            FROM local_leads 
            WHERE date(created_at) = date('now')
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'leads_generated': result[0],
            'calls_needed': result[1],
            'bookings': result[2]
        }
    
    def log_campaign_activity(self, activity_type, count):
        """Log campaign activity for tracking"""
        conn = sqlite3.connect('clinton_leads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type TEXT,
                count INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            INSERT INTO campaign_log (activity_type, count)
            VALUES (?, ?)
        ''', (activity_type, count))
        
        conn.commit()
        conn.close()
        
    def start_campaign(self):
        """Start automated campaign scheduler"""
        print("🚀 Starting Clinton Detailing automated campaign!")
        print("📅 Schedule:")
        print("   • 8:00 AM - Morning lead generation")
        print("   • 2:00 PM - Afternoon follow-up reminder")  
        print("   • 6:00 PM - Evening summary")
        print(f"🔗 Booking URL: {self.leads_system.booking_url}")
        
        # Schedule daily activities
        schedule.every().day.at("08:00").do(self.morning_lead_scan)
        schedule.every().day.at("14:00").do(self.afternoon_follow_up)
        schedule.every().day.at("18:00").do(self.evening_summary)
        
        # Run initial scan
        self.morning_lead_scan()
        
        # Keep running
        while self.campaign_active:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    scheduler = ClintonCampaignScheduler()
    scheduler.start_campaign()