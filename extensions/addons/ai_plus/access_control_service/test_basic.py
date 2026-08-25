# -*- coding: utf-8 -*-
"""Basic test for Access Control Service."""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from access_control_manager import AccessControlManager, RBACManager
from policy_enforcer import PolicyEnforcer
from permission_checker import PermissionChecker


def test_rbac_manager():
    """Test RBAC Manager basic operations."""
    print("Testing RBAC Manager...")
    
    # Mock storage for testing
    class MockStorage:
        def __init__(self):
            self.data = {}
        
        def get_connection(self):
            return self
        
        def execute_query(self, query, params=None):
            return []
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    storage = MockStorage()
    rbac_manager = RBACManager(storage)
    
    # Test that manager can be created
    assert rbac_manager is not None
    print("[OK] RBAC Manager created successfully")


def test_access_control_manager():
    """Test Access Control Manager basic operations."""
    print("Testing Access Control Manager...")
    
    # Mock storage for testing
    class MockStorage:
        def __init__(self):
            self.data = {}
        
        def get_connection(self):
            return self
        
        def execute_query(self, query, params=None):
            return []
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    storage = MockStorage()
    access_control_manager = AccessControlManager(storage)
    
    # Test that manager can be created
    assert access_control_manager is not None
    print("[OK] Access Control Manager created successfully")


def test_policy_enforcer():
    """Test Policy Enforcer basic operations."""
    print("Testing Policy Enforcer...")
    
    # Mock storage for testing
    class MockStorage:
        def __init__(self):
            self.data = {}
        
        def get_connection(self):
            return self
        
        def execute_query(self, query, params=None):
            return []
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    storage = MockStorage()
    access_control_manager = AccessControlManager(storage)
    policy_enforcer = PolicyEnforcer(access_control_manager)
    
    # Test that enforcer can be created
    assert policy_enforcer is not None
    print("[OK] Policy Enforcer created successfully")


def test_permission_checker():
    """Test Permission Checker basic operations."""
    print("Testing Permission Checker...")
    
    # Mock storage for testing
    class MockStorage:
        def __init__(self):
            self.data = {}
        
        def get_connection(self):
            return self
        
        def execute_query(self, query, params=None):
            return []
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    storage = MockStorage()
    access_control_manager = AccessControlManager(storage)
    permission_checker = PermissionChecker(access_control_manager)
    
    # Test that checker can be created
    assert permission_checker is not None
    print("[OK] Permission Checker created successfully")


if __name__ == "__main__":
    print("=" * 60)
    print("Access Control Service - Basic Tests")
    print("=" * 60)
    
    try:
        test_rbac_manager()
        test_access_control_manager()
        test_policy_enforcer()
        test_permission_checker()
        
        print("=" * 60)
        print("All basic tests passed! [OK]")
        print("=" * 60)
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
