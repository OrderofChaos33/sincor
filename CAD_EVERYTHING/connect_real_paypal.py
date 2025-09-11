#!/usr/bin/env python3
"""
Connect to REAL PayPal API and get actual balance/transactions
No simulation - real API calls only
"""
import requests
import os
import base64
from datetime import datetime, timedelta

class RealPayPalAPI:
    def __init__(self):
        # Get real PayPal credentials from environment
        self.client_id = os.getenv('PAYPAL_CLIENT_ID')
        self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET') 
        self.sandbox = os.getenv('PAYPAL_SANDBOX', 'true').lower() == 'true'
        
        if self.sandbox:
            self.base_url = 'https://api-m.sandbox.paypal.com'
        else:
            self.base_url = 'https://api-m.paypal.com'
            
        self.access_token = None
    
    def get_access_token(self):
        """Get real PayPal access token"""
        if not self.client_id or not self.client_secret:
            print("ERROR: PayPal credentials not found in environment")
            print("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET")
            return None
            
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Accept': 'application/json',
            'Accept-Language': 'en_US',
        }
        
        data = 'grant_type=client_credentials'
        
        response = requests.post(
            f'{self.base_url}/v1/oauth2/token',
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            print(f"✅ PayPal API Connected: {self.base_url}")
            return self.access_token
        else:
            print(f"❌ PayPal API Error: {response.status_code}")
            print(response.text)
            return None
    
    def get_account_balance(self):
        """Get real PayPal account balance"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        # Get account balance
        response = requests.get(
            f'{self.base_url}/v1/reporting/balances',
            headers=headers
        )
        
        if response.status_code == 200:
            balance_data = response.json()
            return balance_data
        else:
            print(f"Balance API Error: {response.status_code}")
            return None
    
    def get_recent_transactions(self, days=7):
        """Get recent PayPal transactions"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        # Get transactions from last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            'start_date': start_date.isoformat() + 'Z',
            'end_date': end_date.isoformat() + 'Z',
            'fields': 'all'
        }
        
        response = requests.get(
            f'{self.base_url}/v1/reporting/transactions',
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Transactions API Error: {response.status_code}")
            return None

def main():
    print("CONNECTING TO REAL PAYPAL API")
    print("=" * 40)
    
    paypal = RealPayPalAPI()
    
    # Test connection
    token = paypal.get_access_token()
    if not token:
        print("❌ Failed to connect to PayPal API")
        print("\nTo connect:")
        print("1. Set PAYPAL_CLIENT_ID in environment")
        print("2. Set PAYPAL_CLIENT_SECRET in environment") 
        print("3. Set PAYPAL_SANDBOX=false for live account")
        return
    
    # Get real balance
    balance = paypal.get_account_balance()
    if balance:
        print("✅ REAL PAYPAL BALANCE:")
        print(balance)
    
    # Get real transactions  
    transactions = paypal.get_recent_transactions()
    if transactions:
        print("✅ RECENT TRANSACTIONS:")
        for tx in transactions.get('transaction_details', []):
            amount = tx.get('transaction_info', {}).get('transaction_amount', {})
            print(f"  {amount.get('value', 'N/A')} {amount.get('currency_code', 'USD')}")

if __name__ == "__main__":
    main()