import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from .monetization import Quote
from .monetized_auction import MonetizedBid


class MonetizationLogger:
    """Structured logging for monetization events"""
    
    def __init__(self, enable_console: bool = True):
        self.enable_console = enable_console
        self.log_buffer: List[Dict[str, Any]] = []
    
    def _emit_log(self, event: Dict[str, Any]):
        """Emit log event"""
        if self.enable_console:
            print(json.dumps(event, indent=2))
        self.log_buffer.append(event)
        
        # Keep only last 1000 events in memory
        if len(self.log_buffer) > 1000:
            self.log_buffer = self.log_buffer[-1000:]
    
    def log_quote(self, task_id: str, client_id: str, quote: Quote, 
                  revenue_priority: float, value_hint: float, 
                  experiment_flags: Dict[str, Any] = None):
        """Log pricing quote details"""
        
        event = {
            "timestamp": time.time(),
            "event_type": "pricing_quote",
            "task_id": task_id,
            "client_id": client_id,
            "quote": {
                "price": quote.price,
                "base_cost": quote.base_cost,
                "margin_absolute": quote.margin_absolute,
                "margin_percentage": quote.margin_percentage,
                "pricing_details": {
                    "margin_factor": quote.margin_factor,
                    "surge_multiplier": quote.surge_multiplier,
                    "segment_weight": quote.segment_weight,
                    "risk_add": quote.risk_add,
                    "bundle_discount": quote.bundle_discount,
                    "exploration_applied": quote.exploration_applied,
                    "notes": quote.notes
                }
            },
            "revenue_priority": revenue_priority,
            "auction_value_hint": value_hint,
            "experiment_flags": experiment_flags or {}
        }
        
        self._emit_log(event)
    
    def log_auction_result(self, lot_id: str, winner: MonetizedBid, 
                          pay: float, total_bids: int, quote: Quote,
                          client_id: str, mode: str = "STRUCTURED"):
        """Log auction completion and results"""
        
        event = {
            "timestamp": time.time(),
            "event_type": "auction_result",
            "lot_id": lot_id,
            "client_id": client_id,
            "execution_mode": mode,
            "winner": {
                "agent_id": winner.agent_id,
                "ask": winner.ask,
                "pay": pay,
                "confidence": winner.confidence,
                "score": winner.score,
                "segment": winner.segment,
                "strategic_weight": winner.strategic_weight
            },
            "competition": {
                "total_bids": total_bids,
                "winning_margin": winner.score - (winner.ask + winner.risk_adj) if total_bids > 1 else 0
            },
            "financials": {
                "client_price": quote.price,
                "provider_cost": pay,
                "platform_margin": quote.price - pay,
                "margin_percentage": ((quote.price - pay) / quote.price * 100) if quote.price > 0 else 0
            }
        }
        
        self._emit_log(event)
    
    def log_swarm_result(self, lot_id: str, client_id: str, swarm_result: Dict[str, Any], 
                        quote: Quote):
        """Log SWARM mode execution results"""
        
        event = {
            "timestamp": time.time(),
            "event_type": "swarm_result", 
            "lot_id": lot_id,
            "client_id": client_id,
            "execution_mode": "SWARM",
            "swarm_data": {
                "confidence": swarm_result.get("confidence", 0),
                "pod_size": swarm_result.get("pod_size", 0),
                "runtime_s": swarm_result.get("runtime_s", 0),
                "consensus_method": swarm_result.get("consensus_method", ""),
                "artifact": swarm_result.get("artifact", "")
            },
            "financials": {
                "client_price": quote.price,
                "platform_margin": quote.margin_absolute,
                "margin_percentage": quote.margin_percentage * 100
            }
        }
        
        self._emit_log(event)
    
    def log_conversion(self, task_id: str, client_id: str, accepted: bool, 
                      final_price: float, abandonment_reason: Optional[str] = None):
        """Log customer conversion outcome"""
        
        event = {
            "timestamp": time.time(),
            "event_type": "conversion_outcome",
            "task_id": task_id,
            "client_id": client_id,
            "conversion": {
                "accepted": accepted,
                "final_price": final_price,
                "abandonment_reason": abandonment_reason
            }
        }
        
        self._emit_log(event)
    
    def log_value_creation(self, completion_task_id: str, product_type: str,
                          derivatives_created: int, feedback_signals: int):
        """Log value logic derivative creation"""
        
        event = {
            "timestamp": time.time(),
            "event_type": "value_creation",
            "source_task_id": completion_task_id,
            "product_type": product_type,
            "derivatives_spawned": derivatives_created,
            "feedback_signals_sent": feedback_signals,
            "value_multiplier_applied": True
        }
        
        self._emit_log(event)
    
    def log_revenue_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """Generate and log revenue summary for recent period"""
        
        cutoff_time = time.time() - (period_hours * 3600)
        recent_events = [e for e in self.log_buffer if e.get("timestamp", 0) >= cutoff_time]
        
        # Filter for financial events
        auction_results = [e for e in recent_events if e.get("event_type") == "auction_result"]
        swarm_results = [e for e in recent_events if e.get("event_type") == "swarm_result"]
        quotes = [e for e in recent_events if e.get("event_type") == "pricing_quote"]
        conversions = [e for e in recent_events if e.get("event_type") == "conversion_outcome"]
        
        total_tasks = len(auction_results) + len(swarm_results)
        total_quotes = len(quotes)
        
        # Revenue calculations
        total_revenue = 0
        total_margin = 0
        for event in auction_results + swarm_results:
            financials = event.get("financials", {})
            total_revenue += financials.get("client_price", 0)
            total_margin += financials.get("platform_margin", 0)
        
        # Conversion rate
        accepted_conversions = len([c for c in conversions if c.get("conversion", {}).get("accepted", False)])
        conversion_rate = (accepted_conversions / max(1, total_quotes)) * 100
        
        # Mode distribution
        structured_count = len([e for e in auction_results if e.get("execution_mode") == "STRUCTURED"])
        swarm_count = len([e for e in swarm_results if e.get("execution_mode") == "SWARM"])
        
        summary = {
            "timestamp": time.time(),
            "event_type": "revenue_summary",
            "period_hours": period_hours,
            "metrics": {
                "total_tasks_completed": total_tasks,
                "total_quotes_generated": total_quotes,
                "total_revenue": round(total_revenue, 2),
                "total_platform_margin": round(total_margin, 2),
                "average_margin_pct": round((total_margin / max(1, total_revenue)) * 100, 2),
                "conversion_rate_pct": round(conversion_rate, 2),
                "execution_modes": {
                    "structured": structured_count,
                    "swarm": swarm_count,
                    "structured_pct": round((structured_count / max(1, total_tasks)) * 100, 2)
                }
            }
        }
        
        self._emit_log(summary)
        return summary
    
    def get_recent_logs(self, event_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent log entries, optionally filtered by type"""
        
        filtered_logs = self.log_buffer
        if event_type:
            filtered_logs = [log for log in self.log_buffer if log.get("event_type") == event_type]
        
        return sorted(filtered_logs, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]
    
    def export_logs_json(self, filepath: str, hours_back: int = 24):
        """Export recent logs to JSON file"""
        cutoff_time = time.time() - (hours_back * 3600)
        recent_logs = [log for log in self.log_buffer if log.get("timestamp", 0) >= cutoff_time]
        
        with open(filepath, 'w') as f:
            json.dump({
                "export_timestamp": time.time(),
                "hours_back": hours_back,
                "total_events": len(recent_logs),
                "events": recent_logs
            }, f, indent=2)
            
        return len(recent_logs)