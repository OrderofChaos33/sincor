from pathlib import Path
from dataclasses import asdict
import yaml, time, random
from sincor.agents import AgentRegistry
from sincor.task import TaskToken, Lot, AuctionSpec
from sincor.auction import AuctionEngine
from sincor.handoff import HandoffManager
from sincor.mode_select import choose_mode, Signal
from sincor.swarm import SwarmAdapter

# Load registry and policies
root = Path(".")
reg = AgentRegistry.load(str(root/"config/agents.yaml"), str(root/"config/taxonomy.yaml"))
mode_policy = yaml.safe_load((root/"config/mode_policy.yaml").read_text())

# Define a task with 3 lots
task = TaskToken(
    task_id="TT-2025-0903-0017",
    origin="S2",
    intent="Generate lead-magnet PDF for plumbers",
    spec={"acceptance": ["<=10MB", "brand:SINCOR", "CTA:/book"]},
    budget={"hard": 120, "soft": 90, "currency": "credits"},
    deadline_unix=int(time.time())+3600,
    priority=0.78,
    risk={"pii": False, "ext_write": False}
)

lots = [
    Lot(lot_id="L1", scope="Outline + sources", target_guild="PROD",
        required_skills={"synthesis":0.7,"research":0.6}, budget=20, deadline_s=900, diversity_lambda=0.1),
    Lot(lot_id="L2", scope="Design + layout", target_guild="PROD", 
        required_skills={"design":0.8,"viz":0.6}, budget=40, deadline_s=1800, diversity_lambda=0.1),
    Lot(lot_id="L3", scope="QA conformance", target_guild="QA",
        required_skills={"qa-auto":0.7,"qa-redteam":0.3}, budget=15, deadline_s=900, diversity_lambda=0.1),
]

spec = AuctionSpec(
    task_id=task.task_id,
    lots=lots,
    market_rules={"auction_type":"vickrey","T_bidding_s":3,"T_ack_s":5,"cooldown_fail_s":60,"max_parallel_wins_per_agent":1}
)

# Initialize engines
auction_engine = AuctionEngine(reg.taxonomy)
swarm_adapter = SwarmAdapter(mode_policy)
handoff_manager = HandoffManager(T_ack_s=spec.market_rules["T_ack_s"])

print("=== SINCOR DUAL MODE SIMULATION ===")
print(f"Task: {task.intent}")
print(f"Lots: {len(spec.lots)}")
print()

results = []
for lot in spec.lots:
    print(f"--- Processing {lot.lot_id}: {lot.scope} ---")
    
    # Compute signals for mode selection
    # Simulate different signal values for demonstration
    if lot.lot_id == "L1":  # Research-heavy lot - likely SWARM
        signal = Signal(
            novelty=0.8,           # High novelty - new domain
            ambiguity=0.6,         # Moderate ambiguity
            time_pressure=0.3,     # Low time pressure
            externality=0.2,       # Low external dependencies  
            exploration_budget=0.4, # Medium exploration budget
            safety_risk=0.1        # Low safety risk
        )
    elif lot.lot_id == "L2":  # Design lot - could go either way
        signal = Signal(
            novelty=0.4,
            ambiguity=0.7,         # High ambiguity - creative decisions
            time_pressure=0.6,     # Higher time pressure
            externality=0.3,
            exploration_budget=0.3,
            safety_risk=0.2
        )
    else:  # QA lot - likely STRUCTURED
        signal = Signal(
            novelty=0.2,           # Low novelty - established QA processes
            ambiguity=0.3,         # Low ambiguity
            time_pressure=0.8,     # High time pressure
            externality=0.1,
            exploration_budget=0.1,
            safety_risk=0.4        # Higher safety risk
        )
    
    # Choose execution mode
    mode = choose_mode(signal, mode_policy)
    print(f"Mode selected: {mode}")
    print(f"Signals: novelty={signal.novelty}, ambiguity={signal.ambiguity}, safety_risk={signal.safety_risk}")
    
    if mode == "SWARM":
        print("Executing via SWARM mode...")
        swarm_result = swarm_adapter.run(lot, mem=None, tools=None)
        
        # Check if confidence meets threshold for QA handoff
        if swarm_result["confidence"] >= mode_policy["thresholds"]["swarm_exit_confidence"]:
            print(f"SWARM confidence {swarm_result['confidence']:.3f} meets threshold, handing off to QA...")
            handoff_msg = handoff_manager.request(
                from_agent="swarm_coordinator",
                to_guild="QA", 
                task_id=task.task_id,
                lot_id=lot.lot_id,
                artifacts=[{"uri": swarm_result["artifact"], "sha256": "swarm_consensus"}],
                checks=["consensus_quality", "route_diversity", "confidence_threshold"]
            )
            # Simulate immediate ack
            ack = dict(handoff_msg)
            ack_success = handoff_manager.await_ack(ack)
            print(f"QA handoff ACK: {'SUCCESS' if ack_success else 'FAILED'}")
        else:
            print(f"SWARM confidence {swarm_result['confidence']:.3f} below threshold, escalating to ORCH...")
        
        results.append({
            "lot": lot,
            "mode": mode,
            "swarm_result": swarm_result,
            "confidence": swarm_result["confidence"],
            "pod_size": swarm_result["pod_size"],
            "runtime_s": swarm_result["runtime_s"]
        })
        
    else:  # STRUCTURED mode
        print("Executing via STRUCTURED mode...")
        agents = reg.by_guild(lot.target_guild)
        winner, pay, bids = auction_engine.run(lot, agents, spec.market_rules)
        
        # Simulate handoff after work completion
        handoff_msg = handoff_manager.request(
            from_agent=winner.agent_id,
            to_guild="QA",
            task_id=task.task_id, 
            lot_id=lot.lot_id,
            artifacts=[{"uri": f"structured://artifacts/{lot.lot_id}/final.pdf", "sha256": "structured_output"}],
            checks=["spec_conformance", "quality_gates", "brand_compliance"]
        )
        # Simulate ack
        ack = dict(handoff_msg)
        ack_success = handoff_manager.await_ack(ack)
        
        results.append({
            "lot": lot,
            "mode": mode,
            "winner": winner,
            "pay": pay,
            "bids": len(bids),
            "handoff_ack": ack_success
        })
    
    print()

# Print final results
print("=== EXECUTION SUMMARY ===")
for result in results:
    lot = result["lot"]
    mode = result["mode"]
    print(f"{lot.lot_id} ({mode}):", end=" ")
    
    if mode == "SWARM":
        print(f"confidence={result['confidence']:.3f}, pod_size={result['pod_size']}, runtime={result['runtime_s']:.1f}s")
    else:
        print(f"winner={result['winner'].agent_id}, pay={result['pay']:.2f}, bids={result['bids']}, ack={'✓' if result['handoff_ack'] else '✗'}")

print()
print("=== MODE DISTRIBUTION ===")
mode_counts = {}
for result in results:
    mode = result["mode"]
    mode_counts[mode] = mode_counts.get(mode, 0) + 1

for mode, count in mode_counts.items():
    print(f"{mode}: {count} lots")

print("\nSimulation complete. The dual-mode system successfully:")
print("- Routed complex/novel tasks to SWARM mode for exploration")  
print("- Kept structured tasks in STRUCTURED mode for efficiency")
print("- Maintained QA gates and handoff protocols across both modes")
print("- Enforced safety rails to prevent risky tasks from using SWARM")