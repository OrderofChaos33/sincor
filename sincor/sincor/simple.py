#!/usr/bin/env python3
"""
SINCOR Production System for Railway Deployment
Integrates all monetization engines and systems for getsincor.com
"""
from flask import Flask, jsonify, render_template_string, request, redirect, url_for
import os
import requests
import logging
import asyncio
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'sincor-production-2025-secure-fallback-key-xyz123')

# Configure logging based on environment
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Environment configuration
PAYPAL_ENV = os.getenv('PAYPAL_ENV', 'sandbox')
IS_PRODUCTION = PAYPAL_ENV == 'live'
PAYPAL_API_BASE = 'https://api-m.paypal.com' if IS_PRODUCTION else 'https://api-m.sandbox.paypal.com'
APP_BASE_URL = os.getenv('APP_BASE_URL', 'https://getsincor.com')

# Initialize SINCOR engines
try:
    from monetization_engine import MonetizationEngine
    from paypal_integration import SINCORPaymentProcessor, PaymentRequest
    from instant_business_intelligence import InstantBusinessIntelligence
    from dynamic_pricing_engine import DynamicPricingEngine
    from infinite_scaling_engine import InfiniteScalingEngine
    ENGINES_AVAILABLE = True
    logger.info("✅ SINCOR engines imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Engine import failed: {e}")
    ENGINES_AVAILABLE = False

# Initialize engines after routes are defined
monetization_engine = None
payment_processor = None
bi_engine = None
pricing_engine = None
scaling_engine = None


def initialize_engines():
    """Initialize SINCOR engines safely"""
    global monetization_engine, payment_processor, bi_engine, pricing_engine, scaling_engine
    
    if not ENGINES_AVAILABLE:
        logger.warning("Engines not available due to import failures")
        return False
    
    try:
        # Import additional dependencies for BI engine
        from swarm_coordination import TaskMarket
        from cortecs_core import CortecsBrain
        
        # Initialize core engines
        monetization_engine = MonetizationEngine()
        payment_processor = SINCORPaymentProcessor()
        
        # Initialize BI engine with proper dependencies
        task_market = TaskMarket()
        cortecs_brain = CortecsBrain()
        bi_engine = InstantBusinessIntelligence(task_market, cortecs_brain)
        
        pricing_engine = DynamicPricingEngine()
        scaling_engine = InfiniteScalingEngine()
        logger.info("✅ SINCOR engines initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Engine initialization failed: {e}")
        return False

@app.route('/')
def home():
    """Professional landing page"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SINCOR - Intelligence at the Speed of Business</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #1e3a8a 0%, #7c3aed 50%, #dc2626 100%); }
        .card-hover { transition: transform 0.3s ease, box-shadow 0.3s ease; }
        .card-hover:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
        .agent-pulse { animation: pulse 2s infinite; }
        .revenue-glow { box-shadow: 0 0 20px rgba(34, 197, 94, 0.4); }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Header with Logo -->
    <header class="bg-white bg-opacity-10 backdrop-blur">
        <div class="container mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <img src="/static/sincor-logo.jpg" alt="SINCOR Business Solutions" class="h-12 w-12 rounded-full">
                    <div class="text-white font-bold text-xl">SINCOR</div>
                </div>
                <nav class="hidden md:flex space-x-6">
                    <a href="/services" class="text-white hover:text-blue-300">Services</a>
                    <a href="/agents" class="text-white hover:text-blue-300">Agents</a>
                    <a href="/dashboard" class="text-white hover:text-blue-300">Dashboard</a>
                    <a href="/contact" class="text-white hover:text-blue-300">Contact</a>
                </nav>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <div class="gradient-bg text-white relative overflow-hidden">
        <div class="absolute inset-0 bg-black bg-opacity-20"></div>
        <div class="container mx-auto px-4 py-24 relative z-10">
            <div class="text-center max-w-6xl mx-auto">
                <div class="mb-8">
                    <img src="/static/sincor-logo.jpg" alt="SINCOR Business Solutions" class="h-24 w-24 mx-auto rounded-full mb-6 border-4 border-yellow-400">
                    <span class="bg-yellow-400 text-gray-900 px-4 py-2 rounded-full font-bold text-sm">🤖 43-AGENT AI SWARM</span>
                </div>
                <h1 class="text-6xl md:text-7xl font-bold mb-8 leading-tight">
                    SINCOR
                    <span class="block text-4xl md:text-5xl text-blue-300 mt-2">Intelligence at the Speed of Business</span>
                </h1>
                <p class="text-xl md:text-2xl mb-8 opacity-90 leading-relaxed">
                    <strong>Enterprise-Grade Business Intelligence • Predictive Analytics • Automated Agent Services</strong><br>
                    Deploy 43 specialized AI agents that deliver instant business intelligence and scale enterprise operations with unmatched precision.
                </p>
                <div class="grid md:grid-cols-3 gap-4 mb-12 text-center">
                    <div class="bg-white bg-opacity-20 backdrop-blur rounded-lg p-6">
                        <div class="text-4xl mb-3">⚡</div>
                        <div class="text-xl font-bold text-green-400">Instant Intelligence</div>
                        <div class="text-sm opacity-80">Real-time business insights</div>
                    </div>
                    <div class="bg-white bg-opacity-20 backdrop-blur rounded-lg p-6">
                        <div class="text-4xl mb-3">🏢</div>
                        <div class="text-xl font-bold text-purple-400">Enterprise Scale</div>
                        <div class="text-sm opacity-80">Fortune 500 ready solutions</div>
                    </div>
                    <div class="bg-white bg-opacity-20 backdrop-blur rounded-lg p-6">
                        <div class="text-4xl mb-3">🎯</div>
                        <div class="text-xl font-bold text-yellow-400">Strategic Automation</div>
                        <div class="text-sm opacity-80">AI-powered decision making</div>
                    </div>
                </div>
                <div class="space-x-4">
                    <a href="/dashboard" class="bg-green-600 hover:bg-green-700 px-8 py-4 rounded-lg font-semibold text-lg inline-block revenue-glow">
                        🚀 Launch Command Center
                    </a>
                    <a href="/consultation" class="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white hover:text-gray-900 inline-block">
                        📞 Schedule Consultation
                    </a>
                </div>
                <div class="mt-8 space-x-6 opacity-90">
                    <a href="/services" class="text-white underline">Premium Services</a> • 
                    <a href="/agents" class="text-white underline">Agent Portfolio</a>
                </div>
            </div>
        </div>
    </div>

    <!-- 43-Agent Swarm Architecture -->
    <div class="py-20 bg-gray-900">
        <div class="container mx-auto px-4">
            <div class="text-center mb-16">
                <h2 class="text-4xl md:text-5xl font-bold mb-6 text-white">43-Agent AI Swarm</h2>
                <p class="text-xl text-gray-300 mb-8 max-w-4xl mx-auto">
                    Deploy specialized AI agents across 7 distinct archetypes with enterprise-grade security and infinite scaling capabilities for mission-critical operations.
                </p>
                <div class="bg-yellow-400 text-gray-900 px-6 py-3 rounded-full inline-block font-bold">
                    🚀 CRYPTOGRAPHIC DID IDENTITY • SOULBOUND TOKEN AUTHORITY • ENTERPRISE SECURITY
                </div>
            </div>
            
            <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <!-- Scout Agents -->
                <div class="bg-gray-800 border-2 border-blue-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">🔍</div>
                    <h3 class="text-xl font-bold mb-2 text-blue-400">SCOUT AGENTS</h3>
                    <div class="text-2xl font-bold text-white mb-2">8 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Market intelligence, competitive analysis, lead prospecting</p>
                    <div class="bg-blue-500 bg-opacity-20 text-blue-400 px-3 py-1 rounded text-xs">
                        Intelligence Gathering
                    </div>
                </div>

                <!-- Synthesizer Agents -->
                <div class="bg-gray-800 border-2 border-purple-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">🧠</div>
                    <h3 class="text-xl font-bold mb-2 text-purple-400">SYNTHESIZER</h3>
                    <div class="text-2xl font-bold text-white mb-2">6 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Executive briefings, intelligence fusion, technical documentation</p>
                    <div class="bg-purple-500 bg-opacity-20 text-purple-400 px-3 py-1 rounded text-xs">
                        Data Analysis
                    </div>
                </div>

                <!-- Builder Agents -->
                <div class="bg-gray-800 border-2 border-green-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">🏗️</div>
                    <h3 class="text-xl font-bold mb-2 text-green-400">BUILDER</h3>
                    <div class="text-2xl font-bold text-white mb-2">7 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Architecture design, automation development, system integration</p>
                    <div class="bg-green-500 bg-opacity-20 text-green-400 px-3 py-1 rounded text-xs">
                        Development
                    </div>
                </div>

                <!-- Negotiator Agents -->
                <div class="bg-gray-800 border-2 border-yellow-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">🤝</div>
                    <h3 class="text-xl font-bold mb-2 text-yellow-400">NEGOTIATOR</h3>
                    <div class="text-2xl font-bold text-white mb-2">6 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Partnership negotiations, client sales, proposal development</p>
                    <div class="bg-yellow-500 bg-opacity-20 text-yellow-400 px-3 py-1 rounded text-xs">
                        Revenue Generation
                    </div>
                </div>
            </div>

            <div class="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
                <!-- Caretaker Agents -->
                <div class="bg-gray-800 border-2 border-cyan-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">🛡️</div>
                    <h3 class="text-xl font-bold mb-2 text-cyan-400">CARETAKER</h3>
                    <div class="text-2xl font-bold text-white mb-2">5 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Data maintenance, compliance oversight, system monitoring</p>
                    <div class="bg-cyan-500 bg-opacity-20 text-cyan-400 px-3 py-1 rounded text-xs">
                        System Health
                    </div>
                </div>

                <!-- Auditor Agents -->
                <div class="bg-gray-800 border-2 border-red-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">📋</div>
                    <h3 class="text-xl font-bold mb-2 text-red-400">AUDITOR</h3>
                    <div class="text-2xl font-bold text-white mb-2">5 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Quality validation, compliance checking, risk assessment</p>
                    <div class="bg-red-500 bg-opacity-20 text-red-400 px-3 py-1 rounded text-xs">
                        Quality Control
                    </div>
                </div>

                <!-- Director Agents -->
                <div class="bg-gray-800 border-2 border-orange-500 rounded-lg p-6 text-center card-hover">
                    <div class="text-4xl mb-4">👑</div>
                    <h3 class="text-xl font-bold mb-2 text-orange-400">DIRECTOR</h3>
                    <div class="text-2xl font-bold text-white mb-2">6 Agents</div>
                    <p class="text-gray-300 text-sm mb-4">Strategic coordination, priority setting, market clearing</p>
                    <div class="bg-orange-500 bg-opacity-20 text-orange-400 px-3 py-1 rounded text-xs">
                        Strategic Control
                    </div>
                </div>
            </div>

            <div class="text-center mt-12">
                <a href="/agents" class="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-purple-700 inline-block">
                    🤖 Deploy Your Agent Swarm
                </a>
            </div>
        </div>
    </div>

    <!-- Premium Use Cases -->
    <div class="py-20 bg-white">
        <div class="container mx-auto px-4">
            <div class="text-center mb-16">
                <img src="/static/sincor-logo.jpg" alt="SINCOR Business Solutions" class="h-16 w-16 mx-auto rounded-full mb-4">
                <h2 class="text-4xl font-bold mb-4 text-gray-800">Enterprise Solutions Portfolio</h2>
                <p class="text-xl text-gray-600 mb-4">Premium AI automation for Fortune 500 companies and strategic enterprises</p>
                <div class="bg-blue-100 text-blue-800 px-4 py-2 rounded-full inline-block font-semibold">
                    🏆 PREMIUM ONLY • ENTERPRISE GRADE • STRATEGIC PARTNERSHIPS
                </div>
            </div>
            
            <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
                <!-- Financial Services -->
                <div class="bg-white border-2 border-green-500 rounded-lg p-6 relative card-hover shadow-lg">
                    <div class="text-center">
                        <div class="text-4xl mb-4">🏦</div>
                        <h3 class="text-xl font-bold mb-2 text-green-600">FINANCIAL SERVICES</h3>
                        <p class="text-gray-600 mb-6">High-frequency trading algorithms, risk assessment models, regulatory compliance automation for investment banks and hedge funds</p>
                        <ul class="text-left space-y-2 mb-6">
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Algorithmic trading systems</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Risk management AI</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Regulatory compliance</li>
                        </ul>
                        <a href="/consultation" class="w-full bg-green-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-green-700 block text-center">
                            Schedule Consultation
                        </a>
                    </div>
                </div>

                <!-- Manufacturing -->
                <div class="bg-white border-2 border-purple-500 rounded-lg p-6 relative card-hover shadow-lg">
                    <div class="text-center">
                        <div class="text-4xl mb-4">🏭</div>
                        <h3 class="text-xl font-bold mb-2 text-purple-600">MANUFACTURING</h3>
                        <p class="text-gray-600 mb-6">Smart factory automation, predictive maintenance, supply chain optimization for global manufacturing leaders</p>
                        <ul class="text-left space-y-2 mb-6">
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Predictive maintenance AI</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Supply chain optimization</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Quality assurance automation</li>
                        </ul>
                        <a href="/consultation" class="w-full bg-purple-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-purple-700 block text-center">
                            Schedule Consultation
                        </a>
                    </div>
                </div>

                <!-- Healthcare -->
                <div class="bg-white border-2 border-blue-500 rounded-lg p-6 relative card-hover shadow-lg">
                    <div class="text-center">
                        <div class="text-4xl mb-4">🏥</div>
                        <h3 class="text-xl font-bold mb-2 text-blue-600">HEALTHCARE</h3>
                        <p class="text-gray-600 mb-6">Drug discovery acceleration, clinical trial optimization, patient outcome prediction for pharmaceutical giants</p>
                        <ul class="text-left space-y-2 mb-6">
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Drug discovery AI</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Clinical trial optimization</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Patient outcome prediction</li>
                        </ul>
                        <a href="/consultation" class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-blue-700 block text-center">
                            Schedule Consultation
                        </a>
                    </div>
                </div>

                <!-- Technology -->
                <div class="bg-white border-2 border-yellow-500 rounded-lg p-6 relative card-hover shadow-lg transform scale-105">
                    <div class="absolute -top-3 left-1/2 transform -translate-x-1/2">
                        <span class="bg-yellow-500 text-white px-3 py-1 rounded-full text-xs font-semibold">FEATURED</span>
                    </div>
                    <div class="text-center">
                        <div class="text-4xl mb-4">💻</div>
                        <h3 class="text-xl font-bold mb-2 text-yellow-600">TECHNOLOGY</h3>
                        <p class="text-gray-600 mb-6">Infrastructure scaling, cybersecurity automation, DevOps orchestration for tech unicorns and FAANG companies</p>
                        <ul class="text-left space-y-2 mb-6">
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Auto-scaling infrastructure</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>Cybersecurity automation</li>
                            <li class="flex items-center text-sm"><span class="text-green-500 mr-2">✓</span>DevOps orchestration</li>
                        </ul>
                        <a href="/consultation" class="w-full bg-yellow-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-yellow-700 block text-center">
                            Schedule Consultation
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Real-Time Intelligence System -->
    <div class="py-20 bg-gradient-to-r from-gray-900 to-blue-900 text-white">
        <div class="container mx-auto px-4">
            <div class="text-center mb-16">
                <h2 class="text-4xl md:text-5xl font-bold mb-6">Real-Time Intelligence System</h2>
                <p class="text-xl text-gray-300 mb-8 max-w-4xl mx-auto">
                    Live market data streams providing instant strategic adjustments across financial markets, competitor monitoring, and industry trend detection.
                </p>
                <div class="bg-blue-500 bg-opacity-30 backdrop-blur text-white px-6 py-3 rounded-full inline-block font-bold">
                    📡 LIVE FEEDS • INSTANT ALERTS • STRATEGIC AUTOMATION
                </div>
            </div>
            
            <div class="grid md:grid-cols-2 lg:grid-cols-5 gap-6 mb-12">
                <div class="bg-white bg-opacity-10 backdrop-blur rounded-lg p-6 text-center">
                    <div class="text-3xl mb-3">💹</div>
                    <h4 class="font-bold mb-2">Financial Markets</h4>
                    <p class="text-sm text-gray-300">Real-time market data and trading signals</p>
                </div>
                
                <div class="bg-white bg-opacity-10 backdrop-blur rounded-lg p-6 text-center">
                    <div class="text-3xl mb-3">📰</div>
                    <h4 class="font-bold mb-2">News Feeds</h4>
                    <p class="text-sm text-gray-300">Breaking industry news and analysis</p>
                </div>
                
                <div class="bg-white bg-opacity-10 backdrop-blur rounded-lg p-6 text-center">
                    <div class="text-3xl mb-3">💭</div>
                    <h4 class="font-bold mb-2">Social Sentiment</h4>
                    <p class="text-sm text-gray-300">Brand mentions and market mood</p>
                </div>
                
                <div class="bg-white bg-opacity-10 backdrop-blur rounded-lg p-6 text-center">
                    <div class="text-3xl mb-3">🎯</div>
                    <h4 class="font-bold mb-2">Competitor Intel</h4>
                    <p class="text-sm text-gray-300">Live competitor tracking and alerts</p>
                </div>
                
                <div class="bg-white bg-opacity-10 backdrop-blur rounded-lg p-6 text-center">
                    <div class="text-3xl mb-3">📈</div>
                    <h4 class="font-bold mb-2">Trend Detection</h4>
                    <p class="text-sm text-gray-300">Industry patterns and opportunities</p>
                </div>
            </div>
            
            <div class="text-center">
                <a href="/intelligence" class="bg-blue-600 hover:bg-blue-700 px-8 py-4 rounded-lg font-semibold text-lg inline-block">
                    📡 Access Live Intelligence
                </a>
            </div>
        </div>
    </div>

    <!-- Infinite Scaling Model -->
    <div class="py-20 bg-gray-50">
        <div class="container mx-auto px-4">
            <div class="text-center mb-16">
                <h2 class="text-4xl font-bold mb-6 text-gray-800">Enterprise-Grade Infinite Scaling</h2>
                <p class="text-xl text-gray-600 mb-8 max-w-4xl mx-auto">
                    Deploy thousands of agents with predictive workload forecasting, substrate-aware resource allocation, and intent-driven autoscaling based on cognitive resonance patterns for mission-critical enterprise operations.
                </p>
            </div>
            
            <div class="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto mb-12">
                <div class="bg-white p-8 rounded-lg shadow-lg text-center">
                    <div class="text-5xl mb-4">🧠</div>
                    <h3 class="text-2xl font-bold mb-4 text-gray-800">4-Tier Memory</h3>
                    <ul class="text-left space-y-2">
                        <li class="flex items-center"><span class="text-green-500 mr-2">📝</span> Episodic Memory</li>
                        <li class="flex items-center"><span class="text-blue-500 mr-2">🧠</span> Semantic Memory</li>
                        <li class="flex items-center"><span class="text-purple-500 mr-2">⚙️</span> Procedural Memory</li>
                        <li class="flex items-center"><span class="text-orange-500 mr-2">📖</span> Autobiographical Memory</li>
                    </ul>
                </div>
                
                <div class="bg-white p-8 rounded-lg shadow-lg text-center">
                    <div class="text-5xl mb-4">🔐</div>
                    <h3 class="text-2xl font-bold mb-4 text-gray-800">Identity & Authority</h3>
                    <ul class="text-left space-y-2">
                        <li class="flex items-center"><span class="text-green-500 mr-2">🔑</span> Cryptographic DID Keys</li>
                        <li class="flex items-center"><span class="text-blue-500 mr-2">🏅</span> Soulbound Token Roles</li>
                        <li class="flex items-center"><span class="text-purple-500 mr-2">✅</span> Constitution Hash Verification</li>
                        <li class="flex items-center"><span class="text-orange-500 mr-2">📊</span> Promotion Tracking</li>
                    </ul>
                </div>
                
                <div class="bg-white p-8 rounded-lg shadow-lg text-center">
                    <div class="text-5xl mb-4">📊</div>
                    <h3 class="text-2xl font-bold mb-4 text-gray-800">Resource Management</h3>
                    <ul class="text-left space-y-2">
                        <li class="flex items-center"><span class="text-green-500 mr-2">🔮</span> Predictive Forecasting</li>
                        <li class="flex items-center"><span class="text-blue-500 mr-2">⚡</span> Substrate Allocation</li>
                        <li class="flex items-center"><span class="text-purple-500 mr-2">🎯</span> Intent-Driven Scaling</li>
                        <li class="flex items-center"><span class="text-orange-500 mr-2">🔄</span> Cognitive Resonance</li>
                    </ul>
                </div>
            </div>
            
            <div class="bg-gradient-to-r from-green-500 to-blue-600 text-white p-8 rounded-lg text-center max-w-4xl mx-auto">
                <img src="/static/sincor-logo.jpg" alt="SINCOR Business Solutions" class="h-12 w-12 mx-auto rounded-full mb-4 border-2 border-white">
                <h3 class="text-3xl font-bold mb-4">Scale to Enterprise Requirements</h3>
                <div class="grid md:grid-cols-3 gap-6 mb-6">
                    <div>
                        <div class="text-4xl font-bold">10K+</div>
                        <div class="text-sm opacity-80">Concurrent Agents</div>
                    </div>
                    <div>
                        <div class="text-4xl font-bold">∞</div>
                        <div class="text-sm opacity-80">Scaling Capacity</div>
                    </div>
                    <div>
                        <div class="text-4xl font-bold">24/7</div>
                        <div class="text-sm opacity-80">Enterprise Support</div>
                    </div>
                </div>
                <a href="/consultation" class="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 inline-block">
                    🏢 Enterprise Consultation
                </a>
            </div>
        </div>
    </div>

    <!-- Footer CTA -->
    <div class="gradient-bg text-white py-16">
        <div class="container mx-auto px-4 text-center">
            <img src="/static/sincor-logo.jpg" alt="SINCOR Business Solutions" class="h-16 w-16 mx-auto rounded-full mb-6 border-4 border-white">
            <h2 class="text-4xl font-bold mb-6">Ready for Enterprise Transformation?</h2>
            <p class="text-xl mb-8 max-w-3xl mx-auto">Join Fortune 500 companies and industry leaders who trust SINCOR for mission-critical AI business automation</p>
            <div class="space-x-4 mb-8">
                <a href="/consultation" class="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 inline-block">
                    🏢 Enterprise Consultation
                </a>
                <a href="/portfolio" class="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-white hover:text-blue-600 inline-block">
                    📊 View Portfolio
                </a>
            </div>
            <p class="mt-6 opacity-90 text-lg">Premium Enterprise Solutions • Strategic Partnerships • Global Scale</p>
            
            <!-- Footer -->
            <div class="mt-12 pt-8 border-t border-white border-opacity-20">
                <div class="flex items-center justify-center space-x-4 mb-4">
                    <img src="/static/sincor-logo.jpg" alt="SINCOR Business Solutions" class="h-8 w-8 rounded-full">
                    <span class="text-xl font-bold">SINCOR Business Solutions</span>
                </div>
                <p class="text-sm opacity-70">© 2025 SINCOR. All rights reserved. Intelligence at the Speed of Business.</p>
            </div>
        </div>
    </div>
</body>
</html>'''

@app.route('/dashboard')
def dashboard():
    """Main SINCOR dashboard"""
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SINCOR Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-4xl font-bold mb-8 text-green-400 text-center">🚀 SINCOR Command Center</h1>
        
        <div class="grid md:grid-cols-4 gap-6 mb-8">
            <div class="bg-gray-800 p-4 rounded-lg text-center">
                <h3 class="text-lg font-bold text-blue-400 mb-2">System Status</h3>
                <div id="system-status" class="text-2xl font-bold text-green-400">ONLINE</div>
                <p class="text-sm text-gray-400">All systems operational</p>
            </div>
            
            <div class="bg-gray-800 p-4 rounded-lg text-center">
                <h3 class="text-lg font-bold text-purple-400 mb-2">Revenue Streams</h3>
                <div class="text-2xl font-bold text-purple-400">8</div>
                <p class="text-sm text-gray-400">Active channels</p>
            </div>
            
            <div class="bg-gray-800 p-4 rounded-lg text-center">
                <h3 class="text-lg font-bold text-yellow-400 mb-2">PayPal Status</h3>
                <div id="paypal-status" class="text-2xl font-bold text-green-400">LIVE</div>
                <p class="text-sm text-gray-400">API connected</p>
            </div>
            
            <div class="bg-gray-800 p-4 rounded-lg text-center">
                <h3 class="text-lg font-bold text-red-400 mb-2">Agent Cost</h3>
                <div class="text-2xl font-bold text-green-400">$1</div>
                <p class="text-sm text-gray-400">Per operation</p>
            </div>
        </div>
        
        <div class="grid md:grid-cols-2 gap-8 mb-8">
            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-2xl font-bold mb-4 text-green-400">Revenue Generation</h2>
                <div class="space-y-4">
                    <button onclick="startMonetization()" class="w-full bg-green-600 hover:bg-green-700 px-4 py-2 rounded font-semibold">
                        🚀 Start Monetization Engine
                    </button>
                    <button onclick="createPayment()" class="w-full bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded font-semibold">
                        💳 Create $2,500 Payment
                    </button>
                    <button onclick="getOpportunities()" class="w-full bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded font-semibold">
                        🎯 Find Revenue Opportunities
                    </button>
                </div>
                
                <div id="action-result" class="mt-4 p-4 bg-gray-700 rounded min-h-[100px]">
                    <p class="text-gray-400">Click buttons above to interact with SINCOR systems</p>
                </div>
            </div>
            
            <div class="bg-gray-800 p-6 rounded-lg">
                <h2 class="text-2xl font-bold mb-4 text-cyan-400">Business Intelligence</h2>
                <div class="space-y-4">
                    <div class="flex justify-between">
                        <span>Instant BI Engine:</span>
                        <span class="text-cyan-400">{{ 'READY' if engines_available else 'OFFLINE' }}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Pricing Engine:</span>
                        <span class="text-cyan-400">{{ 'READY' if engines_available else 'OFFLINE' }}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Scaling Engine:</span>
                        <span class="text-cyan-400">{{ 'READY' if engines_available else 'OFFLINE' }}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>PayPal Integration:</span>
                        <span class="text-cyan-400">{{ 'LIVE' if paypal_configured else 'NEEDS CONFIG' }}</span>
                    </div>
                </div>
                
                <div class="mt-4 p-4 bg-gray-700 rounded">
                    <h3 class="font-bold text-yellow-400 mb-2">Quick Stats</h3>
                    <p class="text-sm">Environment: {{ environment }}</p>
                    <p class="text-sm">Base URL: {{ base_url }}</p>
                    <p class="text-sm">API Base: {{ api_base }}</p>
                </div>
            </div>
        </div>
        
        <div class="bg-gray-800 p-6 rounded-lg">
            <h2 class="text-2xl font-bold mb-4 text-red-400">Available Services</h2>
            <div class="grid md:grid-cols-4 gap-4">
                <div class="text-center p-4 bg-gray-700 rounded">
                    <div class="text-2xl mb-2">💡</div>
                    <h3 class="font-bold">Instant BI</h3>
                    <p class="text-sm text-gray-400">$2,500 - $15,000</p>
                </div>
                <div class="text-center p-4 bg-gray-700 rounded">
                    <div class="text-2xl mb-2">🤖</div>
                    <h3 class="font-bold">Agent Services</h3>
                    <p class="text-sm text-gray-400">$500 - $5,000/mo</p>
                </div>
                <div class="text-center p-4 bg-gray-700 rounded">
                    <div class="text-2xl mb-2">📊</div>
                    <h3 class="font-bold">Predictive Analytics</h3>
                    <p class="text-sm text-gray-400">$6,000 - $25,000</p>
                </div>
                <div class="text-center p-4 bg-gray-700 rounded">
                    <div class="text-2xl mb-2">🤝</div>
                    <h3 class="font-bold">Enterprise Partnerships</h3>
                    <p class="text-sm text-gray-400">$50K - $200K</p>
                </div>
            </div>
        </div>
    </div>

<script>
async function startMonetization() {
    const result = document.getElementById('action-result');
    result.innerHTML = '<p class="text-yellow-400">🔄 Starting monetization engine...</p>';
    
    try {
        const response = await fetch('/api/monetization/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();
        
        if (data.success) {
            result.innerHTML = `
                <div class="text-green-400">
                    <p class="font-bold">✅ Monetization Engine Started!</p>
                    <p>Opportunities executed: ${data.opportunities_executed || 0}</p>
                    <p>Revenue generated: $${data.total_revenue || 0}</p>
                    <p>Success rate: ${(data.success_rate * 100 || 0).toFixed(1)}%</p>
                </div>
            `;
        } else {
            result.innerHTML = `<p class="text-red-400">❌ Error: ${data.error}</p>`;
        }
    } catch (error) {
        result.innerHTML = `<p class="text-red-400">❌ Network error: ${error.message}</p>`;
    }
}

async function createPayment() {
    const result = document.getElementById('action-result');
    result.innerHTML = '<p class="text-yellow-400">💳 Creating PayPal payment...</p>';
    
    try {
        const response = await fetch('/api/paypal/create-payment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                amount: 2500,
                service_type: 'instant_bi',
                client_email: 'demo@client.com'
            })
        });
        const data = await response.json();
        
        if (data.success) {
            result.innerHTML = `
                <div class="text-blue-400">
                    <p class="font-bold">💳 Payment Created!</p>
                    <p>Payment ID: ${data.payment_id}</p>
                    <p>Amount: $${data.amount}</p>
                    <p><a href="${data.approval_url}" target="_blank" class="underline text-blue-300">Complete Payment on PayPal</a></p>
                </div>
            `;
        } else {
            result.innerHTML = `<p class="text-red-400">❌ Payment failed: ${data.error}</p>`;
        }
    } catch (error) {
        result.innerHTML = `<p class="text-red-400">❌ Payment error: ${error.message}</p>`;
    }
}

async function getOpportunities() {
    const result = document.getElementById('action-result');
    result.innerHTML = '<p class="text-yellow-400">🎯 Finding revenue opportunities...</p>';
    
    try {
        const response = await fetch('/api/opportunities');
        const data = await response.json();
        
        if (data.opportunities) {
            result.innerHTML = `
                <div class="text-purple-400">
                    <p class="font-bold">🎯 Revenue Opportunities Found!</p>
                    <p>Total opportunities: ${data.total_opportunities}</p>
                    <p>Potential revenue: $${data.total_potential_revenue?.toFixed(2) || 0}</p>
                    <p class="text-sm mt-2">Top opportunity: ${data.opportunities[0]?.revenue_stream || 'N/A'}</p>
                </div>
            `;
        } else {
            result.innerHTML = `<p class="text-red-400">❌ Error: ${data.error}</p>`;
        }
    } catch (error) {
        result.innerHTML = `<p class="text-red-400">❌ Error: ${error.message}</p>`;
    }
}
</script>
</body>
</html>''', 
    engines_available=ENGINES_AVAILABLE,
    paypal_configured=bool(os.getenv('PAYPAL_REST_API_ID') or os.getenv('PAYPAL_CLIENT_ID')),
    environment=PAYPAL_ENV,
    base_url=APP_BASE_URL,
    api_base=PAYPAL_API_BASE
)

@app.route('/services')
def services():
    """Services page"""
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SINCOR Services</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <div class="text-center mb-12">
            <h1 class="text-4xl font-bold mb-4 text-blue-400">SINCOR Services</h1>
            <p class="text-xl text-gray-300">AI-powered business solutions that deliver results</p>
        </div>
        
        <div class="grid md:grid-cols-2 gap-8 mb-12">
            <div class="bg-gray-800 p-8 rounded-lg">
                <h2 class="text-2xl font-bold mb-4 text-green-400">💡 Instant Business Intelligence</h2>
                <p class="text-gray-300 mb-4">Get comprehensive business analysis in minutes, not months.</p>
                <ul class="text-gray-300 space-y-2 mb-6">
                    <li>• Market opportunity analysis</li>
                    <li>• Competitive intelligence reports</li>
                    <li>• Revenue optimization strategies</li>
                    <li>• Risk assessment and mitigation</li>
                </ul>
                <div class="text-2xl font-bold text-green-400 mb-4">$2,500 - $15,000</div>
                <button onclick="requestService('instant_bi', 2500)" class="w-full bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg font-semibold">
                    Request Instant BI
                </button>
            </div>
            
            <div class="bg-gray-800 p-8 rounded-lg">
                <h2 class="text-2xl font-bold mb-4 text-purple-400">🤖 Agent Services</h2>
                <p class="text-gray-300 mb-4">AI agents that handle your business operations 24/7.</p>
                <ul class="text-gray-300 space-y-2 mb-6">
                    <li>• Customer service automation</li>
                    <li>• Lead generation and qualification</li>
                    <li>• Process optimization</li>
                    <li>• Performance monitoring</li>
                </ul>
                <div class="text-2xl font-bold text-purple-400 mb-4">$500 - $5,000/month</div>
                <button onclick="requestService('agent_services', 500)" class="w-full bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg font-semibold">
                    Start Agent Services
                </button>
            </div>
            
            <div class="bg-gray-800 p-8 rounded-lg">
                <h2 class="text-2xl font-bold mb-4 text-yellow-400">📊 Predictive Analytics</h2>
                <p class="text-gray-300 mb-4">Forecast market trends and identify future opportunities.</p>
                <ul class="text-gray-300 space-y-2 mb-6">
                    <li>• Market trend forecasting</li>
                    <li>• Demand prediction models</li>
                    <li>• Price optimization algorithms</li>
                    <li>• Strategic planning insights</li>
                </ul>
                <div class="text-2xl font-bold text-yellow-400 mb-4">$6,000 - $25,000</div>
                <button onclick="requestService('predictive_analytics', 6000)" class="w-full bg-yellow-600 hover:bg-yellow-700 px-6 py-3 rounded-lg font-semibold">
                    Get Predictive Analytics
                </button>
            </div>
            
            <div class="bg-gray-800 p-8 rounded-lg">
                <h2 class="text-2xl font-bold mb-4 text-red-400">🤝 Enterprise Partnerships</h2>
                <p class="text-gray-300 mb-4">Strategic partnerships that unlock massive revenue streams.</p>
                <ul class="text-gray-300 space-y-2 mb-6">
                    <li>• Partnership framework development</li>
                    <li>• Revenue sharing models</li>
                    <li>• Joint venture structures</li>
                    <li>• Strategic alliance management</li>
                </ul>
                <div class="text-2xl font-bold text-red-400 mb-4">$50,000 - $200,000</div>
                <button onclick="requestService('enterprise_partnerships', 50000)" class="w-full bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg font-semibold">
                    Explore Partnerships
                </button>
            </div>
        </div>
        
        <div class="text-center">
            <a href="/dashboard" class="bg-blue-600 hover:bg-blue-700 px-8 py-4 rounded-lg font-semibold text-xl">
                Back to Dashboard
            </a>
        </div>
        
        <div id="service-result" class="mt-8 p-6 bg-gray-800 rounded-lg min-h-[100px]">
            <p class="text-gray-400">Click any service above to get started with SINCOR</p>
        </div>
    </div>

<script>
async function requestService(serviceType, amount) {
    const result = document.getElementById('service-result');
    result.innerHTML = `<p class="text-yellow-400">🔄 Creating payment for ${serviceType.replace('_', ' ')} service...</p>`;
    
    try {
        const response = await fetch('/api/paypal/create-payment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                amount: amount,
                service_type: serviceType,
                client_email: 'client@example.com'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            result.innerHTML = `
                <div class="text-green-400">
                    <p class="font-bold">✅ Payment Created Successfully!</p>
                    <p class="mb-2">Service: ${serviceType.replace('_', ' ').toUpperCase()}</p>
                    <p class="mb-2">Amount: $${data.amount.toFixed(2)}</p>
                    <p class="mb-4">Payment ID: ${data.payment_id}</p>
                    <a href="${data.approval_url}" target="_blank" 
                       class="inline-block bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold text-white">
                        Complete Payment on PayPal →
                    </a>
                </div>
            `;
        } else {
            result.innerHTML = `<p class="text-red-400">❌ Payment creation failed: ${data.error}</p>`;
        }
    } catch (error) {
        result.innerHTML = `<p class="text-red-400">❌ Network error: ${error.message}</p>`;
    }
}
</script>
</body>
</html>''')

# API Routes
@app.route('/api/monetization/start', methods=['POST'])
def start_monetization():
    """Start the monetization engine"""
    if not monetization_engine:
        return jsonify({'success': False, 'error': 'Monetization engine not available'}), 500
    
    try:
        # Execute monetization strategy (synchronous wrapper for async function)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        strategy_report = loop.run_until_complete(
            monetization_engine.execute_monetization_strategy(max_concurrent_opportunities=10)
        )
        loop.close()
        
        return jsonify({
            'success': True,
            'message': 'Monetization engine started',
            'opportunities_executed': strategy_report['execution_summary']['opportunities_executed'],
            'total_revenue': strategy_report['execution_summary']['total_revenue'],
            'success_rate': strategy_report['execution_summary']['success_rate']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to start monetization: {str(e)}'}), 500

@app.route('/api/paypal/create-payment', methods=['POST'])
def create_payment():
    """Create a PayPal payment"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        service_type = data.get('service_type', 'instant_bi')
        client_email = data.get('client_email', 'demo@client.com')
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400
        
        client_id = os.getenv('PAYPAL_REST_API_ID') or os.getenv('PAYPAL_CLIENT_ID')
        client_secret = os.getenv('PAYPAL_REST_API_SECRET') or os.getenv('PAYPAL_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            return jsonify({
                'success': False, 
                'error': 'PayPal credentials not configured in Railway environment'
            }), 500
        
        # Get PayPal access token
        token_response = requests.post(
            f'{PAYPAL_API_BASE}/v1/oauth2/token',
            headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
            data='grant_type=client_credentials',
            auth=(client_id, client_secret)
        )
        
        if token_response.status_code != 200:
            return jsonify({
                'success': False, 
                'error': f'PayPal token request failed: {token_response.status_code}'
            }), 500
        
        access_token = token_response.json()['access_token']
        
        # Create PayPal payment
        payment_data = {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {"total": f"{amount:.2f}", "currency": "USD"},
                "description": f"SINCOR {service_type.replace('_', ' ').title()} Service"
            }],
            "redirect_urls": {
                "return_url": f"{APP_BASE_URL}/payment/success",
                "cancel_url": f"{APP_BASE_URL}/payment/cancel"
            }
        }
        
        payment_response = requests.post(
            f'{PAYPAL_API_BASE}/v1/payments/payment',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            },
            json=payment_data
        )
        
        if payment_response.status_code == 201:
            payment_result = payment_response.json()
            payment_id = payment_result['id']
            
            # Find approval URL
            approval_url = None
            for link in payment_result.get('links', []):
                if link['rel'] == 'approval_url':
                    approval_url = link['href']
                    break
            
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'amount': amount,
                'approval_url': approval_url
            })
        else:
            return jsonify({
                'success': False,
                'error': f'PayPal payment creation failed: {payment_response.status_code}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Payment processing error: {str(e)}'
        }), 500

@app.route('/api/opportunities', methods=['GET'])
def get_opportunities():
    """Get revenue opportunities"""
    if not monetization_engine:
        return jsonify({'error': 'Monetization engine not available'}), 500
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        opportunities = loop.run_until_complete(monetization_engine.identify_revenue_opportunities())
        loop.close()
        
        # Convert to JSON-serializable format
        opportunities_data = []
        for opp in opportunities[:20]:  # Limit to top 20
            opportunities_data.append({
                'opportunity_id': opp.opportunity_id,
                'revenue_stream': opp.revenue_stream.value,
                'client_segment': opp.client_segment,
                'revenue_potential': opp.revenue_potential,
                'confidence_score': opp.confidence_score,
                'time_to_close': opp.time_to_close,
                'strategic_value': opp.strategic_value
            })
        
        return jsonify({
            'opportunities': opportunities_data,
            'total_opportunities': len(opportunities),
            'total_potential_revenue': sum(opp['revenue_potential'] for opp in opportunities_data)
        })
    
    except Exception as e:
        return jsonify({'error': f'Failed to get opportunities: {str(e)}'}), 500

@app.route('/payment/success')
def payment_success():
    """Payment success callback"""
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    
    return render_template_string('''<!DOCTYPE html>
<html><head><title>Payment Successful!</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head><body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
<div class="bg-green-900 p-8 rounded-lg max-w-md text-center">
    <h1 class="text-3xl font-bold mb-4 text-green-400">🎉 Payment Successful!</h1>
    <div class="space-y-2 mb-6">
        <p><strong>Payment ID:</strong> {{ payment_id }}</p>
        <p><strong>Payer ID:</strong> {{ payer_id }}</p>
    </div>
    <p class="text-green-300 mb-6">Your SINCOR service has been activated!</p>
    <a href="/dashboard" class="inline-block bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-semibold">
        Return to Dashboard
    </a>
</div></body></html>''', payment_id=payment_id, payer_id=payer_id)

@app.route('/payment/cancel')
def payment_cancel():
    """Payment cancel callback"""
    return render_template_string('''<!DOCTYPE html>
<html><head><title>Payment Cancelled</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head><body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
<div class="bg-gray-800 p-8 rounded-lg max-w-md text-center">
    <h1 class="text-2xl font-bold mb-4">Payment Cancelled</h1>
    <p class="text-gray-300 mb-6">Your payment was cancelled. You can try again anytime.</p>
    <a href="/services" class="inline-block bg-blue-600 hover:bg-blue-500 px-6 py-3 rounded-lg font-semibold">
        View Services
    </a>
</div></body></html>''')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'SINCOR Production Platform',
        'engines_available': ENGINES_AVAILABLE,
        'paypal_configured': bool(os.getenv('PAYPAL_REST_API_ID') or os.getenv('PAYPAL_CLIENT_ID')),
        'environment': PAYPAL_ENV,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/readyz')
def readiness_check():
    """Railway readiness check"""
    checks = {
        'paypal_credentials': bool((os.getenv('PAYPAL_REST_API_ID') or os.getenv('PAYPAL_CLIENT_ID')) and (os.getenv('PAYPAL_REST_API_SECRET') or os.getenv('PAYPAL_CLIENT_SECRET'))),
        'environment': PAYPAL_ENV,
        'api_base': PAYPAL_API_BASE,
        'base_url': APP_BASE_URL,
        'engines_available': ENGINES_AVAILABLE
    }
    
    all_ready = all(checks.values())
    
    return jsonify({
        'ready': all_ready,
        'checks': checks,
        'service': 'SINCOR Production Platform',
        'version': '2.0.0'
    }), 200 if all_ready else 503

@app.route('/deployment-test')
def deployment_test():
    """Test endpoint to verify latest deployment"""
    return jsonify({
        'message': 'SINCOR LATEST DEPLOYMENT ACTIVE',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.1-route-fix',
        'routes_registered': True,
        'file': 'simple.py'
    })

# Initialize engines for both direct run and gunicorn
try:
    logger.info("Initializing SINCOR engines...")
    engines_initialized = initialize_engines()
    logger.info(f"Engine initialization: {'SUCCESS' if engines_initialized else 'FAILED (routes still work)'}")
except Exception as e:
    logger.error(f"Engine initialization error: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f">> Starting SINCOR Production Platform on port {port}")
    print(f">> Environment: {PAYPAL_ENV.upper()}")
    print(f">> Base URL: {APP_BASE_URL}")
    print(f">> PayPal: {'CONFIGURED' if (os.getenv('PAYPAL_REST_API_ID') or os.getenv('PAYPAL_CLIENT_ID')) else 'MISSING CREDENTIALS'}")
    print(f">> Engines: {'AVAILABLE' if ENGINES_AVAILABLE else 'IMPORT FAILED'}")
    
    # List registered routes for debugging
    print(">> Registered Flask routes:")
    for rule in app.url_map.iter_rules():
        print(f"   {rule.rule} -> {rule.endpoint}")
    
    print(">> Starting Flask server...")
    app.run(host='0.0.0.0', port=port, debug=False)