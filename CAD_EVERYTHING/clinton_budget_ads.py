#!/usr/bin/env python3
"""
Clinton Detailing Budget-Controlled Ad Campaign
MAX $15/day, no overspending, current CPC limits
"""

import os
from datetime import datetime, date
import sqlite3

class ClintonBudgetAds:
    def __init__(self):
        # STRICT BUDGET CONTROLS
        self.MAX_DAILY_SPEND = 15.00  # Never exceed $15/day
        self.MAX_CPC_LIMIT = 2.50     # Adjust based on current local CPC
        self.SAFETY_BUFFER = 0.90     # Only spend 90% of budget for safety
        
        self.target_radius = 10  # 10 miles from Clinton
        self.booking_url = "https://clintondetailing.com/bookings"
        
        # Initialize spend tracking
        self.init_budget_database()
    
    def init_budget_database(self):
        """Track daily ad spend to prevent overspending"""
        conn = sqlite3.connect('clinton_ad_budget.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_spend (
                date TEXT PRIMARY KEY,
                total_spent REAL DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                budget_remaining REAL,
                campaign_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_today_spend(self):
        """Get today's current ad spend"""
        conn = sqlite3.connect('clinton_ad_budget.db')
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        cursor.execute('SELECT total_spent FROM daily_spend WHERE date = ?', (today,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 0.0
    
    def can_spend_more(self, proposed_cost):
        """Check if we can spend more without exceeding budget"""
        today_spent = self.get_today_spend()
        safe_budget = self.MAX_DAILY_SPEND * self.SAFETY_BUFFER
        
        return (today_spent + proposed_cost) <= safe_budget
    
    def create_safe_ad_config(self):
        """Create ad configuration with strict budget controls"""
        today_spent = self.get_today_spend()
        remaining_budget = (self.MAX_DAILY_SPEND * self.SAFETY_BUFFER) - today_spent
        
        ad_config = {
            "campaign_name": "Clinton Detailing Local - Budget Safe",
            "daily_budget": min(remaining_budget, self.MAX_DAILY_SPEND),
            "max_cpc": self.MAX_CPC_LIMIT,
            
            # Geographic targeting - 10 miles only
            "location_targeting": {
                "radius": f"{self.target_radius} miles",
                "center": "Clinton, IL",  # Adjust to your actual location
                "exclude_outside": True
            },
            
            # Keywords with budget consciousness
            "keywords": [
                {"keyword": "car detailing near me", "max_cpc": 2.00},
                {"keyword": "auto detailing Clinton", "max_cpc": 1.50}, 
                {"keyword": "mobile car wash", "max_cpc": 2.50},
                {"keyword": "car cleaning service", "max_cpc": 1.75},
                {"keyword": "vehicle detailing", "max_cpc": 2.00}
            ],
            
            # Ad copy focused on local + booking
            "ad_copy": {
                "headline1": "Local Car Detailing",
                "headline2": "Book Online Today",
                "description": f"Professional auto detailing within {self.target_radius} miles. Book now at clintondetailing.com/bookings. Same day service available!",
                "final_url": self.booking_url
            },
            
            # Strict budget controls
            "budget_controls": {
                "daily_budget_cap": self.MAX_DAILY_SPEND,
                "cpc_cap": self.MAX_CPC_LIMIT,
                "auto_pause_at_budget": True,
                "spend_tracking": True
            },
            
            # Schedule - Business hours only (when you can handle calls)
            "ad_schedule": {
                "monday": "08:00-17:00",
                "tuesday": "08:00-17:00", 
                "wednesday": "08:00-17:00",
                "thursday": "08:00-17:00",
                "friday": "08:00-17:00",
                "saturday": "08:00-16:00",
                "sunday": "OFF"  # No ads on Sunday
            }
        }
        
        return ad_config
    
    def log_ad_spend(self, cost, clicks=0, impressions=0):
        """Log ad spend to prevent budget overrun"""
        conn = sqlite3.connect('clinton_ad_budget.db')
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_spend 
            (date, total_spent, clicks, impressions, budget_remaining, campaign_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            today,
            self.get_today_spend() + cost,
            clicks,
            impressions,
            self.MAX_DAILY_SPEND - (self.get_today_spend() + cost),
            (self.get_today_spend() + cost) < self.MAX_DAILY_SPEND
        ))
        
        conn.commit()
        conn.close()
        
        # Alert if approaching budget
        if self.get_today_spend() >= (self.MAX_DAILY_SPEND * 0.8):
            print(f"WARNING: Approaching daily budget limit!")
            print(f"   Spent: ${self.get_today_spend():.2f} / ${self.MAX_DAILY_SPEND}")
    
    def get_budget_status(self):
        """Get current budget status"""
        today_spent = self.get_today_spend()
        remaining = self.MAX_DAILY_SPEND - today_spent
        
        return {
            "date": date.today().isoformat(),
            "spent_today": today_spent,
            "budget_limit": self.MAX_DAILY_SPEND,
            "remaining": max(0, remaining),
            "can_advertise": remaining > 1.00,  # Need at least $1 left
            "safety_status": "SAFE" if today_spent < (self.MAX_DAILY_SPEND * 0.8) else "CAUTION"
        }
    
    def generate_campaign_summary(self):
        """Generate safe campaign summary"""
        budget_status = self.get_budget_status()
        ad_config = self.create_safe_ad_config()
        
        print("CLINTON DETAILING BUDGET-SAFE AD CAMPAIGN")
        print("=" * 50)
        print(f"Date: {budget_status['date']}")
        print(f"Daily Budget Limit: ${self.MAX_DAILY_SPEND}")
        print(f"Spent Today: ${budget_status['spent_today']:.2f}")
        print(f"Remaining: ${budget_status['remaining']:.2f}")
        print(f"Target Area: {self.target_radius} miles from Clinton")
        print(f"Booking URL: {self.booking_url}")
        print(f"Max CPC: ${self.MAX_CPC_LIMIT}")
        print(f"Safety Status: {budget_status['safety_status']}")
        
        if budget_status['can_advertise']:
            print("\nSAFE TO RUN ADS")
            print(f"   Keywords ready with budget controls")
            print(f"   Auto-pause at ${self.MAX_DAILY_SPEND} spend")
        else:
            print("\nBUDGET EXHAUSTED - ADS PAUSED")
            print(f"   Will resume tomorrow with fresh ${self.MAX_DAILY_SPEND} budget")
        
        return {
            "budget_status": budget_status,
            "ad_config": ad_config,
            "campaign_ready": budget_status['can_advertise']
        }

if __name__ == "__main__":
    clinton_ads = ClintonBudgetAds()
    campaign = clinton_ads.generate_campaign_summary()
    
    if campaign['campaign_ready']:
        print(f"\nCampaign ready to launch with strict budget controls!")
    else:
        print(f"\nBudget limit reached. Campaign will resume tomorrow.")