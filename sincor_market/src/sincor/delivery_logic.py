
"""
Service Delivery Logic for BI agent workflows.
- Routes tasks into express vs deepdive modes.
- Computes quality scores from QA + client feedback.
- Escalates when conditions met.
"""
import time, uuid, yaml
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class DeliveryTask:
    task_id: str
    client_id: str
    segment: str
    mode: str
    deadline_minutes: int
    modules: List[str]

@dataclass
class QualityScore:
    qa_metrics: float
    client_feedback: float
    review_override: float = 0.0

    def compute(self, weights=(0.5,0.4,0.1)) -> float:
        return (weights[0]*self.qa_metrics +
                weights[1]*self.client_feedback +
                weights[2]*self.review_override)

class ServiceDelivery:
    def __init__(self, delivery_modes_path: str, escalation_path: str):
        self.modes = yaml.safe_load(Path(delivery_modes_path).read_text())["modes"]
        self.escalation = yaml.safe_load(Path(escalation_path).read_text())

    def create_task(self, client_id: str, segment: str, mode: str) -> DeliveryTask:
        spec = self.modes.get(mode)
        if not spec:
            raise ValueError(f"Unknown delivery mode: {mode}")
        tid = f"TASK-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        return DeliveryTask(task_id=tid, client_id=client_id,
                            segment=segment, mode=mode,
                            deadline_minutes=spec["deadline_minutes"],
                            modules=spec["modules"])

    def evaluate_quality(self, qa: float, feedback: float, override: float=0.0) -> float:
        qs = QualityScore(qa_metrics=qa, client_feedback=feedback, review_override=override)
        return qs.compute()

    def needs_escalation(self, quality: float, confidence: float, segment: str, feedback_streak: int) -> str:
        t = self.escalation["triggers"]
        if confidence < t["low_confidence"]: return "L1"
        if quality < t["low_quality"]: return "L1"
        if segment == t["high_value_client_segment"]: return "L1"
        if feedback_streak >= t["repeated_low_feedback"]: return "L2"
        return ""

    def escalation_action(self, level: str) -> Dict[str, Any]:
        return self.escalation["levels"].get(level, {})
