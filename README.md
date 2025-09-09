# SINCOR - Advanced Business Intelligence Platform

**Live URL:** [https://getsincor.com](https://getsincor.com)  
**Deploy Branch:** `main` (production-ready)

## Quick Start

### Local Development
```bash
# Clone and setup
git clone https://github.com/OrderofChaos33/sincor.git
cd sincor-clean

# Install dependencies  
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your API keys

# Run locally
python app.py
# Access at http://localhost:8000
```

### Production Deployment (Railway)
- **Deploy Branch:** `main`  
- **Entry Point:** `app.py`
- **Procfile:** `web: gunicorn app:app`
- **Environment:** See variables below

## Environment Variables (Required)

### Core System
```
DATABASE_URL=sqlite:///sincor.db
REDIS_URL=redis://localhost:6379
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
```

### Business Configuration  
```
BUSINESS_NAME=Your Business Name
BUSINESS_PHONE=your_phone_number
BUSINESS_EMAIL=your_email@example.com
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

### API Integrations
```
GOOGLE_API_KEY=your_google_api_key
FACEBOOK_ACCESS_TOKEN=your_facebook_token
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

## System Architecture

### Core Services
- **Main App** (`app.py`) - Flask web application
- **Marketing Workflow** - AI content generation and distribution  
- **Analytics API** - Revenue tracking and optimization
- **Scheduler** - Automated daily content generation
- **Marketplace** - Template and pack sales

### Agent System
- **Content Generation Agent** - Creates $500+ media packs
- **Distribution Handler** - Multi-channel content syndication
- **Health Monitor** - System status tracking

## Features

✅ **AI Content Generation** - Automated $500+ marketing packs  
✅ **Multi-Channel Distribution** - Instagram, Facebook, Google Business, Email  
✅ **Revenue Optimization** - 17-point monetization system  
✅ **Production Scheduler** - Daily content generation 8AM-5PM M-F  
✅ **Real-time Monitoring** - System health and performance tracking  

## Status

- **System Health:** ✅ Operational  
- **Email Distribution:** ✅ Working  
- **Daily Scheduler:** ✅ Running  
- **Content Generation:** ✅ Active (89% success rate)  
- **Revenue Streams:** ✅ Multiple channels active  

## Tech Stack

- **Backend:** Python 3.13, Flask 3.0
- **Database:** SQLite (local), PostgreSQL (production)
- **Caching:** Redis 5.0  
- **Scheduling:** Croniter with Central timezone
- **Deployment:** Railway, Docker support
- **Monitoring:** Real-time dashboards, health checks

## Contributing

1. Use `main` branch for production-ready code
2. All commits must pass health checks  
3. Environment variables required for testing
4. Follow existing code patterns and documentation

Last updated: 2025-09-09
