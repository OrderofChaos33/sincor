#!/bin/bash
# Production startup script for SINCOR

echo "🚀 Starting SINCOR in production mode..."

# Install dependencies
pip install -r requirements.txt

# Start with Gunicorn (production WSGI server)
echo "🔧 Starting Gunicorn production server..."
gunicorn --config gunicorn_config.py run_clean:application

echo "✅ SINCOR production server started on 0.0.0.0:8000"