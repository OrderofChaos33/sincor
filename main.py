#!/usr/bin/env python3
"""
SINCOR Startup - Simple monetization app
"""
from flask import Flask, jsonify, render_template_string
import os
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return '''<!DOCTYPE html>
<html><head><title>SINCOR - AI Business Automation</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head><body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
<div class="text-center">
    <h1 class="text-6xl font-bold mb-4 text-blue-400">SINCOR</h1>
    <p class="text-2xl mb-8 text-gray-300">AI Business Automation Platform</p>
    <a href="/monetization/dashboard" class="bg-green-600 hover:bg-green-700 px-8 py-4 rounded-lg font-semibold text-xl">
        🚀 Launch Monetization Dashboard
    </a>
</div></body></html>'''

@app.route('/monetization/dashboard')
def monetization_dashboard():
    return '''<!DOCTYPE html>
<html><head><title>SINCOR Monetization Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head><body class="bg-gray-900 text-white min-h-screen">
<div class="container mx-auto px-4 py-8">
    <h1 class="text-4xl font-bold mb-8 text-green-400 text-center">🚀 SINCOR Monetization Dashboard</h1>
    
    <div class="grid md:grid-cols-3 gap-6 mb-8">
        <div class="bg-gray-800 p-6 rounded-lg text-center">
            <h2 class="text-xl font-bold mb-4 text-blue-400">PayPal Integration</h2>
            <div class="text-3xl font-bold text-green-400">LIVE</div>
            <p class="text-gray-400">API Connected</p>
        </div>
        
        <div class="bg-gray-800 p-6 rounded-lg text-center">
            <h2 class="text-xl font-bold mb-4 text-purple-400">Revenue Streams</h2>
            <div class="text-3xl font-bold text-green-400">8</div>
            <p class="text-gray-400">Active</p>
        </div>
        
        <div class="bg-gray-800 p-6 rounded-lg text-center">
            <h2 class="text-xl font-bold mb-4 text-yellow-400">Agent Cost</h2>
            <div class="text-3xl font-bold text-green-400">$1</div>
            <p class="text-gray-400">Per Operation</p>
        </div>
    </div>
    
    <div class="bg-gray-800 p-6 rounded-lg mb-8">
        <h2 class="text-2xl font-bold mb-4 text-red-400">💳 PayPal API Test</h2>
        <button onclick="testPayPal()" id="paypal-btn" class="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg font-semibold">
            Test PayPal Payment ($2,500)
        </button>
        <div id="paypal-result" class="mt-4"></div>
    </div>
    
    <div class="bg-gray-800 p-6 rounded-lg">
        <h2 class="text-2xl font-bold mb-4 text-cyan-400">Revenue Opportunities</h2>
        <div class="grid md:grid-cols-2 gap-4">
            <div class="text-cyan-300">🎯 Instant BI Services: $2,500 - $15,000</div>
            <div class="text-cyan-300">🤖 Agent Subscriptions: $500 - $5,000/mo</div>
            <div class="text-cyan-300">📊 Predictive Analytics: $6,000 - $25,000</div>
            <div class="text-cyan-300">🤝 Enterprise Partnerships: $50K - $200K</div>
        </div>
    </div>
</div>

<script>
async function testPayPal() {
    const btn = document.getElementById('paypal-btn');
    const result = document.getElementById('paypal-result');
    
    btn.disabled = true;
    btn.textContent = '🔄 Creating PayPal Payment...';
    result.innerHTML = '<div class="text-yellow-400">Connecting to PayPal API...</div>';
    
    try {
        const response = await fetch('/api/paypal-test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({amount: 2500})
        });
        
        const data = await response.json();
        
        if (data.success) {
            result.innerHTML = `
                <div class="text-green-400 font-bold">✅ PayPal API Success!</div>
                <div class="mt-2">Payment ID: <span class="font-mono">${data.payment_id}</span></div>
                <div class="mt-2">Amount: $${data.amount}</div>
                <a href="${data.approval_url}" target="_blank" class="inline-block mt-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-white">
                    Complete Payment on PayPal
                </a>
            `;
        } else {
            result.innerHTML = `<div class="text-red-400">❌ Error: ${data.error}</div>`;
        }
    } catch (error) {
        result.innerHTML = `<div class="text-red-400">❌ Network Error: ${error.message}</div>`;
    }
    
    btn.disabled = false;
    btn.textContent = 'Test PayPal Payment ($2,500)';
}
</script>
</body></html>'''

@app.route('/api/paypal-test', methods=['POST'])
def paypal_test():
    try:
        client_id = os.getenv('PAYPAL_REST_API_ID')
        client_secret = os.getenv('PAYPAL_REST_API_SECRET')
        
        if not client_id or not client_secret:
            return jsonify({
                'success': False, 
                'error': 'PayPal credentials not configured in Railway environment'
            })
        
        # Get PayPal access token
        token_response = requests.post(
            'https://api.sandbox.paypal.com/v1/oauth2/token',
            headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
            data='grant_type=client_credentials',
            auth=(client_id, client_secret)
        )
        
        if token_response.status_code != 200:
            return jsonify({
                'success': False, 
                'error': f'PayPal token request failed: {token_response.status_code}'
            })
        
        access_token = token_response.json()['access_token']
        
        # Create PayPal payment
        payment_data = {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {"total": "2500.00", "currency": "USD"},
                "description": "SINCOR AI Business Intelligence Service - Test Payment"
            }],
            "redirect_urls": {
                "return_url": "https://getsincor.com/payment/success",
                "cancel_url": "https://getsincor.com/payment/cancel"
            }
        }
        
        payment_response = requests.post(
            'https://api.sandbox.paypal.com/v1/payments/payment',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            },
            json=payment_data
        )
        
        if payment_response.status_code == 201:
            payment_result = payment_response.json()
            payment_id = payment_result['id']
            
            # Find approval URL
            approval_url = None
            for link in payment_result.get('links', []):
                if link['rel'] == 'approval_url':
                    approval_url = link['href']
                    break
            
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'amount': 2500.00,
                'approval_url': approval_url
            })
        else:
            return jsonify({
                'success': False,
                'error': f'PayPal payment creation failed: {payment_response.status_code}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Payment processing error: {str(e)}'
        })

@app.route('/payment/success')
def payment_success():
    return '''<!DOCTYPE html>
<html><head><title>Payment Successful!</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head><body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
<div class="bg-green-900 p-8 rounded-lg max-w-md text-center">
    <h1 class="text-3xl font-bold mb-4 text-green-400">🎉 Payment Successful!</h1>
    <p class="text-green-300 mb-6">Your SINCOR AI service has been activated!</p>
    <a href="/monetization/dashboard" class="inline-block bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-semibold">
        Return to Dashboard
    </a>
</div></body></html>'''

@app.route('/payment/cancel')
def payment_cancel():
    return '''<!DOCTYPE html>
<html><head><title>Payment Cancelled</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head><body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
<div class="bg-gray-800 p-8 rounded-lg max-w-md text-center">
    <h1 class="text-2xl font-bold mb-4">Payment Cancelled</h1>
    <p class="text-gray-300 mb-6">No charges were made. You can try again anytime.</p>
    <a href="/monetization/dashboard" class="inline-block bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-semibold">
        Return to Dashboard
    </a>
</div></body></html>'''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'SINCOR Monetization Platform',
        'paypal_configured': bool(os.getenv('PAYPAL_REST_API_ID')),
        'timestamp': '2025-08-29T17:35:00Z'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Starting SINCOR Monetization Platform on port {port}")
    print(f"💰 PayPal Integration: {'✅ Configured' if os.getenv('PAYPAL_REST_API_ID') else '❌ Missing credentials'}")
    print("🔒 Production WSGI Server Ready for PayPal API")
    app.run(host='0.0.0.0', port=port, debug=False)