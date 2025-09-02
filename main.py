#!/usr/bin/env python3
"""
SINCOR AI Business Automation Platform - Railway Entry Point
Main entry point for Railway deployment
"""

if __name__ == "__main__":
    from simple import app
    import os
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)