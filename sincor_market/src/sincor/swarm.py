import time
import random
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class SwarmAgent:
    """Lightweight swarm agent archetype"""
    id: str
    archetype: str  # Scout, Synthesizer, Critic, RedTeamer, Mapper
    confidence: float = 0.0
    route_trace: List[str] = None

    def __post_init__(self):
        if self.route_trace is None:
            self.route_trace = []

class SwarmAdapter:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.archetypes = ["Scout", "Synthesizer", "Contrastive_Critic", "Red_Teamer", "Mapper"]
    
    def spawn_pod(self, size: int) -> List[SwarmAgent]:
        """Spawn a pod of diverse swarm agents"""
        pod = []
        for i in range(size):
            archetype = random.choice(self.archetypes)
            agent = SwarmAgent(
                id=f"swarm_{archetype.lower()}_{i}",
                archetype=archetype
            )
            pod.append(agent)
        return pod
    
    def run_multi_route(self, lot, pod: List[SwarmAgent]) -> Dict[str, Any]:
        """Run multiple independent solution routes"""
        routes = []
        
        for agent in pod:
            # Simulate different solution approaches based on archetype
            if agent.archetype == "Scout":
                agent.confidence = random.uniform(0.6, 0.9)
                agent.route_trace = ["search_phase", "discovery", "triage"]
            elif agent.archetype == "Synthesizer":
                agent.confidence = random.uniform(0.7, 0.95)
                agent.route_trace = ["analysis", "synthesis", "integration"]
            elif agent.archetype == "Contrastive_Critic":
                agent.confidence = random.uniform(0.5, 0.8)
                agent.route_trace = ["contrast", "critique", "validation"]
            elif agent.archetype == "Red_Teamer":
                agent.confidence = random.uniform(0.4, 0.7)
                agent.route_trace = ["attack_vectors", "failure_modes", "edge_cases"]
            elif agent.archetype == "Mapper":
                agent.confidence = random.uniform(0.6, 0.85)
                agent.route_trace = ["mapping", "structure", "relationships"]
            
            routes.append({
                "agent_id": agent.id,
                "archetype": agent.archetype,
                "confidence": agent.confidence,
                "trace": agent.route_trace
            })
        
        return {"routes": routes}
    
    def compute_consensus(self, routes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute consensus from multiple routes using quorum"""
        # Sort routes by confidence
        sorted_routes = sorted(routes, key=lambda r: r["confidence"], reverse=True)
        
        # Take top 3 for quorum (3-of-5 consensus)
        top_routes = sorted_routes[:3]
        avg_confidence = sum(r["confidence"] for r in top_routes) / len(top_routes)
        
        # Check if consensus meets exit threshold
        consensus_confidence = min(0.95, avg_confidence * 0.9)  # slight penalty for averaging
        
        return {
            "confidence": consensus_confidence,
            "participating_routes": len(top_routes),
            "top_routes": [r["agent_id"] for r in top_routes],
            "evidence": [r["trace"] for r in top_routes]
        }
    
    def run(self, lot, mem=None, tools=None) -> Dict[str, Any]:
        """Main swarm execution"""
        start_time = time.time()
        
        # Spawn pod
        pod_size = random.randint(
            self.policy["swarm_pod"]["size"]["min"],
            self.policy["swarm_pod"]["size"]["max"]
        )
        pod = self.spawn_pod(pod_size)
        
        # Run multi-route search/synthesis
        route_results = self.run_multi_route(lot, pod)
        
        # Compute consensus
        consensus = self.compute_consensus(route_results["routes"])
        
        # Generate artifact URI (simulated)
        artifact_uri = f"swarm://artifacts/{lot.lot_id}/consensus_{int(time.time())}"
        
        runtime = time.time() - start_time
        
        return {
            "artifact": artifact_uri,
            "evidence": consensus["evidence"],
            "confidence": consensus["confidence"],
            "route_traces": route_results["routes"],
            "runtime_s": runtime,
            "pod_size": pod_size,
            "consensus_method": self.policy["swarm_pod"]["consensus"]
        }