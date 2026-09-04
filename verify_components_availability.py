#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify critical components availability
Check if key components for scenarios 1, 2, 3 are truly available
"""

import sys
import os

def test_causal_availability():
    """Test causal analysis component availability"""
    try:
        from core.analysis.l2.enhanced_causal_analyzer import CAUSAL_AVAILABLE
        print(f"CAUSAL_AVAILABLE: {CAUSAL_AVAILABLE}")
        
        if CAUSAL_AVAILABLE:
            from core.analysis.l2.enhanced_causal_analyzer import (
                CausalGraph, CausalEdge, CausalStrength
            )
            print("[OK] Causal analysis components fully available")
            return True
        else:
            print("[FAIL] Causal analysis components in degraded mode")
            return False
    except Exception as e:
        print(f"[FAIL] Causal analysis components import failed: {e}")
        return False

def test_hitl_availability():
    """Test HITL component availability"""
    try:
        from api.hitl_router import HITL_AVAILABLE
        print(f"HITL_AVAILABLE: {HITL_AVAILABLE}")
        
        if HITL_AVAILABLE:
            from core.hitl import (
                ApprovalWorkflow, MultiLevelApprover, ConditionalApproval
            )
            print("[OK] HITL components fully available")
            return True
        else:
            print("[FAIL] HITL components in degraded mode")
            return False
    except Exception as e:
        print(f"[FAIL] HITL components import failed: {e}")
        return False

def test_webhook_availability():
    """Test Webhook component availability"""
    try:
        from api.alert_webhook_router import PROCESS_AVAILABLE, AUTO_HEAL_AVAILABLE
        print(f"PROCESS_AVAILABLE: {PROCESS_AVAILABLE}")
        print(f"AUTO_HEAL_AVAILABLE: {AUTO_HEAL_AVAILABLE}")
        
        if PROCESS_AVAILABLE and AUTO_HEAL_AVAILABLE:
            print("[OK] Webhook and auto-heal components fully available")
            return True
        else:
            print("[FAIL] Webhook or auto-heal components in degraded mode")
            return False
    except Exception as e:
        print(f"[FAIL] Webhook components import failed: {e}")
        return False

def test_workflow_availability():
    """Test workflow component availability"""
    try:
        from core.workflow.engine import (
            WorkflowDSL, parse_yaml_workflow, parse_json_workflow
        )
        print("[OK] Workflow DSL components fully available")
        return True
    except Exception as e:
        print(f"[FAIL] Workflow DSL components import failed: {e}")
        return False

def test_subagent_availability():
    """Test subagent component availability"""
    try:
        from core.agent.subagent import SubAgentDispatcher
        print("[OK] Subagent dispatcher components fully available")
        return True
    except Exception as e:
        print(f"[FAIL] Subagent dispatcher components import failed: {e}")
        return False

def test_natural_language_availability():
    """Test natural language processing component availability"""
    try:
        from core.chat_command_handler import parse_chat_command
        print("[OK] Natural language processing components fully available")
        return True
    except Exception as e:
        print(f"[FAIL] Natural language processing components import failed: {e}")
        return False

def test_rollback_availability():
    """Test rollback component availability"""
    try:
        from services.repair_service.rollback import RollbackEngine
        print("[OK] Rollback engine components fully available")
        return True
    except Exception as e:
        print(f"[FAIL] Rollback engine components import failed: {e}")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("Critical Components Availability Verification")
    print("=" * 60)
    
    results = {
        "Causal Analysis": test_causal_availability(),
        "HITL": test_hitl_availability(),
        "Webhook": test_webhook_availability(),
        "Workflow DSL": test_workflow_availability(),
        "Subagent Dispatcher": test_subagent_availability(),
        "Natural Language Processing": test_natural_language_availability(),
        "Rollback Engine": test_rollback_availability(),
    }
    
    print("=" * 60)
    print("Verification Results Summary:")
    print("=" * 60)
    
    for component, available in results.items():
        status = "[OK]" if available else "[FAIL]"
        print(f"{component}: {status}")
    
    print("=" * 60)
    total = len(results)
    available_count = sum(results.values())
    print(f"Total: {available_count}/{total} components available")
    print("=" * 60)
    
    if available_count == total:
        print("All critical components are available")
        return 0
    else:
        print(f"{total - available_count} components are not available")
        return 1

if __name__ == "__main__":
    sys.exit(main())