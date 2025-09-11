
"""
Recursive Value Logic for SINCOR.
- Spawns derivative tasks on product completion (based on value_multipliers & recipes).
- Emits feedback signals between product types to reinforce adjacent products.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import time, hashlib, random, uuid, yaml
from pathlib import Path

@dataclass
class CompletionEvent:
    task_id: str
    product_type: str
    scope: str
    artifacts: List[Dict[str, Any]]
    confidence: float = 1.0  # or QA score
    ts: float = time.time()

@dataclass
class DerivativeTask:
    task_id: str
    origin: str
    intent: str
    product_type: str
    spec: Dict[str, Any]
    priority: float
    target_guild: str

class ValueLogic:
    def __init__(self, graph_path: str, policy_path: str, rng_seed: int = 1337):
        self.graph = yaml.safe_load(Path(graph_path).read_text())
        self.policy = yaml.safe_load(Path(policy_path).read_text())
        self._rng = random.Random(rng_seed)
        self._feedback_cache = {}  # (src_type, tgt_type) -> last_ts

    def _gen_task_id(self, prefix: str) -> str:
        return f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}"

    def _routing_for(self, product_type: str) -> str:
        return self.graph.get("routing", {}).get(product_type, "PROD")

    def derivatives_for(self, completion: CompletionEvent) -> List[DerivativeTask]:
        if not self.policy["spawn"]["enable"]:
            return []
        if completion.confidence < self.policy["spawn"]["min_confidence_to_spawn"]:
            return []
        recipes = self.graph.get("derivative_recipes", {}).get(completion.product_type, [])
        multiplier = int(self.graph.get("value_multipliers", {}).get(completion.product_type, 1))
        # Limit how many we emit per completion
        limit = min(self.policy["spawn"]["max_derivatives_per_completion"],
                    self.policy["spawn"]["throttle_per_task"],
                    max(0, multiplier))
        # Sample up to limit from recipes (with replacement if need more than unique recipes)
        out: List[DerivativeTask] = []
        for i in range(limit):
            r = recipes[i % max(1, len(recipes))] if recipes else {"type": "template", "scope": "Generalize artifact"}
            pt = r["type"]
            scope = r.get("scope", f"Derive from {completion.product_type}")
            tid = self._gen_task_id(self.policy["naming"]["task_prefix"])
            intent = f"Derive {pt} from {completion.product_type}"
            priority = min(1.0, self.policy["priors"]["default_priority"] + self.policy["priors"]["derivative_priority_boost"])
            target_guild = self._routing_for(pt)
            spec = {
                "source_task": completion.task_id,
                "source_type": completion.product_type,
                "derivation_scope": scope,
                "artifacts": completion.artifacts
            }
            out.append(DerivativeTask(
                task_id=tid, origin=completion.task_id, intent=intent,
                product_type=pt, spec=spec, priority=priority, target_guild=target_guild
            ))
        return out

    def feedback_signals(self, completion: CompletionEvent) -> List[Dict[str, Any]]:
        if not self.policy["feedback"]["enable"]:
            return []
        edges = self.graph.get("feedback_edges", {}).get(completion.product_type, [])
        fanout = min(self.policy["feedback"]["max_fanout"], len(edges))
        out = []
        now = time.time()
        for tgt in edges[:fanout]:
            key = (completion.product_type, tgt)
            last = self._feedback_cache.get(key, 0)
            if now - last < self.policy["feedback"]["debounce_s"]:
                continue
            self._feedback_cache[key] = now
            out.append({
                "topic": "value.feedback",
                "from_type": completion.product_type,
                "to_type": tgt,
                "source_task": completion.task_id,
                "ts": now
            })
        return out
