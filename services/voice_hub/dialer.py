from twilio.rest import Client
import os
from datetime import datetime, time
from typing import Dict, Optional
import asyncpg

class VoiceDialer:
    def __init__(self):
        self.twilio_client = None
        if all(os.getenv(var) for var in ["TWILIO_SID", "TWILIO_TOKEN"]):
            self.twilio_client = Client(
                os.getenv("TWILIO_SID"), 
                os.getenv("TWILIO_TOKEN")
            )
        
        self.from_number = os.getenv("TWILIO_FROM")
        self.call_window = os.getenv("CALL_WINDOW_LOCAL", "09:00-20:00")
        
    def is_call_time_valid(self, phone_timezone: str = None) -> bool:
        """Check if current time is within calling window"""
        # Parse call window (e.g., "09:00-20:00")
        start_str, end_str = self.call_window.split("-")
        start_hour = int(start_str.split(":")[0])
        end_hour = int(end_str.split(":")[0])
        
        # For simplicity, use local time. In production, consider timezone conversion
        current_hour = datetime.now().hour
        
        return start_hour <= current_hour < end_hour
    
    async def initiate_call(self, lead_data: Dict, webhook_base_url: str) -> Dict:
        """Initiate outbound call via Twilio"""
        
        if not self.twilio_client:
            return {"status": "error", "message": "Twilio not configured"}
        
        if not self.from_number:
            return {"status": "error", "message": "Twilio FROM number not configured"}
        
        phone = lead_data.get("phone")
        if not phone:
            return {"status": "error", "message": "No phone number provided"}
        
        # Check calling window
        if not self.is_call_time_valid():
            return {"status": "deferred", "message": "Outside calling hours"}
        
        try:
            # Create call with webhook for status updates
            call = self.twilio_client.calls.create(
                to=phone,
                from_=self.from_number,
                url=f"{webhook_base_url}/voice/twiml",  # TwiML instructions
                status_callback=f"{webhook_base_url}/webhooks/voice-status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                record=True,  # Record call for quality
                machine_detection='Enable'  # Detect answering machines
            )
            
            return {
                "status": "initiated",
                "provider_call_id": call.sid,
                "to_number": phone,
                "from_number": self.from_number
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def generate_twiml_script(self, lead_data: Dict) -> str:
        """Generate TwiML script for the call"""
        
        # Simple script - could be dynamic based on vertical/lead data
        lead_name = lead_data.get("attributes", {}).get("name", "there")
        vertical = lead_data.get("vertical", "service")
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        Hello {lead_name}, this is Sarah calling about your recent interest in our {vertical} services.
        I have some great options that might be perfect for you.
        Please hold while I connect you to one of our specialists.
    </Say>
    <Pause length="2"/>
    <Say voice="alice">
        If you'd like to speak with someone right away, please press 1.
        To schedule a callback at a more convenient time, press 2.
        To be removed from our calling list, press 9.
    </Say>
    <Gather num_digits="1" action="/voice/gather" method="POST" timeout="10">
        <Say voice="alice">Please make your selection now.</Say>
    </Gather>
    <Say voice="alice">
        I didn't receive a response. We'll try calling you back at a better time. 
        Have a great day!
    </Say>
    <Hangup/>
</Response>"""
        
        return twiml
    
    def process_gather_response(self, digits: str, lead_data: Dict) -> str:
        """Process DTMF input from call recipient"""
        
        if digits == "1":
            # Connect to agent
            return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Great! Please hold while I connect you to a specialist.</Say>
    <Dial timeout="30" record="true">
        <Queue>support</Queue>
    </Dial>
    <Say voice="alice">Sorry, all our specialists are currently busy. We'll call you back shortly.</Say>
</Response>"""
        
        elif digits == "2":
            # Schedule callback
            return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        Thank you! We'll schedule a callback at a more convenient time.
        Someone will reach out to you within 24 hours. Have a great day!
    </Say>
    <Hangup/>
</Response>"""
        
        elif digits == "9":
            # Opt out
            return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        You have been removed from our calling list. Thank you and have a great day.
    </Say>
    <Hangup/>
</Response>"""
        
        else:
            # Invalid input
            return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">I didn't understand your selection. We'll try calling back later. Goodbye!</Say>
    <Hangup/>
</Response>"""