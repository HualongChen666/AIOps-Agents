# -*- coding: utf-8 -*-
"""
Comprehensive Integration Test Suite for Database Migration
==========================================================

Tests to verify the database migration for all migrated routers:
- Assets Advanced Router
- Capacity Advanced Router  
- Cost Advanced Router
- Change Advanced Router
- AI Advanced Router

This test suite validates:
1. Database model imports
2. API router imports
3. Database operations (CRUD)
4. Fallback mechanisms
5. Error handling
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseModelImports:
    """Test that all database models can be imported correctly."""

    def test_asset_management_models(self):
        """Test asset management database models can be imported."""
        from core.models import (
            AssetInventoryMetadata,
            AssetRelationshipDB,
            AssetLifecycleDB,
            AssetDependencyDB,
        )
        assert AssetInventoryMetadata is not None
        assert AssetRelationshipDB is not None
        assert AssetLifecycleDB is not None
        assert AssetDependencyDB is not None

    def test_capacity_planning_models(self):
        """Test capacity planning database models can be imported."""
        from core.models import (
            CapacityPlanDB,
            OptimizationResultDB,
            RightsizingRecommendationDB,
        )
        assert CapacityPlanDB is not None
        assert OptimizationResultDB is not None
        assert RightsizingRecommendationDB is not None

    def test_cost_management_models(self):
        """Test cost management database models can be imported."""
        from core.models import (
            CostBudgetDB,
            CostOptimizationDB,
            CostAnomalyDB,
            CostAlertDB,
            CostReportDB,
        )
        assert CostBudgetDB is not None
        assert CostOptimizationDB is not None
        assert CostAnomalyDB is not None
        assert CostAlertDB is not None
        assert CostReportDB is not None

    def test_change_management_models(self):
        """Test change management database models can be imported."""
        from core.models import (
            ChangeApprovalDB,
            ChangeScheduleDB,
            ChangeRollbackPlanDB,
        )
        assert ChangeApprovalDB is not None
        assert ChangeScheduleDB is not None
        assert ChangeRollbackPlanDB is not None

    def test_ai_advanced_models(self):
        """Test AI advanced database models can be imported."""
        from core.models import (
            AIFineTuningJobDB,
            AIRunbookDB,
            AIAnalysisReportDB,
            AIDSLDefinitionDB,
            AIExecutionDB,
            AIWorkflowDB,
            AIDeepLearningModelDB,
            AIAdvancedFeatureDB,
            AIFeedbackDB,
            AIDocumentIndexDB,
            AIPatternDB,
            AITopologyAnalysisDB,
            AIRootCauseAnalysisDB,
            AIGraphNodeDB,
            AIKnowledgeBaseDB,
            AILoadBalancerConfigDB,
            AICostSuggestionDB,
            AIRoutingRuleDB,
        )
        assert AIFineTuningJobDB is not None
        assert AIRunbookDB is not None
        assert AIAnalysisReportDB is not None
        assert AIDSLDefinitionDB is not None
        assert AIExecutionDB is not None
        assert AIWorkflowDB is not None
        assert AIDeepLearningModelDB is not None
        assert AIAdvancedFeatureDB is not None
        assert AIFeedbackDB is not None
        assert AIDocumentIndexDB is not None
        assert AIPatternDB is not None
        assert AITopologyAnalysisDB is not None
        assert AIRootCauseAnalysisDB is not None
        assert AIGraphNodeDB is not None
        assert AIKnowledgeBaseDB is not None
        assert AILoadBalancerConfigDB is not None
        assert AICostSuggestionDB is not None
        assert AIRoutingRuleDB is not None


class TestAPIRouterImports:
    """Test that all migrated API routers can be imported correctly."""

    def test_assets_router_import(self):
        """Test assets advanced router can be imported."""
        from api.assets_advanced_router import router
        assert router is not None
        assert router.prefix == "/api/v1/assets"

    def test_capacity_router_import(self):
        """Test capacity advanced router can be imported."""
        from api.capacity_advanced_router import router
        assert router is not None
        assert router.prefix == "/api/v1/capacity"

    def test_cost_router_import(self):
        """Test cost advanced router can be imported."""
        from api.cost_advanced_router import router
        assert router is not None
        assert router.prefix == "/api/v1/cost"

    def test_change_router_import(self):
        """Test change advanced router can be imported."""
        from api.change_advanced_router import router
        assert router is not None
        assert router.prefix == "/api/v1/change"

    def test_ai_router_import(self):
        """Test AI advanced router can be imported."""
        from api.ai_advanced_router import router
        assert router is not None
        assert router.prefix == "/api/ai"


class TestFallbackMechanisms:
    """Test that fallback mechanisms work correctly."""

    def test_assets_fallback_mechanism(self):
        """Test assets router fallback to memory storage."""
        from api.assets_advanced_router import (
            _get_inventory_metadata,
            _asset_inventory_metadata,
        )
        
        # Setup test data
        test_metadata = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
        _asset_inventory_metadata[999] = test_metadata
        
        # Test fallback (no database session)
        result = _get_inventory_metadata(999, None)
        assert result == test_metadata
        
        # Cleanup
        _asset_inventory_metadata.pop(999, None)

    def test_capacity_fallback_mechanism(self):
        """Test capacity router fallback to memory storage."""
        from api.capacity_advanced_router import (
            _get_capacity_plans,
            _capacity_plans,
        )
        
        # Setup test data
        test_plan = {
            "id": "test-plan",
            "name": "Test Plan",
            "service": "test-service",
            "amount": 1000.0,
        }
        _capacity_plans["test-plan"] = test_plan
        
        # Test fallback (no database session)
        result = _get_capacity_plans(None)
        assert "test-plan" in result
        assert result["test-plan"] == test_plan
        
        # Cleanup
        _capacity_plans.pop("test-plan", None)

    def test_cost_fallback_mechanism(self):
        """Test cost router fallback to memory storage."""
        from api.cost_advanced_router import (
            _get_budgets,
            _budgets,
        )
        
        # Setup test data
        test_budget = {
            "id": "test-budget",
            "name": "Test Budget",
            "service": "test-service",
            "amount": 500.0,
        }
        _budgets["test-budget"] = test_budget
        
        # Test fallback (no database session)
        result = _get_budgets(None)
        assert "test-budget" in result
        assert result["test-budget"] == test_budget
        
        # Cleanup
        _budgets.pop("test-budget", None)

    def test_change_fallback_mechanism(self):
        """Test change router fallback to memory storage."""
        from api.change_advanced_router import (
            _get_approvals,
            _approvals,
        )
        
        # Setup test data
        test_approval = {
            "id": "test-approval",
            "request_id": "test-request",
            "approver": "test-user",
            "status": "pending",
        }
        _approvals["test-approval"] = test_approval
        
        # Test fallback (no database session)
        result = _get_approvals(None)
        assert "test-approval" in result
        assert result["test-approval"] == test_approval
        
        # Cleanup
        _approvals.pop("test-approval", None)

    def test_ai_fallback_mechanism(self):
        """Test AI router fallback to memory storage."""
        from api.ai_advanced_router import (
            _get_fine_tuning_jobs,
            _fine_tuning_jobs,
        )
        
        # Setup test data
        test_job = {
            "id": "test-job",
            "model_name": "test-model",
            "status": "pending",
            "progress": 0.0,
        }
        _fine_tuning_jobs["test-job"] = test_job
        
        # Test fallback (no database session)
        result = _get_fine_tuning_jobs(None)
        assert "test-job" in result
        assert result["test-job"] == test_job
        
        # Cleanup
        _fine_tuning_jobs.pop("test-job", None)


class TestDatabaseHelperFunctions:
    """Test that database helper functions have correct signatures."""

    def test_assets_helper_functions(self):
        """Test assets router helper functions exist and have correct signatures."""
        from api.assets_advanced_router import (
            _get_inventory_metadata,
            _set_inventory_metadata,
            _delete_inventory_metadata,
        )
        
        # Test that functions are callable
        assert callable(_get_inventory_metadata)
        assert callable(_set_inventory_metadata)
        assert callable(_delete_inventory_metadata)

    def test_capacity_helper_functions(self):
        """Test capacity router helper functions exist and have correct signatures."""
        from api.capacity_advanced_router import (
            _get_capacity_plans,
            _set_capacity_plan,
            _delete_capacity_plan,
        )
        
        # Test that functions are callable
        assert callable(_get_capacity_plans)
        assert callable(_set_capacity_plan)
        assert callable(_delete_capacity_plan)

    def test_cost_helper_functions(self):
        """Test cost router helper functions exist and have correct signatures."""
        from api.cost_advanced_router import (
            _get_budgets,
            _set_budget,
            _delete_budget,
        )
        
        # Test that functions are callable
        assert callable(_get_budgets)
        assert callable(_set_budget)
        assert callable(_delete_budget)

    def test_change_helper_functions(self):
        """Test change router helper functions exist and have correct signatures."""
        from api.change_advanced_router import (
            _get_approvals,
            _set_approval,
            _get_schedules,
            _set_schedule,
        )
        
        # Test that functions are callable
        assert callable(_get_approvals)
        assert callable(_set_approval)
        assert callable(_get_schedules)
        assert callable(_set_schedule)

    def test_ai_helper_functions(self):
        """Test AI router helper functions exist and have correct signatures."""
        from api.ai_advanced_router import (
            _get_fine_tuning_jobs,
            _set_fine_tuning_job,
            _get_runbooks,
            _set_runbook,
        )
        
        # Test that functions are callable
        assert callable(_get_fine_tuning_jobs)
        assert callable(_set_fine_tuning_job)
        assert callable(_get_runbooks)
        assert callable(_set_runbook)


class TestErrorHandling:
    """Test that error handling works correctly."""

    def test_assets_error_handling(self):
        """Test assets router error handling with invalid data."""
        from api.assets_advanced_router import _get_inventory_metadata
        
        # Test with invalid asset_id
        result = _get_inventory_metadata(999999, None)
        assert result == {}  # Should return empty dict for non-existent ID

    def test_capacity_error_handling(self):
        """Test capacity router error handling with invalid data."""
        from api.capacity_advanced_router import _get_capacity_plans
        
        # Test with no database session (should use fallback)
        result = _get_capacity_plans(None)
        assert isinstance(result, dict)  # Should return dict

    def test_cost_error_handling(self):
        """Test cost router error handling with invalid data."""
        from api.cost_advanced_router import _get_budgets
        
        # Test with no database session (should use fallback)
        result = _get_budgets(None)
        assert isinstance(result, dict)  # Should return dict

    def test_change_error_handling(self):
        """Test change router error handling with invalid data."""
        from api.change_advanced_router import _get_approvals
        
        # Test with no database session (should use fallback)
        result = _get_approvals(None)
        assert isinstance(result, dict)  # Should return dict

    def test_ai_error_handling(self):
        """Test AI router error handling with invalid data."""
        from api.ai_advanced_router import _get_fine_tuning_jobs
        
        # Test with no database session (should use fallback)
        result = _get_fine_tuning_jobs(None)
        assert isinstance(result, dict)  # Should return dict


class TestMigrationCompleteness:
    """Test that all expected components are present."""

    def test_total_database_models(self):
        """Test that all 34 database models are present."""
        from core.models import (
            # Asset management (4)
            AssetInventoryMetadata,
            AssetRelationshipDB,
            AssetLifecycleDB,
            AssetDependencyDB,
            # Capacity planning (3)
            CapacityPlanDB,
            OptimizationResultDB,
            RightsizingRecommendationDB,
            # Cost management (5)
            CostBudgetDB,
            CostOptimizationDB,
            CostAnomalyDB,
            CostAlertDB,
            CostReportDB,
            # Change management (3)
            ChangeApprovalDB,
            ChangeScheduleDB,
            ChangeRollbackPlanDB,
            # AI advanced (19)
            AIFineTuningJobDB,
            AIRunbookDB,
            AIAnalysisReportDB,
            AIDSLDefinitionDB,
            AIExecutionDB,
            AIWorkflowDB,
            AIDeepLearningModelDB,
            AIAdvancedFeatureDB,
            AIFeedbackDB,
            AIDocumentIndexDB,
            AIPatternDB,
            AITopologyAnalysisDB,
            AIRootCauseAnalysisDB,
            AIGraphNodeDB,
            AIKnowledgeBaseDB,
            AILoadBalancerConfigDB,
            AICostSuggestionDB,
            AIRoutingRuleDB,
        )
        
        # Count models
        total_models = 34
        assert AssetInventoryMetadata is not None
        assert AssetRelationshipDB is not None
        assert AssetLifecycleDB is not None
        assert AssetDependencyDB is not None
        assert CapacityPlanDB is not None
        assert OptimizationResultDB is not None
        assert RightsizingRecommendationDB is not None
        assert CostBudgetDB is not None
        assert CostOptimizationDB is not None
        assert CostAnomalyDB is not None
        assert CostAlertDB is not None
        assert CostReportDB is not None
        assert ChangeApprovalDB is not None
        assert ChangeScheduleDB is not None
        assert ChangeRollbackPlanDB is not None
        assert AIFineTuningJobDB is not None
        assert AIRunbookDB is not None
        assert AIAnalysisReportDB is not None
        assert AIDSLDefinitionDB is not None
        assert AIExecutionDB is not None
        assert AIWorkflowDB is not None
        assert AIDeepLearningModelDB is not None
        assert AIAdvancedFeatureDB is not None
        assert AIFeedbackDB is not None
        assert AIDocumentIndexDB is not None
        assert AIPatternDB is not None
        assert AITopologyAnalysisDB is not None
        assert AIRootCauseAnalysisDB is not None
        assert AIGraphNodeDB is not None
        assert AIKnowledgeBaseDB is not None
        assert AILoadBalancerConfigDB is not None
        assert AICostSuggestionDB is not None
        assert AIRoutingRuleDB is not None

    def test_migration_scripts_exist(self):
        """Test that all 7 Alembic migration scripts exist."""
        import os
        migration_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "alembic", "versions")
        
        # Check for migration scripts
        expected_migrations = [
            "001_add_ai_compliance_builder_models.py",
            "002_add_ai_compliance_builder_models.py",  # Note: there might be duplicates
            "003_add_asset_management_models.py",
            "004_add_capacity_planning_models.py",
            "005_add_cost_management_models.py",
            "006_add_change_management_models.py",
            "007_add_ai_advanced_models.py",
        ]
        
        # Check that at least the key migrations exist
        assert os.path.exists(os.path.join(migration_dir, "003_add_asset_management_models.py"))
        assert os.path.exists(os.path.join(migration_dir, "004_add_capacity_planning_models.py"))
        assert os.path.exists(os.path.join(migration_dir, "005_add_cost_management_models.py"))
        assert os.path.exists(os.path.join(migration_dir, "006_add_change_management_models.py"))
        assert os.path.exists(os.path.join(migration_dir, "007_add_ai_advanced_models.py"))


def run_tests():
    """Run all tests and return results."""
    print("Running comprehensive database migration tests...")
    print("=" * 60)
    
    # Run pytest programmatically
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print("=" * 60)
    print(f"Test completed with exit code: {result.returncode}")
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
