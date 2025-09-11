from dataclasses import dataclass
from typing import Dict, Any, Optional
import yaml
from pathlib import Path

@dataclass
class Client:
    client_id: str
    segment: str = "sme"
    strategic_weight: float = 1.0
    ltv_score: int = 50
    contract_type: str = "monthly"
    sla_tier: str = "standard"
    
    @classmethod
    def load_from_config(cls, client_id: str, config_path: str) -> "Client":
        """Load client configuration from YAML file"""
        config = yaml.safe_load(Path(config_path).read_text())
        
        if client_id in config.get("clients", {}):
            client_data = config["clients"][client_id]
            return cls(client_id=client_id, **client_data)
        else:
            # Use segment defaults for unknown clients
            defaults = config.get("segment_defaults", {}).get("sme", {})
            return cls(client_id=client_id, **defaults)
    
    @property 
    def is_enterprise(self) -> bool:
        return self.segment == "enterprise"
    
    @property
    def is_high_value(self) -> bool:
        return self.ltv_score >= 80 or self.strategic_weight >= 1.3
    
    @property
    def needs_premium_sla(self) -> bool:
        return self.sla_tier == "premium"