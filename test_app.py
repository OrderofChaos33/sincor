#!/usr/bin/env python3

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SINCOR Test</title>
    </head>
    <body>
        <h1>SINCOR is working!</h1>
        <p>Railway deployment test successful.</p>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy', 'message': 'SINCOR Test App Running'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting test app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)