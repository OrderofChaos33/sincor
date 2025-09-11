"""
SINCOR Production Orchestrator
Unified startup system for monetized SINCOR with all engines integrated
"""
import time
import threading
import logging
import yaml
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import all our production-ready components
from .monetization import PricingEngine, RevenuePriority
from .monetized_auction import MonetizedAuctionEngine
from .value_logic import ValueLogic
from .monetization_logger import MonetizationLogger
from .client import Client
from .agents import AgentRegistry
from .god_mode import GodModeController

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SINCOR Production API",
    description="Monetized AI Business Automation Platform",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system components
monetized_engine = None
value_logic = None
mon_logger = None
god_mode = None
agent_registry = None

def initialize_system():
    """Initialize all SINCOR system components"""
    global monetized_engine, value_logic, mon_logger, god_mode, agent_registry
    
    try:
        logger.info("🚀 Initializing SINCOR Production System...")
        
        # Determine config paths (Railway deployment vs local)
        config_base = Path("config")
        if not config_base.exists():
            config_base = Path("sincor_market/config")
        if not config_base.exists():
            config_base = Path(".")
        
        # Initialize agent registry
        agents_path = config_base / "agents.yaml"
        taxonomy_path = config_base / "taxonomy.yaml"
        
        if agents_path.exists() and taxonomy_path.exists():
            agent_registry = AgentRegistry.load(str(agents_path), str(taxonomy_path))
            logger.info(f"✅ Loaded {len(agent_registry.agents)} agents across 6 guilds")
        else:
            logger.warning("⚠️ Agent configuration not found, using minimal setup")
            agent_registry = AgentRegistry()
        
        # Initialize monetized auction engine
        monetization_config = config_base / "monetization.yaml"
        clients_config = config_base / "clients.yaml" 
        value_graph_config = config_base / "value_graph.yaml"
        value_policy_config = config_base / "value_policy.yaml"
        
        if all(p.exists() for p in [monetization_config, clients_config]):
            monetized_engine = MonetizedAuctionEngine(
                taxonomy=agent_registry.taxonomy if agent_registry.taxonomy else ["research", "synthesis", "codegen"],
                monetization_config=str(monetization_config),
                clients_config=str(clients_config),
                value_graph_config=str(value_graph_config) if value_graph_config.exists() else "",
                value_policy_config=str(value_policy_config) if value_policy_config.exists() else ""
            )
            logger.info("✅ Monetized auction engine initialized")
        else:
            logger.warning("⚠️ Monetization configs not found, running in basic mode")
        
        # Initialize value logic
        if value_graph_config.exists() and value_policy_config.exists():
            value_logic = ValueLogic(str(value_graph_config), str(value_policy_config))
            logger.info("✅ Value logic system initialized")
        
        # Initialize monetization logger
        mon_logger = MonetizationLogger(enable_console=True)
        logger.info("✅ Monetization logging initialized")
        
        # Initialize God Mode (if RBAC config exists)
        rbac_config = config_base / "rbac.yaml"
        if rbac_config.exists():
            god_mode = GodModeController(str(rbac_config))
            logger.info("✅ God Mode controls initialized")
        
        logger.info("🎉 SINCOR Production System fully initialized!")
        return True
        
    except Exception as e:
        logger.error(f"❌ System initialization failed: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event"""
    success = initialize_system()
    if not success:
        logger.error("Failed to initialize system - check configuration")

@app.get("/")
async def root():
    return {
        "message": "SINCOR Production API",
        "status": "operational",
        "version": "3.0.0",
        "features": [
            "Monetized auctions",
            "Dual-mode execution (STRUCTURED/SWARM)", 
            "Value creation system",
            "43-agent constellation",
            "Revenue optimization",
            "God Mode controls"
        ]
    }

@app.get("/healthz")
async def health_check():
    """Health check endpoint for Railway/k8s"""
    system_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "monetized_engine": monetized_engine is not None,
            "value_logic": value_logic is not None,
            "agent_registry": agent_registry is not None and len(agent_registry.agents) > 0,
            "logger": mon_logger is not None,
            "god_mode": god_mode is not None
        }
    }
    
    if all(system_status["components"].values()):
        return system_status
    else:
        raise HTTPException(status_code=503, detail=system_status)

@app.get("/metrics")
async def get_metrics():
    """Get system performance metrics"""
    if not monetized_engine:
        raise HTTPException(status_code=503, detail="Monetization engine not initialized")
    
    metrics = monetized_engine.get_revenue_metrics()
    return {
        "revenue_metrics": metrics,
        "system_uptime": time.time(),
        "agents_loaded": len(agent_registry.agents) if agent_registry else 0
    }

@app.post("/quote")
async def generate_quote(client_id: str, base_cost: float, segment: str = "sme"):
    """Generate a pricing quote"""
    if not monetized_engine:
        raise HTTPException(status_code=503, detail="Monetization engine not initialized")
    
    try:
        client = monetized_engine.get_client(client_id)
        
        quote = monetized_engine.pricing_engine.quote(
            base_cost=base_cost,
            segment=segment,
            hours_to_deadline=8.0,  # Default 8 hours
            system_load=0.6,        # Default medium load
            risk={},
            ab_variant=True
        )
        
        return {
            "quote": {
                "price": quote.price,
                "base_cost": quote.base_cost,
                "margin": quote.margin_absolute,
                "margin_pct": quote.margin_percentage * 100,
                "segment": segment,
                "notes": quote.notes
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/god_mode/{action}")
async def god_mode_action(action: str, principal: str = "court@root", target: str = "", **kwargs):
    """God Mode controls for emergency operations"""
    if not god_mode:
        raise HTTPException(status_code=503, detail="God Mode not initialized")
    
    try:
        if action == "force_mode":
            mode = kwargs.get("mode", "STRUCTURED")
            result = god_mode.force_mode(principal, target, mode)
        elif action == "seize":
            result = god_mode.seize(principal, target)
        elif action == "pause":
            result = god_mode.pause(principal, target)
        elif action == "emergency_write":
            justification = kwargs.get("justification", "Emergency access required")
            result = god_mode.emergency_write(principal, target, justification)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def start_background_services():
    """Start background monitoring and value creation services"""
    
    def monetization_monitor():
        """Monitor monetization performance"""
        logger.info("💰 Monetization monitor started")
        while True:
            try:
                if mon_logger and monetized_engine:
                    # Generate periodic revenue summaries
                    summary = mon_logger.log_revenue_summary(period_hours=24)
                    if summary["metrics"]["total_tasks_completed"] > 0:
                        logger.info(f"Revenue Summary: ${summary['metrics']['total_revenue']:.2f} from {summary['metrics']['total_tasks_completed']} tasks")
            except Exception as e:
                logger.error(f"Monetization monitor error: {e}")
            time.sleep(3600)  # Check every hour
    
    def value_creation_monitor():
        """Monitor value creation and derivative spawning"""
        logger.info("📈 Value creation monitor started")
        while True:
            try:
                # In production, this would listen for completion events
                # and spawn derivative tasks automatically
                pass
            except Exception as e:
                logger.error(f"Value creation monitor error: {e}")
            time.sleep(300)  # Check every 5 minutes
    
    def system_supervisor():
        """High-level system health monitoring"""
        logger.info("🔍 System supervisor started")
        while True:
            try:
                # Monitor agent health, auction performance, revenue trends
                # Escalate issues or auto-adjust parameters as needed
                if monetized_engine:
                    metrics = monetized_engine.get_revenue_metrics()
                    recent_margin = metrics.get("avg_margin_pct", 0)
                    
                    # Alert if margins drop too low
                    if recent_margin < 10 and metrics.get("total_records", 0) > 5:
                        logger.warning(f"⚠️ Low margin alert: {recent_margin:.1f}%")
                
            except Exception as e:
                logger.error(f"System supervisor error: {e}")
            time.sleep(1800)  # Check every 30 minutes
    
    # Start background threads
    threading.Thread(target=monetization_monitor, daemon=True).start()
    threading.Thread(target=value_creation_monitor, daemon=True).start() 
    threading.Thread(target=system_supervisor, daemon=True).start()
    
    logger.info("🔧 All background services started")

if __name__ == "__main__":
    # Start background services
    start_background_services()
    
    # Get port from environment (Railway sets this)
    import os
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"🚀 Starting SINCOR Production API on port {port}")
    
    # Start the FastAPI server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )