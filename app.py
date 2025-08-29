#!/usr/bin/env python3
"""
SINCOR Startup - Routes to monetization app
"""
from sincor.railway_monetization_app import app

if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)