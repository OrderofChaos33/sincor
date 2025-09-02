#!/usr/bin/env python3
"""
Fresh SINCOR entry point for Railway deployment
"""
from flask import Flask, jsonify
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/')
def home():
    return f'''
    <h1>SINCOR AI Business Automation Platform</h1>
    <h2>FRESH DEPLOYMENT - {datetime.now()}</h2>
    <p><strong>PayPal Configured:</strong> {bool(os.getenv('PAYPAL_REST_API_ID'))}</p>
    <p><strong>Environment:</strong> {os.getenv('PAYPAL_ENV', 'not-set')}</p>
    <div>
        <a href="/health">Health Check</a> | 
        <a href="/services">Services</a> | 
        <a href="/test">Test Route</a>
    </div>
    '''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'SINCOR Fresh Deployment',
        'timestamp': datetime.now().isoformat(),
        'paypal_configured': bool(os.getenv('PAYPAL_REST_API_ID')),
        'environment': os.getenv('PAYPAL_ENV', 'production')
    })

@app.route('/services') 
def services():
    return jsonify({
        'message': 'SINCOR Services Endpoint Working',
        'available_services': [
            'Business Intelligence',
            'Lead Generation', 
            'Payment Processing',
            'AI Automation'
        ],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test')
def test():
    return jsonify({
        'message': 'SINCOR Test Route Success',
        'timestamp': datetime.now().isoformat(),
        'railway_deployment': True
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f">> Starting SINCOR Fresh Deployment on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)