from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Signal:
    novelty: float        # unseen pattern? embedding distance vs corpus
    ambiguity: float      # spec entropy / conflicting constraints
    time_pressure: float  # deadline tightness vs historical P95
    externality: float    # vendor/API unknowns, ToS risk
    exploration_budget: float  # % budget earmarked for explore
    safety_risk: float    # PII/ext_write/legal flags

def choose_mode(sig: Signal, policy: Dict[str, Any]) -> str:
    # hard rails first
    if sig.safety_risk >= policy["rails"]["max_safety_risk"]:
        return "STRUCTURED"
    
    # score for swarm
    swarm_score = (
        policy["weights"]["novelty"] * sig.novelty +
        policy["weights"]["ambiguity"] * sig.ambiguity +
        policy["weights"]["time_pressure"] * sig.time_pressure +
        policy["weights"]["externality"] * sig.externality +
        policy["weights"]["exploration"] * sig.exploration_budget
    )
    
    return "SWARM" if swarm_score >= policy["thresholds"]["swarm_min"] else "STRUCTURED"