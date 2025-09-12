#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os

# Create Flask app
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

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/media_packs')
def media_packs():
    return render_template('media_packs.html')

@app.route('/pricing') 
def pricing():
    return render_template('pricing.html')

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/bi')
def bi():
    return render_template('bi.html')

@app.route('/agent_services')
def agent_services():
    return render_template('agent_services.html')

@app.route('/enterprise')
def enterprise():
    return render_template('enterprise.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'SINCOR'}

if __name__ == '__main__':
    print("Starting SINCOR Clean App...")
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)