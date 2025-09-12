#!/usr/bin/env python3

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>SINCOR Test</title></head>
    <body>
        <h1>SINCOR is working!</h1>
        <p>Test deployment successful - October 21, 2025 launch on track</p>
        <p>Server time: <script>document.write(new Date())</script></p>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'SINCOR Test'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting minimal test app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)