from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    paypal_id = os.getenv('PAYPAL_REST_API_ID')
    return f'<h1>PAYPAL TEST: {bool(paypal_id)}</h1>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))