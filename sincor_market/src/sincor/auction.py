from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import math
import time
import random

@dataclass
class Bid:
    task_id: str
    lot_id: str
    agent_id: str
    eta_s: int
    ask: float
    confidence: float
    risk_adj: float
    slot: int
    freshness: float = 1.0
    value_hint: float = 1.0  # ORCH-provided V per unit
    diversity_bonus: float = 0.0
    score: float = 0.0  # computed

def jaccard(a: List[float], b: List[float], topk: int = 3) -> float:
    def top_idx(vec):
        return set(sorted(range(len(vec)), key=lambda i: vec[i], reverse=True)[:topk])
    A, B = top_idx(a), top_idx(b)
    return len(A & B)/max(1, len(A | B))

class AuctionEngine:
    def __init__(self, taxonomy: List[str], last_k_winners: Dict[str, List[str]] = None):
        self.taxonomy = taxonomy
        self.last_k_winners = last_k_winners or {}  # lot_id -> [agent_ids]

    def qualify(self, agent, required_skills: Dict[str, float]) -> bool:
        for k, th in required_skills.items():
            if float(agent.skills.get(k, 0.0)) < float(th):
                return False
        return True

    def diversity(self, agent, agents_by_id: Dict[str, Any], lot_id: str, lambda_: float) -> float:
        prev = self.last_k_winners.get(lot_id, [])[-5:]
        if not prev:
            return 0.0
        a_vec = agent.skill_vec(self.taxonomy)
        j_scores = []
        for pid in prev:
            p = agents_by_id.get(pid)
            if p:
                j_scores.append(jaccard(a_vec, p.skill_vec(self.taxonomy)))
        if not j_scores:
            return 0.0
        return lambda_ * (1.0 - sum(j_scores)/len(j_scores))

    def score_bid(self, bid: Bid) -> float:
        penalties = bid.ask + bid.risk_adj
        return bid.value_hint * bid.confidence * bid.freshness - penalties + bid.diversity_bonus

    def run(self, lot, agents: List[Any], rules: Dict[str, Any]) -> Tuple[Bid, float, List[Bid]]:
        T_bidding = int(rules.get("T_bidding_s", 3))
        lambda_div = float(getattr(lot, "diversity_lambda", 0.1))
        agents_by_id = {a.id: a for a in agents}
        # produce bids
        bids: List[Bid] = []
        for a in agents:
            if not self.qualify(a, lot.required_skills):
                continue
            eta = max(30, int(lot.deadline_s * 0.6))
            ask = round(a.cost_model["rate"] * (eta/60.0), 2)
            conf = min(0.95, 0.55 + 0.45*sum([a.skills.get(k,0.0) for k in lot.required_skills])/max(1,len(lot.required_skills)))
            risk_adj = 0.10 if any("external_write:true" in f for f in a.risk_flags) else 0.0
            bid = Bid(
                task_id="TT", lot_id=lot.lot_id, agent_id=a.id, eta_s=eta,
                ask=ask, confidence=conf, risk_adj=risk_adj, slot=1, value_hint=1.0
            )
            bid.diversity_bonus = self.diversity(a, agents_by_id, lot.lot_id, lambda_div)
            bid.score = self.score_bid(bid)
            bids.append(bid)
        if not bids:
            raise RuntimeError("No qualifying bids")
        bids.sort(key=lambda b: b.score, reverse=True)
        winner = bids[0]
        # second price = second-lowest ask among scored bidders (simplified)
        asks_sorted = sorted([b.ask for b in bids])
        pay = asks_sorted[1] if len(asks_sorted) > 1 else winner.ask
        # record winner history
        self.last_k_winners.setdefault(lot.lot_id, []).append(winner.agent_id)
        return winner, pay, bids