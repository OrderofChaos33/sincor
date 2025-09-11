import time
from typing import Dict, Any, Optional

class HandoffManager:
    def __init__(self, T_ack_s: int = 5):
        self.T_ack_s = T_ack_s

    def request(self, from_agent: str, to_guild: str, task_id: str, lot_id: str, artifacts: list, checks: list) -> Dict[str, Any]:
        return {
            "topic": "handoff.request",
            "from": from_agent,
            "to_guild": to_guild,
            "task_id": task_id,
            "lot_id": lot_id,
            "artifacts": artifacts,
            "checks": checks,
            "ts": time.time(),
        }

    def await_ack(self, maybe_ack: Optional[Dict[str, Any]]) -> bool:
        # In real system, this would be event-driven. Here we accept if ack present and timely.
        if not maybe_ack:
            return False
        age = time.time() - maybe_ack.get("ts", time.time())
        return age <= self.T_ack_s