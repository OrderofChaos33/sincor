from dataclasses import dataclass, field
from typing import Dict, List, Any
import time

@dataclass
class TaskToken:
    task_id: str
    origin: str
    intent: str
    spec: Dict[str, Any]
    budget: Dict[str, Any]
    deadline_unix: int
    priority: float
    lineage: List[Dict[str, Any]] = field(default_factory=list)
    assignments: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    qa: List[Dict[str, Any]] = field(default_factory=list)
    risk: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Lot:
    lot_id: str
    scope: str
    target_guild: str
    required_skills: Dict[str, float]
    budget: float
    deadline_s: int
    diversity_lambda: float = 0.1

@dataclass
class AuctionSpec:
    task_id: str
    lots: List[Lot]
    market_rules: Dict[str, Any]