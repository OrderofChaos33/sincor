from pathlib import Path
import yaml
import time
import random
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sincor.agents import AgentRegistry
from sincor.task import TaskToken, Lot, AuctionSpec
from sincor.monetized_auction import MonetizedAuctionEngine, MonetizedBid
from sincor.mode_select import choose_mode, Signal
from sincor.swarm import SwarmAdapter
from sincor.handoff import HandoffManager
from sincor.monetization_logger import MonetizationLogger
from sincor.client import Client


def simulate_monetized_sincor():
    """Comprehensive simulation with full monetization integration"""
    
    print("=== SINCOR MONETIZED SYSTEM SIMULATION ===")
    print("Dual-mode execution with pricing, revenue optimization, and value creation")
    print()
    
    # Initialize system components
    root = Path(".")
    
    # Load configurations
    reg = AgentRegistry.load(str(root/"config/agents.yaml"), str(root/"config/taxonomy.yaml"))
    mode_policy = yaml.safe_load((root/"config/mode_policy.yaml").read_text())
    
    # Initialize monetized auction engine
    monetized_engine = MonetizedAuctionEngine(
        taxonomy=reg.taxonomy,
        monetization_config=str(root/"config/monetization.yaml"),
        clients_config=str(root/"config/clients.yaml"), 
        value_graph_config=str(root/"config/value_graph.yaml"),
        value_policy_config=str(root/"config/value_policy.yaml")
    )
    
    # Initialize other components
    swarm_adapter = SwarmAdapter(mode_policy)
    handoff_manager = HandoffManager(T_ack_s=5)
    logger = MonetizationLogger(enable_console=False)  # Disable console spam
    
    print(f"[OK] Loaded {len(reg.agents)} agents across 6 guilds")
    print(f"[OK] Initialized monetization engine with segment-based pricing")
    print(f"[OK] Value logic system ready for derivative task creation")
    print()
    
    # Define diverse client scenarios
    test_clients = [
        {"id": "client_001", "segment": "enterprise", "expected_mode": "STRUCTURED"},
        {"id": "client_101", "segment": "sme", "expected_mode": "SWARM"},  # Novel task
        {"id": "client_201", "segment": "startup", "expected_mode": "SWARM"},  # Creative task
        {"id": "client_301", "segment": "nonprofit", "expected_mode": "STRUCTURED"},  # Safety-critical
    ]
    
    # Define test scenarios with different characteristics
    scenarios = [
        {
            "task_id": "TT-2025-ENT-001",
            "client": test_clients[0],
            "intent": "Enterprise data pipeline audit and optimization",
            "lots": [
                Lot(lot_id="L1", scope="Security audit + compliance check", target_guild="QA",
                    required_skills={"qa-auto":0.8,"legal-compliance":0.7}, budget=150, deadline_s=3600*8),
            ],
            "product_type": "report",
            "risk": {"pii": True, "ext_write": False, "legal_hold": True},
            "expected_signals": {"novelty": 0.2, "ambiguity": 0.3, "time_pressure": 0.4, "externality": 0.3, "exploration_budget": 0.1, "safety_risk": 0.8}
        },
        {
            "task_id": "TT-2025-SME-001", 
            "client": test_clients[1],
            "intent": "AI-powered creative campaign for local restaurant",
            "lots": [
                Lot(lot_id="L2", scope="Brand strategy + creative concepts", target_guild="PROD",
                    required_skills={"design":0.7,"copy":0.6,"synthesis":0.8}, budget=80, deadline_s=3600*6),
            ],
            "product_type": "media_pack",
            "risk": {"pii": False, "ext_write": False},
            "expected_signals": {"novelty": 0.9, "ambiguity": 0.8, "time_pressure": 0.6, "externality": 0.2, "exploration_budget": 0.4, "safety_risk": 0.1}
        },
        {
            "task_id": "TT-2025-STARTUP-001",
            "client": test_clients[2], 
            "intent": "MVP prototype and go-to-market strategy",
            "lots": [
                Lot(lot_id="L3", scope="Product prototype + market analysis", target_guild="PROD", 
                    required_skills={"codegen":0.8,"data-clean":0.6,"synthesis":0.7}, budget=60, deadline_s=3600*4),
            ],
            "product_type": "code_module",
            "risk": {"pii": False, "ext_write": True},
            "expected_signals": {"novelty": 0.7, "ambiguity": 0.9, "time_pressure": 0.8, "externality": 0.4, "exploration_budget": 0.3, "safety_risk": 0.3}
        },
        {
            "task_id": "TT-2025-NONPROFIT-001",
            "client": test_clients[3],
            "intent": "Donor management system with compliance tracking", 
            "lots": [
                Lot(lot_id="L4", scope="Database design + privacy controls", target_guild="PROD",
                    required_skills={"codegen":0.7,"legal-compliance":0.8,"ops-deploy":0.6}, budget=40, deadline_s=3600*12),
            ],
            "product_type": "template",
            "risk": {"pii": True, "ext_write": False, "legal_hold": False},
            "expected_signals": {"novelty": 0.3, "ambiguity": 0.4, "time_pressure": 0.3, "externality": 0.2, "exploration_budget": 0.1, "safety_risk": 0.6}
        }
    ]
    
    results = []
    total_revenue = 0
    total_margin = 0
    
    print("--- PROCESSING SCENARIOS ---")
    
    for i, scenario in enumerate(scenarios, 1):
        client_info = scenario["client"]
        client_id = client_info["id"]
        
        print(f"\n[Scenario {i}] Client: {client_id} ({client_info['segment'].upper()})")
        print(f"Task: {scenario['intent']}")
        
        # Create task token
        task = TaskToken(
            task_id=scenario["task_id"],
            origin="demo",
            intent=scenario["intent"],
            spec={"acceptance": ["quality>=0.8", "on_time", "budget_compliant"]},
            budget={"hard": sum(lot.budget for lot in scenario["lots"]), "soft": sum(lot.budget for lot in scenario["lots"]) * 0.8, "currency": "USD"},
            deadline_unix=int(time.time()) + min(lot.deadline_s for lot in scenario["lots"]),
            priority=0.75,
            risk=scenario["risk"]
        )
        
        for lot in scenario["lots"]:
            # Compute mode selection signals
            signals = scenario["expected_signals"]
            signal = Signal(**signals)
            
            # Choose execution mode
            mode = choose_mode(signal, mode_policy)
            print(f"  Mode: {mode} (novelty={signals['novelty']:.1f}, safety_risk={signals['safety_risk']:.1f})")
            
            if mode == "SWARM":
                # SWARM execution
                print("  Executing via SWARM mode...")
                swarm_result = swarm_adapter.run(lot, mem=None, tools=None)
                
                # Generate pricing for SWARM result
                client = monetized_engine.get_client(client_id)
                base_cost = monetized_engine.estimate_base_cost(lot, reg.by_guild(lot.target_guild))
                
                quote = monetized_engine.pricing_engine.quote(
                    base_cost=base_cost,
                    segment=client.segment,
                    hours_to_deadline=monetized_engine.hours_to_deadline(lot),
                    system_load=monetized_engine.current_system_load(),
                    risk=scenario["risk"],
                    ab_variant=True
                )
                
                # Log SWARM result
                logger.log_swarm_result(lot.lot_id, client_id, swarm_result, quote)
                
                print(f"  SWARM Result: confidence={swarm_result['confidence']:.3f}, pod_size={swarm_result['pod_size']}")
                print(f"  Pricing: ${quote.price:.2f} (margin: ${quote.margin_absolute:.2f}, {quote.margin_percentage*100:.1f}%)")
                
                total_revenue += quote.price
                total_margin += quote.margin_absolute
                
                results.append({
                    "scenario": i,
                    "client": client_id,
                    "segment": client_info["segment"],
                    "mode": mode,
                    "lot_id": lot.lot_id,
                    "price": quote.price,
                    "margin": quote.margin_absolute,
                    "confidence": swarm_result["confidence"],
                    "execution_time": swarm_result.get("runtime_s", 0)
                })
                
            else:
                # STRUCTURED execution with full monetization
                print("  Executing via STRUCTURED mode with monetization...")
                
                try:
                    agents = reg.by_guild(lot.target_guild)
                    winner, pay, bids, quote = monetized_engine.run_with_monetization(
                        lot=lot,
                        agents=agents,
                        client_id=client_id,
                        rules={"T_bidding_s": 3, "T_ack_s": 5}
                    )
                    
                    # Log auction result
                    logger.log_auction_result(lot.lot_id, winner, pay, len(bids), quote, client_id, mode)
                    
                    print(f"  Winner: {winner.agent_id} (score={winner.score:.3f})")
                    print(f"  Pricing: ${quote.price:.2f} -> Provider: ${pay:.2f} -> Margin: ${quote.price-pay:.2f}")
                    print(f"  Segment pricing applied: {winner.segment} (weight: {winner.strategic_weight:.1f})")
                    
                    total_revenue += quote.price
                    total_margin += quote.price - pay
                    
                    results.append({
                        "scenario": i,
                        "client": client_id,
                        "segment": client_info["segment"],
                        "mode": mode,
                        "lot_id": lot.lot_id,
                        "winner": winner.agent_id,
                        "price": quote.price,
                        "provider_cost": pay,
                        "margin": quote.price - pay,
                        "bids": len(bids)
                    })
                    
                except RuntimeError as e:
                    print(f"  [WARN] Auction failed: {e}")
                    continue
            
            # Simulate task completion and value creation
            if random.random() > 0.2:  # 80% success rate
                print("  [SUCCESS] Task completed successfully")
                
                # Handle value creation
                artifacts = [{"uri": f"artifact://{lot.lot_id}/final", "type": scenario["product_type"]}]
                value_result = monetized_engine.handle_completion(
                    task_id=task.task_id,
                    product_type=scenario["product_type"],
                    scope=lot.scope,
                    artifacts=artifacts,
                    confidence=0.85
                )
                
                derivatives_count = len(value_result["derivatives"])
                feedback_count = len(value_result["feedback_signals"])
                
                if derivatives_count > 0:
                    print(f"  [VALUE] Created: {derivatives_count} derivatives, {feedback_count} feedback signals")
                    logger.log_value_creation(task.task_id, scenario["product_type"], derivatives_count, feedback_count)
                
                # Log conversion
                logger.log_conversion(task.task_id, client_id, True, quote.price if 'quote' in locals() else 0)
            else:
                print("  [FAILED] Task failed - client abandonment")
                logger.log_conversion(task.task_id, client_id, False, 0, "quality_issues")
    
    # Generate comprehensive summary
    print("\n" + "="*60)
    print("MONETIZED SINCOR SIMULATION RESULTS")
    print("="*60)
    
    # Financial summary
    avg_margin_pct = (total_margin / max(1, total_revenue)) * 100
    print(f"\n[FINANCIAL PERFORMANCE]")
    print(f"   Total Revenue: ${total_revenue:.2f}")
    print(f"   Total Margin:  ${total_margin:.2f}")
    print(f"   Avg Margin %:  {avg_margin_pct:.1f}%")
    
    # Mode distribution
    structured_count = len([r for r in results if r["mode"] == "STRUCTURED"])
    swarm_count = len([r for r in results if r["mode"] == "SWARM"])
    
    print(f"\n[EXECUTION MODES]")
    print(f"   STRUCTURED: {structured_count} tasks ({structured_count/max(1,len(results))*100:.0f}%)")
    print(f"   SWARM:      {swarm_count} tasks ({swarm_count/max(1,len(results))*100:.0f}%)")
    
    # Segment performance
    segment_stats = {}
    for result in results:
        seg = result["segment"]
        if seg not in segment_stats:
            segment_stats[seg] = {"tasks": 0, "revenue": 0, "margin": 0}
        segment_stats[seg]["tasks"] += 1
        segment_stats[seg]["revenue"] += result["price"]
        segment_stats[seg]["margin"] += result.get("margin", 0)
    
    print(f"\n[SEGMENT BREAKDOWN]")
    for segment, stats in segment_stats.items():
        avg_price = stats["revenue"] / max(1, stats["tasks"])
        avg_margin = stats["margin"] / max(1, stats["tasks"])
        margin_pct = (stats["margin"] / max(1, stats["revenue"])) * 100
        print(f"   {segment.upper():>10}: {stats['tasks']} tasks, avg ${avg_price:.0f}, {margin_pct:.1f}% margin")
    
    # Generate detailed logs summary
    revenue_summary = logger.log_revenue_summary(period_hours=1)  # Last hour
    
    print(f"\n[SYSTEM METRICS]")
    print(f"   Conversion Rate: {revenue_summary['metrics']['conversion_rate_pct']:.1f}%")
    print(f"   Tasks Completed: {revenue_summary['metrics']['total_tasks_completed']}")
    print(f"   Quotes Generated: {revenue_summary['metrics']['total_quotes_generated']}")
    
    # Revenue optimization insights
    print(f"\n[OPTIMIZATION INSIGHTS]")
    if avg_margin_pct > 25:
        print("   [OK] Healthy margins - pricing strategy effective")
    else:
        print("   [WARN] Low margins - consider adjusting segment multipliers")
    
    if swarm_count > 0:
        print("   [OK] SWARM mode successfully handling creative/novel tasks")
    
    if structured_count > 0:
        print("   [OK] STRUCTURED mode maintaining efficiency for standard work")
    
    print(f"\n[COMPLETE] Monetized SINCOR system operational!")
    print(f"   System successfully integrated: pricing, auctions, value creation, dual-mode execution")
    print(f"   Revenue per task: ${total_revenue/max(1,len(results)):.2f}")
    print(f"   Ready for production deployment!")
    
    return {
        "total_revenue": total_revenue,
        "total_margin": total_margin,
        "tasks_completed": len(results),
        "mode_distribution": {"structured": structured_count, "swarm": swarm_count},
        "segment_performance": segment_stats,
        "logger": logger
    }

if __name__ == "__main__":
    # Run the comprehensive simulation
    simulation_results = simulate_monetized_sincor()