import asyncpg
import json
from datetime import datetime, timedelta
from typing import List, Dict
import random

class SocialProofEventManager:
    def __init__(self, db_conn, redis_conn):
        self.db = db_conn
        self.redis = redis_conn
        self.cache_ttl = 300  # 5 minutes
    
    async def get_recent_events(self, tenant: str = None, vertical: str = None, limit: int = 20) -> List[Dict]:
        """Get recent conversion events for social proof display"""
        
        # Try cache first
        cache_key = f"social_proof:{tenant or 'all'}:{vertical or 'all'}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # Query recent successful deliveries and purchases
        events_query = """
        WITH recent_events AS (
            -- Recent deliveries
            SELECT 
                'booking' as event_type,
                dl.created_at,
                l.vertical,
                l.contact->>'state' as location,
                CASE 
                    WHEN l.attributes->>'name' IS NOT NULL 
                    THEN substring(l.attributes->>'name' from 1 for 1) || '***'
                    ELSE 'Someone'
                END as anonymous_name
            FROM delivery_ledger dl
            JOIN leads l ON dl.lead_id = l.id
            WHERE dl.status = 'DELIVERED' 
            AND dl.created_at >= NOW() - INTERVAL '24 hours'
            
            UNION ALL
            
            -- Recent purchases  
            SELECT
                'purchase' as event_type,
                p.created_at,
                'marketplace' as vertical,
                'Online' as location,
                CASE 
                    WHEN p.customer_email IS NOT NULL
                    THEN substring(p.customer_email from 1 for 1) || '***'
                    ELSE 'Someone'
                END as anonymous_name
            FROM purchases p
            WHERE p.status = 'completed'
            AND p.created_at >= NOW() - INTERVAL '24 hours'
            
            UNION ALL
            
            -- Recent subscriptions
            SELECT
                'subscription' as event_type,
                s.created_at,
                'saas' as vertical,
                'Online' as location,
                'Someone' as anonymous_name
            FROM subscriptions s
            WHERE s.status = 'active'
            AND s.created_at >= NOW() - INTERVAL '24 hours'
            
            UNION ALL
            
            -- Recent successful calls
            SELECT
                'call_conversion' as event_type,
                c.created_at,
                'phone' as vertical,
                'Phone' as location,
                'Someone' as anonymous_name
            FROM calls c
            WHERE c.outcome IN ('interested', 'qualified', 'converted')
            AND c.created_at >= NOW() - INTERVAL '6 hours'
        )
        SELECT * FROM recent_events
        WHERE 1=1
        """
        
        params = []
        
        if tenant and tenant != 'all':
            params.append(tenant)
            events_query += f" AND vertical = ${len(params)}"
            
        if vertical and vertical != 'all':
            params.append(vertical)  
            events_query += f" AND vertical = ${len(params)}"
        
        params.append(limit)
        events_query += f" ORDER BY created_at DESC LIMIT ${len(params)}"
        
        rows = await self.db.fetch(events_query, *params)
        
        # Format events for display
        events = []
        for row in rows:
            # Add some realistic time variance for display
            minutes_ago = random.randint(1, 180)  # 1-180 minutes ago
            display_time = datetime.now() - timedelta(minutes=minutes_ago)
            
            event_messages = {
                'booking': f"{row['anonymous_name']} from {row['location']} just booked a service",
                'purchase': f"{row['anonymous_name']} just purchased a template pack", 
                'subscription': f"{row['anonymous_name']} just started a subscription",
                'call_conversion': f"{row['anonymous_name']} just converted via phone call"
            }
            
            events.append({
                'id': f"{row['event_type']}_{row['created_at'].timestamp()}",
                'type': row['event_type'],
                'message': event_messages.get(row['event_type'], 'Someone just took action'),
                'location': row['location'],
                'vertical': row['vertical'],
                'time_ago': self._format_time_ago(minutes_ago),
                'timestamp': display_time.isoformat()
            })
        
        # Add some synthetic events if we don't have enough real ones
        if len(events) < 10:
            events.extend(self._generate_synthetic_events(10 - len(events), vertical))
        
        # Shuffle for more natural display
        random.shuffle(events)
        events = events[:limit]
        
        # Cache results
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(events))
        
        return events
    
    def _format_time_ago(self, minutes: int) -> str:
        """Format time ago string"""
        if minutes < 60:
            return f"{minutes} minutes ago"
        elif minutes < 1440:  # 24 hours
            hours = minutes // 60
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = minutes // 1440
            return f"{days} day{'s' if days > 1 else ''} ago"
    
    def _generate_synthetic_events(self, count: int, vertical: str = None) -> List[Dict]:
        """Generate synthetic social proof events when real data is sparse"""
        
        synthetic_events = []
        names = ['A***', 'B***', 'C***', 'D***', 'J***', 'M***', 'S***', 'R***']
        locations = ['CA', 'NY', 'TX', 'FL', 'IL', 'OH', 'PA', 'MI']
        
        vertical_messages = {
            'auto_detailing': [
                "just booked a premium detail service",
                "just scheduled paint protection",
                "just booked ceramic coating"
            ],
            'saas': [
                "just started a free trial",
                "just upgraded to premium",
                "just subscribed to Pro plan"
            ],
            'default': [
                "just took action",
                "just made a purchase",
                "just booked a service"
            ]
        }
        
        messages = vertical_messages.get(vertical, vertical_messages['default'])
        
        for i in range(count):
            minutes_ago = random.randint(5, 480)  # 5 minutes to 8 hours ago
            
            synthetic_events.append({
                'id': f"synthetic_{i}_{datetime.now().timestamp()}",
                'type': 'synthetic',
                'message': f"{random.choice(names)} from {random.choice(locations)} {random.choice(messages)}",
                'location': random.choice(locations),
                'vertical': vertical or 'general',
                'time_ago': self._format_time_ago(minutes_ago),
                'timestamp': (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
            })
        
        return synthetic_events