#!/usr/bin/env python3
"""
Clinton Detailing Manual Lead System
Creates sample leads for immediate testing and outreach
"""

import sqlite3
from datetime import datetime

class ClintonManualLeads:
    def __init__(self):
        self.booking_url = "https://clintondetailing.com/bookings"
        self.init_database()
    
    def init_database(self):
        """Initialize local leads database"""
        conn = sqlite3.connect('clinton_leads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS local_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT,
                phone TEXT,
                address TEXT,
                distance_miles REAL,
                lead_score INTEGER,
                vehicle_type TEXT,
                contact_attempted BOOLEAN DEFAULT FALSE,
                booking_scheduled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_sample_leads(self):
        """Create sample local automotive leads for Clinton area"""
        sample_leads = [
            {
                'business_name': 'Main Street Auto Repair',
                'phone': '(217) 935-3456',
                'address': '123 Main St, Clinton, IL',
                'distance_miles': 2.1,
                'lead_score': 8,
                'vehicle_type': 'auto_repair',
                'notes': 'Local repair shop - likely has customer cars needing detailing'
            },
            {
                'business_name': 'Clinton Ford Lincoln',
                'phone': '(217) 935-2200', 
                'address': '1234 Route 51, Clinton, IL',
                'distance_miles': 1.5,
                'lead_score': 9,
                'vehicle_type': 'car_dealer',
                'notes': 'Car dealership - high value for pre-sale detailing'
            },
            {
                'business_name': 'Advanced Auto Parts',
                'phone': '(217) 935-5678',
                'address': '456 Veterans Pkwy, Clinton, IL', 
                'distance_miles': 3.2,
                'lead_score': 6,
                'vehicle_type': 'auto_parts',
                'notes': 'Auto parts store - customers may need detailing services'
            },
            {
                'business_name': 'Jims Body Shop',
                'phone': '(217) 935-7890',
                'address': '789 Lincoln Ave, Clinton, IL',
                'distance_miles': 4.1,
                'lead_score': 8,
                'vehicle_type': 'auto_body',
                'notes': 'Body shop - cars after repair often need detailing'
            },
            {
                'business_name': 'Enterprise Rent-A-Car',
                'phone': '(217) 935-9012',
                'address': '321 Business Loop, Clinton, IL',
                'distance_miles': 2.8,
                'lead_score': 9,
                'vehicle_type': 'car_rental',
                'notes': 'Rental fleet - regular detailing contracts possible'
            }
        ]
        
        return sample_leads
    
    def save_leads(self, leads):
        """Save leads to database"""
        conn = sqlite3.connect('clinton_leads.db')
        cursor = conn.cursor()
        
        for lead in leads:
            cursor.execute('''
                INSERT OR REPLACE INTO local_leads 
                (business_name, phone, address, distance_miles, lead_score, vehicle_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead['business_name'],
                lead['phone'],
                lead['address'],
                lead['distance_miles'], 
                lead['lead_score'],
                lead['vehicle_type'],
                lead['notes']
            ))
            
        conn.commit()
        conn.close()
        
        print(f"Saved {len(leads)} leads to database")
    
    def get_top_leads(self):
        """Get top leads ready for calling"""
        conn = sqlite3.connect('clinton_leads.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT business_name, phone, address, lead_score, vehicle_type, notes
            FROM local_leads 
            WHERE contact_attempted = FALSE
            ORDER BY lead_score DESC
            LIMIT 10
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        leads = []
        for row in results:
            leads.append({
                'business_name': row[0],
                'phone': row[1],
                'address': row[2], 
                'lead_score': row[3],
                'vehicle_type': row[4],
                'notes': row[5]
            })
            
        return leads
    
    def generate_call_list(self):
        """Generate today's call list with scripts"""
        leads = self.get_top_leads()
        
        print("CLINTON DETAILING - TODAY'S CALL LIST")
        print("=" * 50)
        print(f"Booking URL: {self.booking_url}")
        print(f"Total Leads Ready: {len(leads)}")
        print()
        
        for i, lead in enumerate(leads, 1):
            print(f"{i}. {lead['business_name']}")
            print(f"   Phone: {lead['phone']}")
            print(f"   Address: {lead['address']}")
            print(f"   Score: {lead['lead_score']}/10")
            print(f"   Type: {lead['vehicle_type']}")
            print(f"   Notes: {lead['notes']}")
            print()
        
        # Phone script
        print("PHONE SCRIPT:")
        print("-" * 20)
        print("""
Hi, this is [Your Name] from Clinton Detailing.

I noticed your business works with vehicles, and I wanted to reach out 
about our professional detailing services. We're local - right here in Clinton - 
and we specialize in making fleet vehicles and customer cars look pristine.

We offer:
- Business/fleet discount rates
- On-site service within 10 miles
- Same-day service available
- Online booking at clintondetailing.com/bookings

Would you be interested in hearing about our business rates? 
We can also set up regular service schedules.

Can I schedule a free estimate for you?
        """)
        
        return leads

if __name__ == "__main__":
    clinton_manual = ClintonManualLeads()
    
    # Create and save sample leads
    sample_leads = clinton_manual.create_sample_leads()
    clinton_manual.save_leads(sample_leads)
    
    # Generate call list
    call_list = clinton_manual.generate_call_list()
    
    print(f"\nCall list ready! {len(call_list)} prospects to contact today")