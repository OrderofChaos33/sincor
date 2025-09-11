from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import random
import math

@dataclass
class Quote:
    price: float
    base_cost: float
    margin_factor: float
    surge_multiplier: float = 1.0
    segment_weight: float = 1.0
    risk_add: float = 0.0
    bundle_discount: float = 0.0
    exploration_applied: bool = False
    notes: str = ""
    
    @property
    def margin_absolute(self) -> float:
        return self.price - self.base_cost
    
    @property
    def margin_percentage(self) -> float:
        if self.base_cost == 0:
            return 0.0
        return (self.price - self.base_cost) / self.base_cost

class PricingEngine:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.margin = policy.get("margin", {})
        self.segments = policy.get("segments", {})
        self.surge = policy.get("surge", {})
        self.experiment = policy.get("experiment", {})
        self.risk_pricing = policy.get("risk_pricing", {})
        
    def _get_segment_config(self, segment: str) -> Dict[str, Any]:
        """Get configuration for client segment"""
        return self.segments.get(segment, self.segments.get("sme", {}))
    
    def _calculate_base_margin(self, segment: str, base_cost: float) -> float:
        """Calculate base margin multiplier for segment"""
        seg_config = self._get_segment_config(segment)
        margin_factor = seg_config.get("margin_multiplier", 1.3)
        
        # Apply margin bounds
        floor = self.margin.get("floor", 0.20)
        ceiling = self.margin.get("ceiling", 0.55)
        
        # Ensure minimum margin
        min_price = base_cost * (1 + floor)
        max_price = base_cost * (1 + ceiling)
        target_price = base_cost * margin_factor
        
        return max(min_price, min(max_price, target_price)) / base_cost
    
    def _calculate_surge(self, hours_to_deadline: float, system_load: float) -> float:
        """Calculate surge multiplier based on urgency and system load"""
        surge_config = self.surge.get("deadline", {})
        
        # Time pressure component
        if hours_to_deadline < 2:
            time_surge = surge_config.get("rush", 1.4)
        elif hours_to_deadline < 6:
            time_surge = surge_config.get("tight", 1.25)
        else:
            time_surge = 1.0
            
        # System load component
        if system_load > 0.8:
            load_surge = 1.2
        elif system_load > 0.6:
            load_surge = 1.1
        else:
            load_surge = 1.0
            
        # Combined surge with cap
        surge_multiplier = time_surge * load_surge
        surge_cap = self.surge.get("cap", 3.0)
        
        return min(surge_multiplier, surge_cap)
    
    def _calculate_risk_adjustment(self, risk: Dict[str, Any]) -> float:
        """Calculate risk-based pricing adjustment"""
        risk_add = 0.0
        
        if risk.get("pii", False):
            risk_add += self.risk_pricing.get("pii_add", 5.0)
        if risk.get("ext_write", False):
            risk_add += self.risk_pricing.get("ext_write_add", 10.0)
        if risk.get("legal_hold", False):
            risk_add += self.risk_pricing.get("legal_add", 15.0)
            
        return risk_add
    
    def _apply_bundle_discount(self, base_price: float, bundle: Optional[str]) -> float:
        """Apply bundle pricing discounts"""
        if not bundle:
            return 0.0
            
        bundle_config = self.policy.get("bundles", {}).get(bundle, {})
        discount_pct = bundle_config.get("discount_pct", 0.0)
        
        return base_price * discount_pct
    
    def _apply_exploration(self, price: float, ab_variant: bool) -> tuple[float, bool]:
        """Apply A/B test exploration pricing"""
        if not ab_variant:
            return price, False
            
        exploration_rate = self.experiment.get("exploration_rate", 0.05)
        
        if random.random() < exploration_rate:
            # Apply small random adjustment for exploration
            adjustment = random.uniform(-0.1, 0.1)  # ±10%
            return price * (1 + adjustment), True
            
        return price, False
    
    def quote(self, base_cost: float, segment: str, hours_to_deadline: float, 
              system_load: float, risk: Dict[str, Any] = None, 
              bundle: Optional[str] = None, ab_variant: bool = False) -> Quote:
        """Generate a price quote for a task"""
        
        risk = risk or {}
        
        # Base margin calculation
        margin_factor = self._calculate_base_margin(segment, base_cost)
        base_price = base_cost * margin_factor
        
        # Surge pricing
        surge_multiplier = self._calculate_surge(hours_to_deadline, system_load)
        surged_price = base_price * surge_multiplier
        
        # Risk adjustments (flat add, not percentage)
        risk_add = self._calculate_risk_adjustment(risk)
        
        # Bundle discounts
        bundle_discount = self._apply_bundle_discount(surged_price, bundle)
        
        # Calculate intermediate price
        price_before_exploration = surged_price + risk_add - bundle_discount
        
        # A/B exploration
        final_price, exploration_applied = self._apply_exploration(price_before_exploration, ab_variant)
        
        # Get segment config for metadata
        seg_config = self._get_segment_config(segment)
        segment_weight = seg_config.get("margin_multiplier", 1.3)
        
        notes = []
        if surge_multiplier > 1.0:
            notes.append(f"surge_{surge_multiplier:.2f}")
        if risk_add > 0:
            notes.append(f"risk_+${risk_add:.0f}")
        if bundle_discount > 0:
            notes.append(f"bundle_-${bundle_discount:.0f}")
        if exploration_applied:
            notes.append("exploration_variant")
            
        return Quote(
            price=round(final_price, 2),
            base_cost=base_cost,
            margin_factor=margin_factor,
            surge_multiplier=surge_multiplier,
            segment_weight=segment_weight,
            risk_add=risk_add,
            bundle_discount=bundle_discount,
            exploration_applied=exploration_applied,
            notes=", ".join(notes) if notes else "standard_pricing"
        )

class RevenuePriority:
    @staticmethod
    def score(price: float, base_cost: float, effort_hours: float = 1.0, 
              strategic_weight: float = 1.0, segment_priority_weight: float = 1.0) -> float:
        """Calculate revenue priority score for auction value_hint"""
        
        # Base margin value
        margin = price - base_cost
        margin_per_hour = margin / max(0.25, effort_hours)  # Avoid division by zero
        
        # Strategic adjustments
        strategic_bonus = (strategic_weight - 1.0) * 10  # Strategic clients get bonus
        segment_bonus = (segment_priority_weight - 1.0) * 5  # Priority segments get bonus
        
        # Combined revenue priority score
        base_score = margin_per_hour * 2  # Scale margin to reasonable range
        total_score = base_score + strategic_bonus + segment_bonus
        
        # Ensure positive score
        return max(0.1, total_score)