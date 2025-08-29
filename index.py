from flask import Flask, jsonify, request
import os
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>SINCOR MONETIZATION LIVE!</h1>
    <p><a href="/monetization/dashboard">CLICK HERE FOR PAYPAL DASHBOARD</a></p>
    '''

@app.route('/monetization/dashboard')
def dashboard():
    return '''
    <h1>SINCOR PayPal Test</h1>
    <button onclick="test()">TEST PAYPAL NOW</button>
    <div id="result"></div>
    <script>
    async function test() {
        const response = await fetch('/test-paypal', {method: 'POST'});
        const data = await response.json();
        document.getElementById('result').innerHTML = JSON.stringify(data);
    }
    </script>
    '''

@app.route('/test-paypal', methods=['POST'])
def test_paypal():
    client_id = os.getenv('PAYPAL_REST_API_ID')
    if not client_id:
        return jsonify({'error': 'PayPal not configured'})
    
    try:
        response = requests.post(
            'https://api.sandbox.paypal.com/v1/oauth2/token',
            data='grant_type=client_credentials',
            auth=(client_id, os.getenv('PAYPAL_REST_API_SECRET'))
        )
        return jsonify({'success': True, 'status': response.status_code})
    except:
        return jsonify({'error': 'PayPal API failed'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)