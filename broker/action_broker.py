#!/usr/bin/env python3
"""
SINCOR Action Broker - Compliance Gateway
Routes all agent actions through policy compliance checks
"""
import yaml
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActionBroker:
    def __init__(self, policy_file="policy/allowed_actions.yml"):
        self.policy_file = policy_file
        self.policy = self.load_policy()
        self.action_log = []
        
    def load_policy(self) -> Dict[str, Any]:
        """Load compliance policy from YAML file"""
        try:
            with open(self.policy_file, 'r') as f:
                policy = yaml.safe_load(f)
            logger.info(f"Loaded policy from {self.policy_file}")
            return policy
        except FileNotFoundError:
            logger.error(f"Policy file {self.policy_file} not found")
            return self.get_default_policy()
        except Exception as e:
            logger.error(f"Error loading policy: {e}")
            return self.get_default_policy()
    
    def get_default_policy(self) -> Dict[str, Any]:
        """Return default safe policy if file not found"""
        return {
            "defaults": {
                "mode": "SAFE_MODE",
                "dry_run": True,
                "logging": True,
                "max_output_size": "5MB",
                "require_codeowners": True
            },
            "actions": [],
            "denied_patterns": ["api.paypal.com", "PAYPAL_MODE=live", "*.sh", "*.exe"]
        }
    
    def check_action_allowed(self, action_name: str, target_path: str = None, **kwargs) -> Dict[str, Any]:
        """Check if action is allowed by policy"""
        
        # Log the action attempt
        action_attempt = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action_name,
            "target_path": target_path,
            "kwargs": kwargs,
            "status": "checking"
        }
        
        # Check denied patterns first
        if self.is_denied_pattern(action_name, target_path, kwargs):
            action_attempt["status"] = "BLOCKED_BY_POLICY"
            action_attempt["reason"] = "Matches denied pattern"
            self.action_log.append(action_attempt)
            logger.warning(f"BLOCKED BY POLICY: {action_name} - {action_attempt['reason']}")
            return {
                "allowed": False,
                "reason": "Action blocked by compliance policy",
                "details": action_attempt
            }
        
        # Check if action is explicitly allowed
        allowed_action = self.find_allowed_action(action_name, target_path)
        
        if not allowed_action:
            action_attempt["status"] = "BLOCKED_BY_POLICY"
            action_attempt["reason"] = "Action not in whitelist"
            self.action_log.append(action_attempt)
            logger.warning(f"BLOCKED BY POLICY: {action_name} not in allowed actions")
            return {
                "allowed": False,
                "reason": "Action not explicitly allowed in policy",
                "details": action_attempt
            }
        
        # Check action limits
        limit_check = self.check_action_limits(allowed_action, target_path, kwargs)
        if not limit_check["allowed"]:
            action_attempt["status"] = "BLOCKED_BY_LIMITS"
            action_attempt["reason"] = limit_check["reason"]
            self.action_log.append(action_attempt)
            logger.warning(f"BLOCKED BY LIMITS: {action_name} - {limit_check['reason']}")
            return limit_check
        
        # Action is allowed
        action_attempt["status"] = "APPROVED"
        self.action_log.append(action_attempt)
        logger.info(f"APPROVED: {action_name}")
        
        return {
            "allowed": True,
            "action_config": allowed_action,
            "details": action_attempt
        }
    
    def is_denied_pattern(self, action_name: str, target_path: Optional[str], kwargs: Dict[str, Any]) -> bool:
        """Check if action matches any denied pattern"""
        denied_patterns = self.policy.get("denied_patterns", [])
        
        # Check action name against patterns
        for pattern in denied_patterns:
            if pattern in action_name:
                return True
            
            # Check target path
            if target_path and pattern in target_path:
                return True
            
            # Check kwargs values
            for key, value in kwargs.items():
                if isinstance(value, str) and pattern in value:
                    return True
        
        return False
    
    def find_allowed_action(self, action_name: str, target_path: Optional[str]) -> Optional[Dict[str, Any]]:
        """Find matching allowed action in policy"""
        actions = self.policy.get("actions", [])
        
        for action in actions:
            if action.get("name") == action_name:
                # Check if target path matches allowed paths
                if target_path:
                    allowed_paths = action.get("paths", [])
                    if not any(target_path.startswith(path) for path in allowed_paths):
                        continue
                
                return action
        
        return None
    
    def check_action_limits(self, action_config: Dict[str, Any], target_path: Optional[str], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Check if action is within configured limits"""
        limits = action_config.get("limits", {})
        
        # Check max files limit
        if "max_files" in limits:
            # This would need to be implemented based on actual file system checks
            pass
        
        # Check file types
        if "file_types" in limits and target_path:
            allowed_types = limits["file_types"]
            file_ext = os.path.splitext(target_path)[1]
            if file_ext not in allowed_types:
                return {
                    "allowed": False,
                    "reason": f"File type {file_ext} not in allowed types: {allowed_types}"
                }
        
        # Check external calls
        if not limits.get("external_calls", True):
            # Check if action involves external calls
            external_indicators = ["http", "api", "curl", "wget", "requests"]
            action_str = str(kwargs)
            if any(indicator in action_str.lower() for indicator in external_indicators):
                return {
                    "allowed": False,
                    "reason": "External calls not permitted for this action"
                }
        
        return {"allowed": True}
    
    def execute_safe_action(self, action_name: str, target_path: str = None, **kwargs) -> Dict[str, Any]:
        """Execute action through compliance broker"""
        
        # Check if action is allowed
        permission_check = self.check_action_allowed(action_name, target_path, **kwargs)
        
        if not permission_check["allowed"]:
            return {
                "status": "blocked",
                "error": permission_check["reason"],
                "details": permission_check["details"]
            }
        
        # In SAFE_MODE, don't actually execute - just log and return success
        if self.policy.get("defaults", {}).get("dry_run", True):
            logger.info(f"DRY_RUN: Would execute {action_name} on {target_path}")
            return {
                "status": "dry_run_success",
                "action": action_name,
                "target": target_path,
                "message": "Action approved but not executed in DRY_RUN mode"
            }
        
        # If not dry_run, this is where actual action execution would happen
        logger.info(f"EXECUTING: {action_name} on {target_path}")
        return {
            "status": "executed",
            "action": action_name,
            "target": target_path
        }
    
    def get_action_log(self) -> List[Dict[str, Any]]:
        """Get log of all action attempts"""
        return self.action_log
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        total_actions = len(self.action_log)
        approved_actions = len([a for a in self.action_log if a["status"] == "APPROVED"])
        blocked_actions = len([a for a in self.action_log if "BLOCKED" in a["status"]])
        
        return {
            "compliance_summary": {
                "total_action_attempts": total_actions,
                "approved_actions": approved_actions,
                "blocked_actions": blocked_actions,
                "approval_rate": f"{(approved_actions/total_actions*100):.1f}%" if total_actions > 0 else "N/A"
            },
            "policy_status": {
                "policy_file": self.policy_file,
                "mode": self.policy.get("defaults", {}).get("mode", "UNKNOWN"),
                "dry_run_enabled": self.policy.get("defaults", {}).get("dry_run", True)
            },
            "recent_actions": self.action_log[-10:],  # Last 10 actions
            "blocked_patterns_triggered": [
                a for a in self.action_log if "BLOCKED" in a["status"]
            ][-5:]  # Last 5 blocked actions
        }

# Example usage and testing
if __name__ == "__main__":
    print("SINCOR Action Broker - Compliance Gateway")
    print("Testing compliance policy enforcement...")
    
    broker = ActionBroker()
    
    # Test allowed action
    result1 = broker.execute_safe_action("create_ads", "ads/sample.json")
    print(f"Create ads: {result1['status']}")
    
    # Test blocked action  
    result2 = broker.execute_safe_action("delete_system", "/system/critical.sh")
    print(f"Delete system: {result2['status']}")
    
    # Test denied pattern
    result3 = broker.execute_safe_action("connect_paypal", "api.paypal.com/live")
    print(f"Connect PayPal: {result3['status']}")
    
    # Generate compliance report
    report = broker.get_compliance_report()
    print(f"\nCompliance Report:")
    print(f"- Total actions: {report['compliance_summary']['total_action_attempts']}")
    print(f"- Approved: {report['compliance_summary']['approved_actions']}")
    print(f"- Blocked: {report['compliance_summary']['blocked_actions']}")
    print(f"- Approval rate: {report['compliance_summary']['approval_rate']}")