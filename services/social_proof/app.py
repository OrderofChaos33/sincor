from fastapi import FastAPI, Response, Query
from fastapi.responses import HTMLResponse
import asyncpg
import aioredis
import os
from typing import Optional
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from events import SocialProofEventManager

app = FastAPI()
DB_DSN = os.getenv("DB_DSN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SOCIALPROOF_MAX_EVENTS = int(os.getenv("SOCIALPROOF_MAX_EVENTS", "20"))

# Metrics
WIDGET_REQUESTS = Counter("social_proof_widget_requests_total", "Widget script requests", ["tenant", "vertical"])
EVENT_REQUESTS = Counter("social_proof_events_total", "Event API requests", ["tenant"])

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.connect(DB_DSN)
    app.state.redis = await aioredis.from_url(REDIS_URL)
    app.state.events = SocialProofEventManager(app.state.db, app.state.redis)

@app.get("/health")
async def health():
    return {"ok": True, "service": "social_proof"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/widget.js")
async def get_widget_script(tenant: str = Query(...), vertical: Optional[str] = None):
    """Serve embeddable social proof widget JavaScript"""
    
    WIDGET_REQUESTS.labels(tenant=tenant, vertical=vertical or "all").inc()
    
    # JavaScript widget code
    widget_js = f"""
(function() {{
    // Social Proof Widget Configuration
    const config = {{
        tenant: '{tenant}',
        vertical: '{vertical or ""}',
        apiUrl: window.location.origin,
        maxEvents: {SOCIALPROOF_MAX_EVENTS},
        displayDuration: 5000, // 5 seconds per notification
        fadeInDuration: 500,
        fadeOutDuration: 300
    }};
    
    // Widget state
    let eventQueue = [];
    let currentNotification = null;
    let isVisible = false;
    
    // Create widget container
    function createWidget() {{
        const widget = document.createElement('div');
        widget.id = 'sincor-social-proof-widget';
        widget.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            font-weight: 500;
            max-width: 300px;
            z-index: 10000;
            opacity: 0;
            transform: translateX(-100%);
            transition: all 0.3s ease;
            cursor: pointer;
            border-left: 4px solid #ffd700;
        `;
        
        widget.innerHTML = `
            <div style="display: flex; align-items: center;">
                <div style="background: rgba(255,255,255,0.2); border-radius: 50%; width: 8px; height: 8px; margin-right: 8px; animation: pulse 2s infinite;"></div>
                <div id="social-proof-message"></div>
            </div>
        `;
        
        // Add pulse animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {{
                0% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.7; transform: scale(1.1); }}
                100% {{ opacity: 1; transform: scale(1); }}
            }}
        `;
        document.head.appendChild(style);
        
        // Click handler to dismiss
        widget.addEventListener('click', hideNotification);
        
        document.body.appendChild(widget);
        return widget;
    }}
    
    // Show notification
    function showNotification(event) {{
        if (!currentNotification) {{
            currentNotification = createWidget();
        }}
        
        const messageEl = currentNotification.querySelector('#social-proof-message');
        messageEl.textContent = event.message;
        
        // Show with animation
        currentNotification.style.opacity = '1';
        currentNotification.style.transform = 'translateX(0)';
        isVisible = true;
        
        // Auto-hide after display duration
        setTimeout(() => {{
            hideNotification();
        }}, config.displayDuration);
    }}
    
    // Hide notification
    function hideNotification() {{
        if (currentNotification && isVisible) {{
            currentNotification.style.opacity = '0';
            currentNotification.style.transform = 'translateX(-100%)';
            isVisible = false;
            
            setTimeout(() => {{
                if (eventQueue.length > 0) {{
                    const nextEvent = eventQueue.shift();
                    setTimeout(() => showNotification(nextEvent), 1000);
                }}
            }}, config.fadeOutDuration);
        }}
    }}
    
    // Fetch events from API
    async function fetchEvents() {{
        try {{
            const params = new URLSearchParams({{
                tenant: config.tenant,
                limit: config.maxEvents
            }});
            
            if (config.vertical) {{
                params.set('vertical', config.vertical);
            }}
            
            const response = await fetch(`${{config.apiUrl}}/events?${{params}}`);
            const data = await response.json();
            return data.events || [];
        }} catch (error) {{
            console.warn('Social proof widget: Failed to fetch events', error);
            return [];
        }}
    }}
    
    // Start the widget
    async function init() {{
        // Wait for page to load
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
            return;
        }}
        
        // Fetch initial events
        const events = await fetchEvents();
        
        if (events.length === 0) {{
            return; // No events to show
        }}
        
        // Add events to queue
        eventQueue = [...events];
        
        // Show first event after a short delay
        setTimeout(() => {{
            if (eventQueue.length > 0) {{
                const firstEvent = eventQueue.shift();
                showNotification(firstEvent);
            }}
        }}, 3000); // 3 second delay after page load
        
        // Refresh events periodically
        setInterval(async () => {{
            const freshEvents = await fetchEvents();
            // Add new events to queue (avoid duplicates)
            const newEvents = freshEvents.filter(e => 
                !eventQueue.some(qe => qe.id === e.id)
            );
            eventQueue.push(...newEvents);
        }}, 60000); // Refresh every minute
    }}
    
    // Initialize widget
    init();
}})();
"""
    
    return Response(content=widget_js, media_type="application/javascript")

@app.get("/events")
async def get_events(
    tenant: str = Query(...),
    vertical: Optional[str] = None,
    limit: int = Query(SOCIALPROOF_MAX_EVENTS, le=50)
):
    """Get recent events for social proof display"""
    
    EVENT_REQUESTS.labels(tenant=tenant).inc()
    
    events = await app.state.events.get_recent_events(
        tenant=tenant,
        vertical=vertical, 
        limit=limit
    )
    
    return {"events": events, "count": len(events)}

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Demo page showing the social proof widget in action"""
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Social Proof Widget Demo</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }
        .demo-container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; }
        .cta-button { 
            background: #667eea; 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 5px; 
            font-size: 16px; 
            cursor: pointer; 
            margin: 20px 10px;
        }
        .cta-button:hover { background: #5a6fd8; }
        .demo-section { margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="demo-container">
        <h1>Social Proof Widget Demo</h1>
        <p>This page demonstrates the social proof widget in action. Look for notifications in the top-left corner!</p>
        
        <div class="demo-section">
            <h3>Example Service Page</h3>
            <p>Transform your business with our premium auto detailing services. Join hundreds of satisfied customers!</p>
            <button class="cta-button">Book Now</button>
            <button class="cta-button">Get Quote</button>
        </div>
        
        <div class="demo-section">
            <h3>Widget Integration</h3>
            <p>To add this widget to your site, include this script tag:</p>
            <code>&lt;script src="/widget.js?tenant=demo&vertical=auto_detailing"&gt;&lt;/script&gt;</code>
        </div>
        
        <div class="demo-section">
            <h3>Customization Options</h3>
            <ul>
                <li><strong>tenant</strong> - Your tenant/vertical identifier</li>
                <li><strong>vertical</strong> - Filter events by vertical (optional)</li>
                <li><strong>position</strong> - Widget positioning (future feature)</li>
                <li><strong>theme</strong> - Color theme customization (future feature)</li>
            </ul>
        </div>
    </div>
    
    <!-- Load the social proof widget -->
    <script src="/widget.js?tenant=demo&vertical=auto_detailing"></script>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

@app.get("/analytics")
async def widget_analytics():
    """Get social proof widget analytics"""
    
    # Get widget impression stats (would be tracked via additional endpoint)
    stats = {
        "total_widget_loads": 0,  # Placeholder - would track via beacon
        "active_tenants": 0,
        "events_served_24h": 0
    }
    
    # Count recent events served
    event_count = await app.state.db.fetchval("""
        SELECT COUNT(*) FROM (
            SELECT created_at FROM delivery_ledger WHERE created_at >= NOW() - INTERVAL '24 hours'
            UNION ALL
            SELECT created_at FROM purchases WHERE created_at >= NOW() - INTERVAL '24 hours'  
            UNION ALL
            SELECT created_at FROM subscriptions WHERE created_at >= NOW() - INTERVAL '24 hours'
        ) all_events
    """)
    
    stats["events_served_24h"] = event_count or 0
    
    # Count active tenants (simplified)
    tenant_count = await app.state.db.fetchval("""
        SELECT COUNT(DISTINCT vertical) FROM leads WHERE created_at >= NOW() - INTERVAL '7 days'
    """)
    
    stats["active_tenants"] = tenant_count or 0
    
    return {
        "service": "social_proof",
        "status": "active", 
        "stats": stats,
        "widget_url": "/widget.js?tenant={tenant}&vertical={vertical}",
        "demo_url": "/demo"
    }