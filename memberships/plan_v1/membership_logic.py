#!/usr/bin/env python3
"""
SINCOR $99/mo Membership Logic - SAFE MODE
Handles subscription management, billing, and member benefits
"""
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import uuid

app = Flask(__name__)

# SAFE MODE: Mock database for demo purposes
members_db = {}
subscription_plans = {
    "mediapack_basic": {
        "name": "MediaPack Basic",
        "price": 99.00,
        "currency": "USD",
        "billing_cycle": "monthly",
        "features": [
            "Monthly Google Ads campaigns (up to $200 value)",
            "Weekly social media content (Facebook, Instagram)",
            "Email marketing templates and automation",
            "Google Business Profile optimization",
            "Basic performance reporting"
        ],
        "limits": {
            "ad_spend_included": 0,  # Customer pays ad spend separately
            "social_posts_per_week": 3,
            "email_campaigns_per_month": 2,
            "support_level": "email"
        }
    },
    "mediapack_premium": {
        "name": "MediaPack Premium", 
        "price": 199.00,
        "currency": "USD",
        "billing_cycle": "monthly",
        "features": [
            "Everything in Basic",
            "Daily social media content",
            "Advanced Google Ads management",
            "Landing page creation and optimization",
            "SMS marketing campaigns",
            "Priority phone support",
            "Monthly strategy calls"
        ],
        "limits": {
            "ad_spend_included": 0,
            "social_posts_per_week": 7,
            "email_campaigns_per_month": 4,
            "sms_campaigns_per_month": 2,
            "support_level": "phone"
        }
    }
}

@app.route("/membership/signup", methods=["POST"])
def signup_member():
    """Handle new membership signup - SAFE MODE"""
    data = request.json
    
    # Validate required fields
    required_fields = ["business_name", "contact_email", "phone", "plan_id"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    plan_id = data.get("plan_id")
    if plan_id not in subscription_plans:
        return jsonify({"error": "Invalid plan selected"}), 400
    
    # Create member record
    member_id = str(uuid.uuid4())
    plan = subscription_plans[plan_id]
    
    member_record = {
        "member_id": member_id,
        "business_name": data["business_name"],
        "contact_email": data["contact_email"],
        "phone": data["phone"],
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "monthly_price": plan["price"],
        "signup_date": datetime.utcnow().isoformat(),
        "next_billing_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "status": "trial",  # SAFE MODE: Start with trial
        "payment_method": "pending",
        "features": plan["features"],
        "usage_stats": {
            "social_posts_this_month": 0,
            "email_campaigns_this_month": 0,
            "ad_campaigns_active": 0
        }
    }
    
    # Store in mock database
    members_db[member_id] = member_record
    
    return jsonify({
        "status": "signup_successful",
        "member_id": member_id,
        "plan": plan["name"],
        "monthly_price": plan["price"],
        "trial_period": "7 days",
        "next_billing_date": member_record["next_billing_date"],
        "message": "Welcome to SINCOR! Your 7-day trial has started."
    })

@app.route("/membership/<member_id>/status")
def get_member_status(member_id):
    """Get member account status and usage"""
    if member_id not in members_db:
        return jsonify({"error": "Member not found"}), 404
    
    member = members_db[member_id]
    plan = subscription_plans[member["plan_id"]]
    
    return jsonify({
        "member_info": {
            "business_name": member["business_name"],
            "plan": member["plan_name"],
            "status": member["status"],
            "next_billing": member["next_billing_date"]
        },
        "usage_this_month": member["usage_stats"],
        "plan_limits": plan["limits"],
        "available_features": plan["features"]
    })

@app.route("/membership/<member_id>/usage", methods=["POST"]) 
def update_usage(member_id):
    """Update member usage stats - SAFE MODE"""
    if member_id not in members_db:
        return jsonify({"error": "Member not found"}), 404
    
    data = request.json
    member = members_db[member_id]
    
    # Update usage stats
    if "social_posts" in data:
        member["usage_stats"]["social_posts_this_month"] += data["social_posts"]
    
    if "email_campaigns" in data:
        member["usage_stats"]["email_campaigns_this_month"] += data["email_campaigns"]
    
    if "ad_campaigns" in data:
        member["usage_stats"]["ad_campaigns_active"] = data["ad_campaigns"]
    
    return jsonify({
        "status": "usage_updated",
        "current_usage": member["usage_stats"]
    })

@app.route("/membership/plans")
def get_plans():
    """Get available subscription plans"""
    return jsonify({
        "plans": subscription_plans,
        "pricing_model": "monthly_recurring",
        "trial_period": "7 days",
        "payment_methods": ["credit_card", "paypal", "bank_transfer"]
    })

@app.route("/membership/<member_id>/cancel", methods=["POST"])
def cancel_membership(member_id):
    """Cancel membership - SAFE MODE"""
    if member_id not in members_db:
        return jsonify({"error": "Member not found"}), 404
    
    member = members_db[member_id]
    
    # In SAFE MODE, just mark as cancelled
    member["status"] = "cancelled"
    member["cancellation_date"] = datetime.utcnow().isoformat()
    
    return jsonify({
        "status": "membership_cancelled",
        "message": "Your membership has been cancelled. You'll continue to have access until your next billing date.",
        "access_until": member["next_billing_date"]
    })

@app.route("/membership/revenue")
def revenue_dashboard():
    """Revenue dashboard for membership business - SAFE MODE"""
    
    # Calculate metrics from mock data
    total_members = len(members_db)
    active_members = len([m for m in members_db.values() if m["status"] == "active"])
    trial_members = len([m for m in members_db.values() if m["status"] == "trial"])
    
    monthly_recurring_revenue = sum(
        m["monthly_price"] for m in members_db.values() 
        if m["status"] == "active"
    )
    
    return jsonify({
        "membership_stats": {
            "total_members": total_members,
            "active_paying": active_members,
            "trial_members": trial_members,
            "cancelled_members": total_members - active_members - trial_members
        },
        "revenue_metrics": {
            "monthly_recurring_revenue": monthly_recurring_revenue,
            "average_revenue_per_user": monthly_recurring_revenue / max(active_members, 1),
            "projected_annual_revenue": monthly_recurring_revenue * 12
        },
        "mode": "SAFE_MODE_DEMO"
    })

if __name__ == "__main__":
    print("SINCOR Membership System - SAFE MODE")
    print("$99/mo MediaPack subscriptions")
    print("Demo endpoints:")
    print("- POST /membership/signup")
    print("- GET /membership/<id>/status")
    print("- GET /membership/plans")
    print("- GET /membership/revenue")
    
    app.run(host="0.0.0.0", port=8004, debug=False)