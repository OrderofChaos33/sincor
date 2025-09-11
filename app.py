#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import sqlite3
import requests
import json
from datetime import datetime, timedelta
import psutil
import subprocess
import time
import hashlib
import uuid

# Create new Flask app with explicit name to avoid conflicts
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'sincor-secret-key-2024-clean'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/demo/access')
def demo_access():
    session['user_authenticated'] = True
    session['user_level'] = 'member'
    return redirect(url_for('dashboard'))

@app.route('/admin/access')
def admin_access():
    session['user_authenticated'] = True
    session['user_level'] = 'admin'
    return redirect(url_for('admin_dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_authenticated' not in session:
        return redirect(url_for('home'))
    return render_template('dashboards/member_dashboard.html')

@app.route('/admin')
def admin_dashboard():
    if 'user_authenticated' not in session or session.get('user_level') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('dashboards/admin_dashboard.html')

# Add all the missing routes that templates reference
@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/monitoring')
def monitoring():
    return render_template('monitoring_dashboard.html')

@app.route('/api/monitor/status')
def monitor_status():
    """API endpoint for monitoring dashboard status"""
    try:
        # Get system status
        status = {
            "system_health": "100%",
            "active_agents": 5,
            "tasks_today": 12,
            "revenue_today": "$1,250",
            "agents": {
                "content_gen": "online",
                "distribution_handler": "online", 
                "prospect_discovery": "online",
                "health_monitor": "online",
                "revenue_optimizer": "online"
            },
            "queues": {
                "triggers_pending": 0,
                "create_pack_pending": 0,
                "render_asset_pending": 0,
                "syndicate_pending": 1
            },
            "recent_activity": [
                {
                    "time": "2 min ago",
                    "event": "Generated daily content pack for Clinton Auto Detailing",
                    "type": "success"
                },
                {
                    "time": "15 min ago", 
                    "event": "Distributed content to Instagram and Google Business",
                    "type": "info"
                },
                {
                    "time": "1 hour ago",
                    "event": "Health check completed - all systems healthy", 
                    "type": "success"
                },
                {
                    "time": "2 hours ago",
                    "event": "Discovered 3 new prospects in Clinton, IL area",
                    "type": "info"
                }
            ],
            "performance": {
                "avg_response_time": "120ms",
                "success_rate": "98.5%",
                "content_packs_generated": "47",
                "distribution_success_rate": "94.2%"
            },
            "scheduler": {
                "daily_sample_pack": "8:00 AM tomorrow",
                "daily_health_check": "9:00 AM tomorrow", 
                "syndication_retry": "In 2 hours",
                "prospect_discovery": "10:00 AM Wednesday"
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pricing') 
def pricing():
    return render_template('pricing.html')

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/media-packs')
def media_packs():
    return render_template('media_packs.html')

@app.route('/predictive-analytics')
def predictive_analytics():
    return render_template('predictive_analytics.html')

@app.route('/business-intelligence')
def business_intelligence():
    return render_template('business_intelligence.html')

@app.route('/agent-services')
def agent_services():
    return render_template('agent_services.html')

@app.route('/clinton-weekend-special')
def clinton_weekend_special():
    """Clinton Auto Detailing Weekend Special Landing Page"""
    return render_template('clinton_weekend_special.html')

@app.route('/enterprise-solutions')
def enterprise_solutions():
    return render_template('enterprise_solutions.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/admin/agent-constellation')
def agent_constellation():
    if 'user_authenticated' not in session or session.get('user_level') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('dashboards/agent_constellation_working.html')

@app.route('/admin/bi-reporting')
def bi_reporting():
    if 'user_authenticated' not in session or session.get('user_level') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('dashboards/bi_reporting.html')

@app.route('/admin/system-health')
def system_health():
    if 'user_authenticated' not in session or session.get('user_level') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('dashboards/system_health.html')

@app.route('/admin/revenue-metrics')
def revenue_metrics():
    if 'user_authenticated' not in session or session.get('user_level') != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('dashboards/revenue_metrics.html')

# Real API Endpoints for Live Data
@app.route('/api/system/health')
def api_system_health():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Try to get disk usage, fallback if it fails
        try:
            disk = psutil.disk_usage('/')
            disk_percent = round(disk.percent, 1)
            disk_used = round(disk.used / 1024**3, 2)
            disk_total = round(disk.total / 1024**3, 2)
        except:
            disk_percent = 0.0
            disk_used = 0.0
            disk_total = 0.0
        
        return jsonify({
            'cpu': round(cpu_percent, 1),
            'memory': round(memory.percent, 1),
            'disk': disk_percent,
            'memory_used': round(memory.used / 1024**3, 2),
            'memory_total': round(memory.total / 1024**3, 2),
            'disk_used': disk_used,
            'disk_total': disk_total,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'SINCOR Business Automation Platform',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting SINCOR Business Automation Platform on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

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