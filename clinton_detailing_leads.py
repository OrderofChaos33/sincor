#!/usr/bin/env python3
"""
Clinton Detailing Automated Lead Generation & Appointment Setting System
"""

import sqlite3
import random
import time
from datetime import datetime, timedelta

class ClintonDetailingAgent:
    def __init__(self):
        self.setup_database()
        self.services = {
            'express': {'name': 'Express Detail', 'price': 99, 'duration': '2 hours'},
            'full_car': {'name': 'Full Detail - Car', 'price': 199, 'duration': '3 hours'},
            'full_large': {'name': 'Full Detail - Large Vehicle', 'price': 299, 'duration': '4 hours'},
            'paint_correction': {'name': 'Paint Correction', 'price': 399, 'duration': '6 hours'},
            'ceramic': {'name': 'Ceramic Coating', 'price': 999, 'duration': '8 hours'}
        }
        
    def setup_database(self):
        """Initialize the leads database"""
        self.conn = sqlite3.connect('clinton_leads.db')
        cursor = self.conn.cursor()
        
        # Create leads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                vehicle_type TEXT,
                service_interest TEXT,
                status TEXT DEFAULT 'new',
                last_contact TIMESTAMP,
                appointment_booked BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create appointments table  
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                service TEXT,
                price REAL,
                scheduled_date TIMESTAMP,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')
        
        self.conn.commit()
        
    def generate_local_leads(self, count=50):
        """Generate local Clinton, IA leads"""
        first_names = ['Mike', 'Sarah', 'David', 'Jennifer', 'Robert', 'Lisa', 'Chris', 'Amanda', 'Jason', 'Michelle']
        last_names = ['Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Garcia', 'Rodriguez', 'Wilson', 'Martinez']
        vehicles = ['BMW 3 Series', 'Honda Accord', 'Ford F-150', 'Chevrolet Silverado', 'Toyota Camry', 
                   'Mercedes C-Class', 'Audi A4', 'Jeep Wrangler', 'Nissan Altima', 'Ford Explorer']
        
        cursor = self.conn.cursor()
        
        for _ in range(count):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            phone = f"563-{random.randint(200,999)}-{random.randint(1000,9999)}"
            vehicle = random.choice(vehicles)
            
            # Determine service interest based on vehicle type
            if 'BMW' in vehicle or 'Mercedes' in vehicle or 'Audi' in vehicle:
                service = 'ceramic' if random.random() > 0.7 else 'paint_correction'
            elif 'F-150' in vehicle or 'Silverado' in vehicle or 'Explorer' in vehicle:
                service = 'full_large'
            else:
                service = random.choice(['express', 'full_car'])
                
            cursor.execute('''
                INSERT INTO leads (name, phone, vehicle_type, service_interest, status)
                VALUES (?, ?, ?, ?, 'new')
            ''', (name, phone, vehicle, service))
            
        self.conn.commit()
        print(f"Generated {count} local leads for Clinton Detailing")
        
    def create_sales_script(self, lead_data, service_key):
        """Generate personalized sales script"""
        service = self.services[service_key]
        name = lead_data[1]  # name from lead_data tuple
        vehicle = lead_data[3]  # vehicle_type
        
        scripts = {
            'express': f"""
Hi {name}, this is Alex from Clinton Auto Detailing here in Clinton.

I'm calling because we're running a special promotion this week for {vehicle} owners. 

We can have your {vehicle} looking absolutely showroom perfect with our Express Detail service for just ${service['price']} - that includes complete exterior wash, full interior vacuum and cleaning, and crystal-clear windows.

The best part? We offer FREE pick-up and delivery, so you don't even have to leave your house.

We have an opening tomorrow at 2pm or Thursday at 10am. Which works better for you?
""",
            
            'full_car': f"""
Hi {name}, this is Alex from Clinton Auto Detailing.

Your {vehicle} deserves the royal treatment, and we're offering our Full Detail service this week for just ${service['price']}.

This isn't just a wash - we're talking complete interior and exterior detail that will make your {vehicle} look and smell like it just rolled off the dealer lot.

We'll pick it up from your location, spend {service['duration']} making it perfect, and deliver it back to you.

I have Tuesday at 1pm or Wednesday at 11am available. Should I put you down for one of those?
""",
            
            'ceramic': f"""
Hi {name}, this is Alex from Clinton Auto Detailing.

I'm calling {vehicle} owners in Clinton about our premium Ceramic Coating service.

For just ${service['price']}, we can give your {vehicle} a 5-year paint protection that will keep it looking showroom new while making washing effortless.

This is perfect for a {vehicle} - it'll protect your investment and actually increase your resale value.

We have an opening this Friday. Should I reserve that spot for you?
"""
        }
        
        return scripts.get(service_key, scripts['express'])
        
    def simulate_appointment_booking(self, lead_id, service_key):
        """Simulate successful appointment booking"""
        service = self.services[service_key]
        
        # Schedule appointment 2-7 days from now
        scheduled_date = datetime.now() + timedelta(days=random.randint(2, 7))
        
        cursor = self.conn.cursor()
        
        # Create appointment
        cursor.execute('''
            INSERT INTO appointments (lead_id, service, price, scheduled_date, status)
            VALUES (?, ?, ?, ?, 'scheduled')
        ''', (lead_id, service['name'], service['price'], scheduled_date))
        
        # Update lead status
        cursor.execute('''
            UPDATE leads 
            SET status = 'booked', appointment_booked = TRUE, last_contact = ?
            WHERE id = ?
        ''', (datetime.now(), lead_id))
        
        self.conn.commit()
        return scheduled_date
        
    def run_agent_campaign(self):
        """Run automated appointment setting campaign"""
        cursor = self.conn.cursor()
        
        # Get leads that haven't been contacted recently
        cursor.execute('''
            SELECT * FROM leads 
            WHERE status = 'new' OR 
            (status = 'contacted' AND last_contact < datetime('now', '-3 days'))
            LIMIT 10
        ''')
        
        leads = cursor.fetchall()
        booked_appointments = 0
        
        for lead in leads:
            lead_id, name, phone, vehicle, service_interest, status, last_contact, appointment_booked, notes, created_at = lead
            
            print(f"\n📞 CALLING: {name} ({phone}) - {vehicle}")
            print(f"🎯 PITCH: {service_interest.upper()} SERVICE")
            
            # Generate script
            script = self.create_sales_script(lead, service_interest)
            print(f"\n💬 SCRIPT:\n{script}")
            
            # Simulate call success (70% success rate for good leads)
            if random.random() < 0.7:
                scheduled_date = self.simulate_appointment_booking(lead_id, service_interest)
                print(f"✅ SUCCESS! Appointment booked for {scheduled_date.strftime('%A, %B %d at %I:%M %p')}")
                print(f"💰 Revenue: ${self.services[service_interest]['price']}")
                booked_appointments += 1
            else:
                # Update as contacted but not booked
                cursor.execute('''
                    UPDATE leads SET status = 'contacted', last_contact = ? WHERE id = ?
                ''', (datetime.now(), lead_id))
                print("❌ No booking - will follow up later")
                
            # Simulate time between calls
            time.sleep(1)
            
        self.conn.commit()
        print(f"\n🎉 CAMPAIGN COMPLETE: {booked_appointments} appointments booked!")
        return booked_appointments
        
    def get_campaign_stats(self):
        """Get campaign performance statistics"""
        cursor = self.conn.cursor()
        
        # Total leads
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_leads = cursor.fetchone()[0]
        
        # Booked appointments
        cursor.execute("SELECT COUNT(*) FROM leads WHERE appointment_booked = TRUE")
        booked = cursor.fetchone()[0]
        
        # Total revenue
        cursor.execute("SELECT SUM(price) FROM appointments WHERE status = 'scheduled'")
        revenue = cursor.fetchone()[0] or 0
        
        # Appointments by service
        cursor.execute("""
            SELECT service, COUNT(*), SUM(price) 
            FROM appointments 
            WHERE status = 'scheduled' 
            GROUP BY service
        """)
        by_service = cursor.fetchall()
        
        return {
            'total_leads': total_leads,
            'appointments_booked': booked,
            'conversion_rate': (booked / total_leads * 100) if total_leads > 0 else 0,
            'total_revenue': revenue,
            'by_service': by_service
        }
        
    def print_dashboard(self):
        """Print performance dashboard"""
        stats = self.get_campaign_stats()
        
        print("\n" + "="*50)
        print("🚗 CLINTON DETAILING AGENT PERFORMANCE")
        print("="*50)
        print(f"📊 Total Leads Generated: {stats['total_leads']}")
        print(f"📅 Appointments Booked: {stats['appointments_booked']}")
        print(f"📈 Conversion Rate: {stats['conversion_rate']:.1f}%")
        print(f"💰 Total Revenue Scheduled: ${stats['total_revenue']:,.2f}")
        
        print("\n📋 APPOINTMENTS BY SERVICE:")
        for service, count, revenue in stats['by_service']:
            print(f"   • {service}: {count} appointments (${revenue:,.2f})")
            
        # Upcoming appointments
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT l.name, l.phone, a.service, a.scheduled_date, a.price
            FROM appointments a
            JOIN leads l ON a.lead_id = l.id
            WHERE a.scheduled_date > datetime('now')
            ORDER BY a.scheduled_date
            LIMIT 5
        """)
        upcoming = cursor.fetchall()
        
        if upcoming:
            print("\n📅 UPCOMING APPOINTMENTS:")
            for name, phone, service, date, price in upcoming:
                date_obj = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
                print(f"   • {name} ({phone}) - {service} - ${price} - {date_obj.strftime('%A %B %d')}")

if __name__ == '__main__':
    print("🚗 Starting Clinton Detailing Automated Agent System...")
    
    agent = ClintonDetailingAgent()
    
    # Generate leads if database is empty
    stats = agent.get_campaign_stats()
    if stats['total_leads'] == 0:
        print("📝 Generating local leads...")
        agent.generate_local_leads(50)
    
    # Run campaign
    agent.run_agent_campaign()
    
    # Show results
    agent.print_dashboard()