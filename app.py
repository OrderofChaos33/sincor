from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import os
from datetime import datetime

app = FastAPI(title="SINCOR AI Business Automation Platform")

@app.get("/", response_class=HTMLResponse)
def home():
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>SINCOR AI Business Automation Platform</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-900 text-white min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <div class="text-center mb-12">
                <h1 class="text-6xl font-bold mb-4 text-blue-400">SINCOR</h1>
                <p class="text-2xl mb-8 text-gray-300">AI Business Automation Platform</p>
                <div class="text-lg text-gray-400 mb-8">
                    Production System - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </div>
            </div>

            <div class="grid md:grid-cols-3 gap-8 mb-12">
                <div class="bg-gray-800 p-6 rounded-lg text-center">
                    <h2 class="text-xl font-bold mb-4 text-green-400">💡 Instant BI</h2>
                    <p class="text-gray-300 mb-4">Get business intelligence in seconds, not weeks</p>
                    <div class="text-2xl font-bold text-green-400">$2,500 - $15,000</div>
                    <p class="text-sm text-gray-400">Per analysis</p>
                </div>

                <div class="bg-gray-800 p-6 rounded-lg text-center">
                    <h2 class="text-xl font-bold mb-4 text-purple-400">🤖 Agent Services</h2>
                    <p class="text-gray-300 mb-4">AI agents that scale your business operations</p>
                    <div class="text-2xl font-bold text-purple-400">$500 - $5,000/mo</div>
                    <p class="text-sm text-gray-400">Subscription</p>
                </div>

                <div class="bg-gray-800 p-6 rounded-lg text-center">
                    <h2 class="text-xl font-bold mb-4 text-yellow-400">📊 Predictive Analytics</h2>
                    <p class="text-gray-300 mb-4">Forecast market trends and opportunities</p>
                    <div class="text-2xl font-bold text-yellow-400">$6,000 - $25,000</div>
                    <p class="text-sm text-gray-400">Per project</p>
                </div>
            </div>

            <div class="text-center">
                <a href="/dashboard" class="bg-green-600 hover:bg-green-700 px-8 py-4 rounded-lg font-semibold text-xl mr-4">
                    Launch Dashboard
                </a>
                <a href="/services" class="bg-blue-600 hover:bg-blue-700 px-8 py-4 rounded-lg font-semibold text-xl">
                    View Services
                </a>
            </div>

            <div class="mt-12 text-center">
                <p class="text-green-400 text-xl font-bold">[LIVE] SINCOR Production System</p>
                <p class="text-gray-400">getsincor.com - Autonomous Business Intelligence</p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>SINCOR Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-900 text-white min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold mb-8 text-green-400 text-center">SINCOR Command Center</h1>
            <div class="text-center">
                <p class="text-2xl text-blue-400 mb-8">AI Business Automation Platform</p>
                <div class="bg-gray-800 p-6 rounded-lg max-w-2xl mx-auto">
                    <h2 class="text-xl font-bold mb-4 text-yellow-400">Platform Status: ONLINE</h2>
                    <p class="text-gray-300">All SINCOR systems operational</p>
                    <div class="mt-6">
                        <a href="/" class="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold mr-4">Home</a>
                        <a href="/services" class="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg font-semibold">Services</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.get("/services", response_class=HTMLResponse)
def services():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>SINCOR Services</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-900 text-white min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold mb-8 text-blue-400 text-center">SINCOR Services</h1>
            <div class="grid md:grid-cols-2 gap-8">
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-green-400">💡 Instant Business Intelligence</h2>
                    <p class="text-gray-300 mb-4">Comprehensive business analysis in minutes</p>
                    <div class="text-3xl font-bold text-green-400">$2,500 - $15,000</div>
                </div>
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-purple-400">🤖 Agent Services</h2>
                    <p class="text-gray-300 mb-4">AI agents for business operations</p>
                    <div class="text-3xl font-bold text-purple-400">$500 - $5,000/mo</div>
                </div>
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-yellow-400">📊 Predictive Analytics</h2>
                    <p class="text-gray-300 mb-4">Market trend forecasting</p>
                    <div class="text-3xl font-bold text-yellow-400">$6,000 - $25,000</div>
                </div>
                <div class="bg-gray-800 p-6 rounded-lg">
                    <h2 class="text-2xl font-bold mb-4 text-red-400">🤝 Enterprise Partnerships</h2>
                    <p class="text-gray-300 mb-4">Strategic revenue partnerships</p>
                    <div class="text-3xl font-bold text-red-400">$50,000 - $200,000</div>
                </div>
            </div>
            <div class="text-center mt-8">
                <a href="/" class="bg-blue-600 hover:bg-blue-700 px-8 py-4 rounded-lg font-semibold text-xl">Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    '''

# Uvicorn entry if run locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
