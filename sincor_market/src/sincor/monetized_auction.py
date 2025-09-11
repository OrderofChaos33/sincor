from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import time
import yaml
from pathlib import Path

from .auction import AuctionEngine, Bid
from .monetization import PricingEngine, RevenuePriority, Quote
from .client import Client
from .value_logic import ValueLogic, CompletionEvent


@dataclass
class MonetizedBid(Bid):
    """Extended bid with monetization data"""
    client_price: float = 0.0
    margin: float = 0.0
    segment: str = "sme"
    strategic_weight: float = 1.0


class MonetizedAuctionEngine(AuctionEngine):
    """Auction engine enhanced with monetization and value logic"""
    
    def __init__(self, taxonomy: List[str], monetization_config: str, 
                 clients_config: str, value_graph_config: str, value_policy_config: str):
        super().__init__(taxonomy)
        
        # Load configurations
        self.monetization_policy = yaml.safe_load(Path(monetization_config).read_text())
        self.clients_config = yaml.safe_load(Path(clients_config).read_text())
        
        # Initialize engines
        self.pricing_engine = PricingEngine(self.monetization_policy)
        self.value_logic = ValueLogic(value_graph_config, value_policy_config)
        
        # Monetization tracking
        self.revenue_history: List[Dict[str, Any]] = []
        
    def get_client(self, client_id: str) -> Client:
        """Get or create client from configuration"""
        if client_id in self.clients_config.get("clients", {}):
            client_data = self.clients_config["clients"][client_id]
            return Client(client_id=client_id, **client_data)
        else:
            # Use defaults for unknown clients
            defaults = self.clients_config.get("segment_defaults", {}).get("sme", {})
            return Client(client_id=client_id, **defaults)
    
    def estimate_base_cost(self, lot, agents: List[Any]) -> float:
        """Estimate base cost for a lot based on agent rates and effort"""
        if not agents:
            return 50.0  # Default fallback
            
        # Average agent hourly rate
        avg_rate = sum(a.cost_model["rate"] for a in agents) / len(agents)
        
        # Estimate effort hours based on lot scope and skills required
        effort_multiplier = len(lot.required_skills) * 0.5  # More skills = more effort
        base_hours = max(0.5, effort_multiplier)
        
        return avg_rate * base_hours
    
    def hours_to_deadline(self, lot) -> float:
        """Calculate hours to deadline"""
        return max(0.5, lot.deadline_s / 3600.0)
    
    def current_system_load(self) -> float:
        """Calculate current system load (simplified)"""
        # In real implementation, this would check actual system metrics
        return 0.6
    
    def run_with_monetization(self, lot, agents: List[Any], client_id: str, 
                            rules: Dict[str, Any]) -> Tuple[MonetizedBid, float, List[MonetizedBid], Quote]:
        """Run auction with full monetization integration"""
        
        # Get client and estimate costs
        client = self.get_client(client_id)
        base_cost = self.estimate_base_cost(lot, agents)
        
        # Generate pricing quote
        quote = self.pricing_engine.quote(
            base_cost=base_cost,
            segment=client.segment,
            hours_to_deadline=self.hours_to_deadline(lot),
            system_load=self.current_system_load(),
            risk=getattr(lot, 'risk', {}),
            bundle=getattr(lot, 'bundle', None),
            ab_variant=True
        )
        
        # Calculate revenue priority
        effort_hours = max(0.25, base_cost / 30.0)  # Estimate effort from cost
        segment_config = self.monetization_policy.get("segments", {}).get(client.segment, {})
        priority_weight = segment_config.get("priority_weight", 1.0)
        
        revenue_priority = RevenuePriority.score(
            price=quote.price,
            base_cost=base_cost,
            effort_hours=effort_hours,
            strategic_weight=client.strategic_weight,
            segment_priority_weight=priority_weight
        )
        
        # Set value hint for auction
        lot.value_hint = min(2.0, 0.8 + revenue_priority / 50.0)
        
        # Run base auction with enhanced bidding
        monetized_bids = []
        agents_by_id = {a.id: a for a in agents}
        
        for agent in agents:
            if not self.qualify(agent, lot.required_skills):
                continue
                
            # Calculate bid with monetization considerations
            eta = max(30, int(lot.deadline_s * 0.6))
            ask = round(agent.cost_model["rate"] * (eta/60.0), 2)
            conf = min(0.95, 0.55 + 0.45*sum([agent.skills.get(k,0.0) for k in lot.required_skills])/max(1,len(lot.required_skills)))
            risk_adj = 0.10 if any("external_write:true" in f for f in agent.risk_flags) else 0.0
            
            # Create monetized bid
            bid = MonetizedBid(
                task_id=lot.lot_id, 
                lot_id=lot.lot_id,
                agent_id=agent.id,
                eta_s=eta,
                ask=ask,
                confidence=conf,
                risk_adj=risk_adj,
                slot=1,
                value_hint=lot.value_hint,
                client_price=quote.price,
                margin=quote.margin_absolute,
                segment=client.segment,
                strategic_weight=client.strategic_weight
            )
            
            # Calculate diversity bonus
            bid.diversity_bonus = self.diversity(agent, agents_by_id, lot.lot_id, getattr(lot, "diversity_lambda", 0.1))
            
            # Enhanced scoring with monetization
            bid.score = self.score_monetized_bid(bid, revenue_priority)
            monetized_bids.append(bid)
        
        if not monetized_bids:
            raise RuntimeError("No qualifying monetized bids")
            
        # Select winner
        monetized_bids.sort(key=lambda b: b.score, reverse=True)
        winner = monetized_bids[0]
        
        # Calculate second price with monetization considerations
        asks_sorted = sorted([b.ask for b in monetized_bids])
        pay = asks_sorted[1] if len(asks_sorted) > 1 else winner.ask
        
        # Record winner history and revenue metrics
        self.last_k_winners.setdefault(lot.lot_id, []).append(winner.agent_id)
        
        # Track revenue
        revenue_record = {
            "timestamp": time.time(),
            "lot_id": lot.lot_id,
            "client_id": client_id,
            "segment": client.segment,
            "client_price": quote.price,
            "provider_cost": pay,
            "margin": quote.price - pay,
            "margin_pct": (quote.price - pay) / quote.price if quote.price > 0 else 0,
            "revenue_priority": revenue_priority,
            "winner_agent": winner.agent_id
        }
        self.revenue_history.append(revenue_record)
        
        return winner, pay, monetized_bids, quote
    
    def score_monetized_bid(self, bid: MonetizedBid, revenue_priority: float) -> float:
        """Enhanced bid scoring with monetization factors"""
        
        # Base auction score
        base_score = bid.value_hint * bid.confidence * bid.freshness - (bid.ask + bid.risk_adj) + bid.diversity_bonus
        
        # Monetization enhancements
        margin_bonus = bid.margin / 100.0  # Normalize margin to reasonable scale
        strategic_bonus = (bid.strategic_weight - 1.0) * 5  # Bonus for strategic clients
        
        # Combine scores
        monetized_score = base_score + margin_bonus + strategic_bonus
        
        return monetized_score
    
    def handle_completion(self, task_id: str, product_type: str, scope: str, 
                         artifacts: List[Dict[str, Any]], confidence: float = 1.0) -> List[Any]:
        """Handle task completion with value logic"""
        
        completion = CompletionEvent(
            task_id=task_id,
            product_type=product_type,
            scope=scope,
            artifacts=artifacts,
            confidence=confidence
        )
        
        # Generate derivative tasks
        derivatives = self.value_logic.derivatives_for(completion)
        
        # Generate feedback signals
        feedback_signals = self.value_logic.feedback_signals(completion)
        
        return {
            "derivatives": derivatives,
            "feedback_signals": feedback_signals,
            "completion_logged": True
        }
    
    def get_revenue_metrics(self) -> Dict[str, Any]:
        """Get current revenue performance metrics"""
        if not self.revenue_history:
            return {"total_records": 0}
            
        recent_records = self.revenue_history[-100:]  # Last 100 transactions
        
        total_revenue = sum(r["client_price"] for r in recent_records)
        total_margin = sum(r["margin"] for r in recent_records)
        avg_margin_pct = sum(r["margin_pct"] for r in recent_records) / len(recent_records)
        
        # Segment breakdown
        segment_stats = {}
        for record in recent_records:
            seg = record["segment"]
            if seg not in segment_stats:
                segment_stats[seg] = {"count": 0, "revenue": 0, "margin": 0}
            segment_stats[seg]["count"] += 1
            segment_stats[seg]["revenue"] += record["client_price"]
            segment_stats[seg]["margin"] += record["margin"]
        
        return {
            "total_records": len(self.revenue_history),
            "recent_revenue": total_revenue,
            "recent_margin": total_margin,
            "avg_margin_pct": avg_margin_pct,
            "segment_breakdown": segment_stats,
            "last_updated": time.time()
        }