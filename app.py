from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
    <head><title>SINCOR - AI Business Automation Platform</title></head>
    <body style="background: black; color: white; font-family: Arial; padding: 50px; text-align: center;">
        <h1 style="font-size: 60px; color: #00ff00;">SINCOR</h1>
        <h2 style="color: #0088ff;">AI Business Automation Platform</h2>
        <p style="font-size: 24px;">Your $100K Platform is LIVE</p>
        <div style="margin: 40px;">
            <h3 style="color: #ffff00;">Services Available:</h3>
            <p>💡 Instant Business Intelligence: $2,500 - $15,000</p>
            <p>🤖 Agent Services: $500 - $5,000/month</p>
            <p>📊 Predictive Analytics: $6,000 - $25,000</p>
            <p>🤝 Enterprise Partnerships: $50,000 - $200,000</p>
        </div>
        <p style="color: #00ff00; font-size: 18px; font-weight: bold;">[LIVE] SINCOR Production System</p>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)