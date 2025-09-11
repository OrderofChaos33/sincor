#!/usr/bin/env python3
"""
SINCOR Root CLI - God Mode Operations
Usage: python scripts/root.py <command> [args...]
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sincor.god_mode import GodModeController

def main():
    parser = argparse.ArgumentParser(description="SINCOR Root CLI - God Mode Operations")
    parser.add_argument("--principal", default="court@root", help="Principal identity")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # force_mode command
    force_parser = subparsers.add_parser("force_mode", help="Override execution mode for task/lot")
    force_parser.add_argument("target", help="Task or lot ID")
    force_parser.add_argument("mode", choices=["STRUCTURED", "SWARM"], help="Force execution mode")
    
    # seize command  
    seize_parser = subparsers.add_parser("seize", help="Immediately stop and checkpoint task")
    seize_parser.add_argument("task_id", help="Task ID to seize")
    
    # pause command
    pause_parser = subparsers.add_parser("pause", help="Pause guild or market operations")
    pause_parser.add_argument("target", help="Guild name or 'market'")
    
    # emergency_write command
    emergency_parser = subparsers.add_parser("emergency_write", help="Grant temporary external write permission")
    emergency_parser.add_argument("target", help="Target system/resource")
    emergency_parser.add_argument("justification", help="Justification for emergency access")
    
    # audit command
    audit_parser = subparsers.add_parser("audit", help="View recent audit log")
    audit_parser.add_argument("--limit", type=int, default=20, help="Number of entries to show")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load God Mode controller
    config_path = Path(__file__).parent.parent / "config" / "rbac.yaml"
    controller = GodModeController(str(config_path))
    
    try:
        if args.command == "force_mode":
            result = controller.force_mode(args.principal, args.target, args.mode)
            print(f"Force mode result: {result}")
            
        elif args.command == "seize":
            result = controller.seize(args.principal, args.task_id)
            print(f"Seize result: {result}")
            
        elif args.command == "pause":
            result = controller.pause(args.principal, args.target)
            print(f"Pause result: {result}")
            
        elif args.command == "emergency_write":
            result = controller.emergency_write(args.principal, args.target, args.justification)
            print(f"Emergency write result: {result}")
            
        elif args.command == "audit":
            entries = controller.get_audit_log(args.principal, args.limit)
            print(f"=== AUDIT LOG (last {len(entries)} entries) ===")
            for entry in entries:
                status = "✓" if entry["success"] else "✗"
                print(f"{status} {entry['timestamp']:.0f} {entry['principal']} {entry['action']} {entry['target']}")
                if entry["metadata"]:
                    for k, v in entry["metadata"].items():
                        print(f"    {k}: {v}")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main() or 0)