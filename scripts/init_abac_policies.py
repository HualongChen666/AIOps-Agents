# -*- coding: utf-8 -*-
"""
Initialize ABAC policies for sensitive operations.

This script creates default ABAC policies for the AIOps platform,
covering various sensitive operations with fine-grained access control.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_default_policies():
    """Initialize default ABAC policies for sensitive operations."""
    
    # For now, we'll create a policy configuration file that can be loaded
    # when the ABAC engine is properly initialized with the database
    
    policies_config = {
        "policies": [
            {
                "name": "alert_delete_policy",
                "description": "Allow operators and admins to delete alerts",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"in": ["operator", "admin"]},
                    "clearance_level": {"gte": 2}
                },
                "resource_conditions": {
                    "type": {"equals": "alert"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["delete"],
                "priority": 100
            },
            {
                "name": "auto_heal_execute_policy",
                "description": "Allow operators and admins to execute auto-heal actions",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"in": ["operator", "admin"]},
                    "clearance_level": {"gte": 3}
                },
                "resource_conditions": {
                    "type": {"equals": "auto_heal"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["execute"],
                "priority": 100
            },
            {
                "name": "config_write_policy",
                "description": "Allow admins to write configuration",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"equals": "admin"},
                    "clearance_level": {"gte": 4}
                },
                "resource_conditions": {
                    "type": {"equals": "configuration"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["write"],
                "priority": 100
            },
            {
                "name": "policy_admin_policy",
                "description": "Allow admins to manage policies",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"equals": "admin"},
                    "clearance_level": {"gte": 5}
                },
                "resource_conditions": {
                    "type": {"equals": "policy"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["admin"],
                "priority": 100
            },
            {
                "name": "user_management_policy",
                "description": "Allow admins to manage users",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"equals": "admin"},
                    "clearance_level": {"gte": 4}
                },
                "resource_conditions": {
                    "type": {"equals": "user"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["write"],
                "priority": 100
            },
            {
                "name": "workflow_execute_policy",
                "description": "Allow operators and admins to execute workflows",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"in": ["operator", "admin"]},
                    "clearance_level": {"gte": 3}
                },
                "resource_conditions": {
                    "type": {"equals": "workflow"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["execute"],
                "priority": 100
            },
            {
                "name": "deployment_write_policy",
                "description": "Allow admins to manage deployments",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"equals": "admin"},
                    "clearance_level": {"gte": 4}
                },
                "resource_conditions": {
                    "type": {"equals": "deployment"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["write"],
                "priority": 100
            },
            {
                "name": "tenant_admin_policy",
                "description": "Allow super admins to manage tenants",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"equals": "admin"},
                    "clearance_level": {"gte": 5},
                    "is_super_admin": {"equals": True}
                },
                "resource_conditions": {
                    "type": {"equals": "tenant"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["admin"],
                "priority": 100
            },
            {
                "name": "secrets_access_policy",
                "description": "Allow admins to access secrets",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"equals": "admin"},
                    "clearance_level": {"gte": 5}
                },
                "resource_conditions": {
                    "type": {"equals": "secret"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["admin"],
                "priority": 100
            },
            {
                "name": "audit_read_policy",
                "description": "Allow auditors and admins to read audit logs",
                "effect": "allow",
                "subject_conditions": {
                    "role": {"in": ["admin", "auditor"]},
                    "clearance_level": {"gte": 3}
                },
                "resource_conditions": {
                    "type": {"equals": "audit"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["read"],
                "priority": 100
            },
            {
                "name": "deny_unauthorized_access",
                "description": "Deny access for users with insufficient clearance",
                "effect": "deny",
                "subject_conditions": {
                    "clearance_level": {"lt": 2}
                },
                "resource_conditions": {
                    "type": {"regex": ".*"}
                },
                "environment_conditions": {
                    "time": {"regex": ".*"}
                },
                "actions": ["read", "write", "delete", "execute", "admin"],
                "priority": 200
            },
            {
                "name": "deny_business_hours_restriction",
                "description": "Deny sensitive operations outside business hours for non-admins",
                "effect": "deny",
                "subject_conditions": {
                    "role": {"in": ["operator", "viewer"]},
                    "clearance_level": {"lt": 5}
                },
                "resource_conditions": {
                    "type": {"in": ["configuration", "deployment", "secret"]}
                },
                "environment_conditions": {
                    "time": {"regex": "(2[0-3]|[01][0-9]):[0-5][0-9]"}
                },
                "actions": ["write", "delete", "execute", "admin"],
                "priority": 150
            }
        ]
    }
    
    # Save policies to configuration file
    import json
    config_path = os.path.join(os.path.dirname(__file__), "..", "data", "abac_policies.json")
    
    try:
        with open(config_path, 'w') as f:
            json.dump(policies_config, f, indent=2)
        
        print(f"ABAC policies configuration saved to {config_path}")
        print(f"Total policies: {len(policies_config['policies'])}")
        
        # List policies
        for policy in policies_config['policies']:
            print(f"  - {policy['name']}: {policy['description']}")
        
        return True
    except Exception as e:
        print(f"Failed to save ABAC policies configuration: {e}")
        return False


if __name__ == "__main__":
    success = init_default_policies()
    sys.exit(0 if success else 1)