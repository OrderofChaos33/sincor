from dataclasses import dataclass, field
from typing import Dict, List, Any
import yaml
from pathlib import Path

@dataclass
class Agent:
    id: str
    guild: str
    skills: Dict[str, float]
    cost_model: Dict[str, float]
    slo: Dict[str, float]
    risk_flags: List[str]
    reputation: Dict[str, float]
    availability: Dict[str, int]
    claims: List[str]
    inbox_topics: List[str]
    outbox_topics: List[str]
    # runtime attrs
    cold: bool = True

    def skill_vec(self, taxonomy: List[str]) -> List[float]:
        return [float(self.skills.get(k, 0.0)) for k in taxonomy]


@dataclass
class AgentRegistry:
    agents: List[Agent] = field(default_factory=list)
    taxonomy: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, agents_path: str, taxonomy_path: str) -> "AgentRegistry":
        taxonomy_doc = yaml.safe_load(Path(taxonomy_path).read_text())
        taxonomy = taxonomy_doc["taxonomy"]
        doc = yaml.safe_load(Path(agents_path).read_text())
        loaded = []
        for a in doc["agents"]:
            loaded.append(Agent(**a))
        return cls(agents=loaded, taxonomy=taxonomy)

    def by_guild(self, guild: str) -> List[Agent]:
        return [a for a in self.agents if a.guild == guild]