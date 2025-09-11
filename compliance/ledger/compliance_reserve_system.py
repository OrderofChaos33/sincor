#!/usr/bin/env python3
"""
SINCOR Compliance Reserve System - SAFE MODE
Allocates percentage of revenue to compliance reserve fund
"""
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import uuid

app = Flask(__name__)

# SAFE MODE: Mock database for demo purposes
compliance_ledger = []
reserve_settings = {
    "reserve_percentage": 15.0,  # 15% of revenue goes to compliance reserve
    "minimum_reserve": 1000.0,  # Minimum $1000 in reserve
    "maximum_reserve": 25000.0, # Maximum $25000 in reserve
    "auto_allocation": True,
    "created_date": "2025-09-09"
}

revenue_sources = {
    "mediapack_subscriptions": 0.0,
    "template_sales": 0.0,
    "consultation_fees": 0.0,
    "affiliate_commissions": 0.0,
    "other_revenue": 0.0
}

@app.route("/compliance/reserve/status")
def reserve_status():
    """Get current compliance reserve status"""
    
    # Calculate totals from ledger
    total_allocated = sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "allocation")
    total_used = sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "expense")
    current_reserve = total_allocated - total_used
    
    total_revenue = sum(revenue_sources.values())
    target_reserve = total_revenue * (reserve_settings["reserve_percentage"] / 100)
    
    return jsonify({
        "compliance_reserve": {
            "current_balance": current_reserve,
            "target_balance": target_reserve,
            "reserve_percentage": reserve_settings["reserve_percentage"],
            "minimum_threshold": reserve_settings["minimum_reserve"],
            "maximum_cap": reserve_settings["maximum_reserve"]
        },
        "reserve_health": {
            "status": "healthy" if current_reserve >= reserve_settings["minimum_reserve"] else "low",
            "coverage_days": int(current_reserve / 50) if current_reserve > 0 else 0,  # Assuming $50/day compliance costs
            "next_allocation_due": (datetime.utcnow() + timedelta(days=30)).isoformat()
        },
        "revenue_tracking": revenue_sources,
        "mode": "SAFE_MODE_DEMO"
    })

@app.route("/compliance/reserve/allocate", methods=["POST"])
def allocate_to_reserve():
    """Allocate revenue to compliance reserve - SAFE MODE"""
    data = request.json
    
    revenue_source = data.get("source", "other_revenue")
    revenue_amount = data.get("amount", 0.0)
    
    if revenue_amount <= 0:
        return jsonify({"error": "Revenue amount must be positive"}), 400
    
    # Update revenue source
    if revenue_source in revenue_sources:
        revenue_sources[revenue_source] += revenue_amount
    
    # Calculate allocation amount
    allocation_percentage = reserve_settings["reserve_percentage"]
    allocation_amount = revenue_amount * (allocation_percentage / 100)
    
    # Check maximum cap
    current_reserve = sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "allocation") - \
                     sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "expense")
    
    if current_reserve + allocation_amount > reserve_settings["maximum_reserve"]:
        allocation_amount = max(0, reserve_settings["maximum_reserve"] - current_reserve)
    
    # Create ledger entry
    ledger_entry = {
        "entry_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "allocation",
        "amount": allocation_amount,
        "revenue_source": revenue_source,
        "revenue_amount": revenue_amount,
        "percentage": allocation_percentage,
        "description": f"Auto-allocation from {revenue_source}"
    }
    
    compliance_ledger.append(ledger_entry)
    
    return jsonify({
        "status": "allocation_successful",
        "allocated_amount": allocation_amount,
        "revenue_amount": revenue_amount,
        "allocation_percentage": allocation_percentage,
        "new_reserve_balance": current_reserve + allocation_amount,
        "entry_id": ledger_entry["entry_id"]
    })

@app.route("/compliance/reserve/expense", methods=["POST"])
def log_compliance_expense():
    """Log compliance-related expense - SAFE MODE"""
    data = request.json
    
    expense_amount = data.get("amount", 0.0)
    expense_category = data.get("category", "general")
    description = data.get("description", "Compliance expense")
    
    if expense_amount <= 0:
        return jsonify({"error": "Expense amount must be positive"}), 400
    
    # Check available reserve
    current_reserve = sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "allocation") - \
                     sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "expense")
    
    if expense_amount > current_reserve:
        return jsonify({
            "error": "Insufficient compliance reserve funds",
            "available": current_reserve,
            "requested": expense_amount
        }), 400
    
    # Create expense entry
    expense_entry = {
        "entry_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "expense",
        "amount": expense_amount,
        "category": expense_category,
        "description": description,
        "approved_by": "system"
    }
    
    compliance_ledger.append(expense_entry)
    
    return jsonify({
        "status": "expense_logged",
        "expense_amount": expense_amount,
        "category": expense_category,
        "remaining_reserve": current_reserve - expense_amount,
        "entry_id": expense_entry["entry_id"]
    })

@app.route("/compliance/ledger")
def get_ledger():
    """Get compliance ledger history"""
    
    # Sort by timestamp, most recent first
    sorted_ledger = sorted(compliance_ledger, key=lambda x: x["timestamp"], reverse=True)
    
    return jsonify({
        "ledger_entries": sorted_ledger,
        "total_entries": len(sorted_ledger),
        "reserve_settings": reserve_settings
    })

@app.route("/compliance/reports/weekly")
def weekly_report():
    """Generate weekly compliance report - SAFE MODE"""
    
    # Calculate week-over-week metrics
    one_week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    
    recent_allocations = [
        entry for entry in compliance_ledger 
        if entry["timestamp"] > one_week_ago and entry["type"] == "allocation"
    ]
    
    recent_expenses = [
        entry for entry in compliance_ledger 
        if entry["timestamp"] > one_week_ago and entry["type"] == "expense"
    ]
    
    weekly_allocated = sum(entry["amount"] for entry in recent_allocations)
    weekly_spent = sum(entry["amount"] for entry in recent_expenses)
    
    total_reserve = sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "allocation") - \
                   sum(entry["amount"] for entry in compliance_ledger if entry["type"] == "expense")
    
    return jsonify({
        "report_period": {
            "start_date": one_week_ago,
            "end_date": datetime.utcnow().isoformat(),
            "period_type": "weekly"
        },
        "weekly_summary": {
            "revenue_allocated": weekly_allocated,
            "compliance_expenses": weekly_spent,
            "net_reserve_change": weekly_allocated - weekly_spent,
            "current_reserve_balance": total_reserve
        },
        "compliance_categories": {
            "legal_review": sum(e["amount"] for e in recent_expenses if e["category"] == "legal"),
            "audit_costs": sum(e["amount"] for e in recent_expenses if e["category"] == "audit"),
            "insurance": sum(e["amount"] for e in recent_expenses if e["category"] == "insurance"),
            "other": sum(e["amount"] for e in recent_expenses if e["category"] == "general")
        },
        "recommendations": [
            "Maintain 15% revenue allocation to compliance reserve",
            "Monthly legal review of new features",
            "Quarterly third-party security audit",
            "Annual compliance insurance policy review"
        ],
        "mode": "SAFE_MODE_DEMO"
    })

@app.route("/compliance/reports/monthly")
def monthly_report():
    """Generate monthly compliance report - SAFE MODE"""
    
    one_month_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
    
    monthly_allocations = [
        entry for entry in compliance_ledger 
        if entry["timestamp"] > one_month_ago and entry["type"] == "allocation"
    ]
    
    monthly_expenses = [
        entry for entry in compliance_ledger 
        if entry["timestamp"] > one_month_ago and entry["type"] == "expense"
    ]
    
    return jsonify({
        "report_period": {
            "start_date": one_month_ago,
            "end_date": datetime.utcnow().isoformat(),
            "period_type": "monthly"
        },
        "monthly_metrics": {
            "total_revenue_tracked": sum(revenue_sources.values()),
            "compliance_allocations": sum(entry["amount"] for entry in monthly_allocations),
            "compliance_expenses": sum(entry["amount"] for entry in monthly_expenses),
            "reserve_growth": len(monthly_allocations) - len(monthly_expenses)
        },
        "expense_breakdown": {
            "legal_fees": sum(e["amount"] for e in monthly_expenses if e["category"] == "legal"),
            "audit_costs": sum(e["amount"] for e in monthly_expenses if e["category"] == "audit"), 
            "insurance_premiums": sum(e["amount"] for e in monthly_expenses if e["category"] == "insurance"),
            "training_costs": sum(e["amount"] for e in monthly_expenses if e["category"] == "training")
        },
        "mode": "SAFE_MODE_DEMO"
    })

if __name__ == "__main__":
    print("SINCOR Compliance Reserve System - SAFE MODE")
    print("Revenue allocation and compliance tracking")
    print("Demo endpoints:")
    print("- GET /compliance/reserve/status")
    print("- POST /compliance/reserve/allocate") 
    print("- POST /compliance/reserve/expense")
    print("- GET /compliance/ledger")
    print("- GET /compliance/reports/weekly")
    print("- GET /compliance/reports/monthly")
    
    app.run(host="0.0.0.0", port=8005, debug=False)