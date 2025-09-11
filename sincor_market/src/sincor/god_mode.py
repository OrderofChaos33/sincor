import time
import yaml
from typing import Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class GodModeAuditLog:
    timestamp: float
    principal: str
    action: str
    target: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True

class GodModeController:
    def __init__(self, rbac_config_path: str):
        self.rbac = yaml.safe_load(Path(rbac_config_path).read_text())
        self.audit_log: List[GodModeAuditLog] = []
        self.cooldowns: Dict[str, float] = {}
        self.blast_radius_counter: Dict[str, int] = {}
    
    def _check_auth(self, principal: str, action: str) -> bool:
        """Check if principal is authorized for action"""
        for role, config in self.rbac["roles"].items():
            if principal in config.get("principals", []) and action in config.get("allow", []):
                return True
        return False
    
    def _check_cooldown(self, principal: str, action: str) -> bool:
        """Check if action is in cooldown period"""
        cooldown_key = f"{principal}:{action}"
        if cooldown_key in self.cooldowns:
            elapsed = time.time() - self.cooldowns[cooldown_key]
            role_config = self._get_role_config(principal)
            if role_config and f"{action}_s" in role_config.get("cooldowns", {}):
                required_cooldown = role_config["cooldowns"][f"{action}_s"]
                if elapsed < required_cooldown:
                    return False
        return True
    
    def _check_blast_radius(self, principal: str, action: str) -> bool:
        """Check blast radius limits"""
        role_config = self._get_role_config(principal)
        if not role_config or "blast_radius" not in role_config:
            return True
        
        minute_key = int(time.time() // 60)
        counter_key = f"{principal}:{minute_key}"
        
        current_count = self.blast_radius_counter.get(counter_key, 0)
        max_lots_per_min = role_config["blast_radius"].get("max_lots_per_min", float('inf'))
        
        return current_count < max_lots_per_min
    
    def _get_role_config(self, principal: str) -> Dict[str, Any]:
        """Get role configuration for principal"""
        for role, config in self.rbac["roles"].items():
            if principal in config.get("principals", []):
                return config
        return {}
    
    def _log_action(self, principal: str, action: str, target: str, metadata: Dict[str, Any] = None, success: bool = True):
        """Log action to audit trail"""
        log_entry = GodModeAuditLog(
            timestamp=time.time(),
            principal=principal,
            action=action,
            target=target,
            metadata=metadata or {},
            success=success
        )
        self.audit_log.append(log_entry)
        
        # Update counters and cooldowns if successful
        if success:
            cooldown_key = f"{principal}:{action}"
            self.cooldowns[cooldown_key] = time.time()
            
            minute_key = int(time.time() // 60)
            counter_key = f"{principal}:{minute_key}"
            self.blast_radius_counter[counter_key] = self.blast_radius_counter.get(counter_key, 0) + 1
    
    def force_mode(self, principal: str, target: str, mode: str) -> Dict[str, Any]:
        """Force execution mode for task or lot"""
        action = "force_mode"
        
        if not self._check_auth(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Unauthorized"}
        
        if not self._check_cooldown(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Action in cooldown"}
        
        if not self._check_blast_radius(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Blast radius limit exceeded"}
        
        metadata = {"forced_mode": mode}
        self._log_action(principal, action, target, metadata)
        
        return {"success": True, "target": target, "mode": mode, "timestamp": time.time()}
    
    def seize(self, principal: str, task_id: str) -> Dict[str, Any]:
        """Immediate stop and checkpoint task"""
        action = "seize"
        
        if not self._check_auth(principal, action):
            self._log_action(principal, action, task_id, success=False)
            return {"success": False, "error": "Unauthorized"}
        
        if not self._check_blast_radius(principal, action):
            self._log_action(principal, action, task_id, success=False)
            return {"success": False, "error": "Blast radius limit exceeded"}
        
        metadata = {"seized_at": time.time()}
        self._log_action(principal, action, task_id, metadata)
        
        return {"success": True, "task_id": task_id, "status": "seized", "checkpoint": "mem://checkpoints/seized"}
    
    def pause(self, principal: str, target: str) -> Dict[str, Any]:
        """Pause guild or market operations"""
        action = "pause"
        
        if not self._check_auth(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Unauthorized"}
        
        if not self._check_blast_radius(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Blast radius limit exceeded"}
        
        metadata = {"paused_at": time.time()}
        self._log_action(principal, action, target, metadata)
        
        return {"success": True, "target": target, "status": "paused", "drain_time_s": 30}
    
    def emergency_write(self, principal: str, target: str, justification: str) -> Dict[str, Any]:
        """Temporary allowance for blocked external write"""
        action = "emergency_write"
        
        if not self._check_auth(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Unauthorized"}
        
        if not self._check_cooldown(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Action in cooldown"}
        
        if not self._check_blast_radius(principal, action):
            self._log_action(principal, action, target, success=False)
            return {"success": False, "error": "Blast radius limit exceeded"}
        
        metadata = {"justification": justification, "granted_at": time.time()}
        self._log_action(principal, action, target, metadata)
        
        return {
            "success": True,
            "target": target,
            "permission": "external_write",
            "expires_at": time.time() + 300,  # 5 minute window
            "justification": justification
        }
    
    def get_audit_log(self, principal: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries"""
        if not self._check_auth(principal, "seize"):  # Use seize as proxy for admin access
            return []
        
        recent_entries = sorted(self.audit_log, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                "timestamp": entry.timestamp,
                "principal": entry.principal,
                "action": entry.action,
                "target": entry.target,
                "success": entry.success,
                "metadata": entry.metadata if not self.rbac["audit"]["redact_artifacts"] else {}
            }
            for entry in recent_entries
        ]