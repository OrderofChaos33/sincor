#!/usr/bin/env python3
"""
Minimal SINCOR app for Railway deployment test
"""
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return f'''
    <h1>SINCOR LLC - AI Business Automation Platform</h1>
    <p>PayPal Test: {bool(os.getenv('PAYPAL_REST_API_ID'))}</p>
    <p>Environment: {os.getenv('PAYPAL_ENV', 'not-set')}</p>
    <p>Status: LIVE</p>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'SINCOR'}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)