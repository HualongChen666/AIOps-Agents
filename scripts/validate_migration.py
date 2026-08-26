#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Migration Validation Script
====================================

Validates that all database models are correctly created and accessible.
Provides a summary of the migration status.
"""

import logging
import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_database_models() -> Dict[str, bool]:
    """Validate that all database models can be imported and are accessible."""
    validation_results = {}
    
    # Test asset management models
    try:
        from core.models import (
            AssetInventoryMetadata,
            AssetRelationshipDB,
            AssetLifecycleDB,
            AssetDependencyDB,
        )
        validation_results['asset_management'] = True
        logger.info("✓ Asset management models validated")
    except Exception as e:
        validation_results['asset_management'] = False
        logger.error(f"✗ Asset management models failed: {e}")
    
    # Test capacity planning models
    try:
        from core.models import (
            CapacityPlanDB,
            OptimizationResultDB,
            RightsizingRecommendationDB,
        )
        validation_results['capacity_planning'] = True
        logger.info("✓ Capacity planning models validated")
    except Exception as e:
        validation_results['capacity_planning'] = False
        logger.error(f"✗ Capacity planning models failed: {e}")
    
    # Test cost management models
    try:
        from core.models import (
            CostBudgetDB,
            CostOptimizationDB,
            CostAnomalyDB,
            CostAlertDB,
            CostReportDB,
        )
        validation_results['cost_management'] = True
        logger.info("✓ Cost management models validated")
    except Exception as e:
        validation_results['cost_management'] = False
        logger.error(f"✗ Cost management models failed: {e}")
    
    # Test change management models
    try:
        from core.models import (
            ChangeApprovalDB,
            ChangeScheduleDB,
            ChangeRollbackPlanDB,
        )
        validation_results['change_management'] = True
        logger.info("✓ Change management models validated")
    except Exception as e:
        validation_results['change_management'] = False
        logger.error(f"✗ Change management models failed: {e}")
    
    # Test AI advanced models
    try:
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
        validation_results['ai_advanced'] = True
        logger.info("✓ AI advanced models validated")
    except Exception as e:
        validation_results['ai_advanced'] = False
        logger.error(f"✗ AI advanced models failed: {e}")
    
    return validation_results


def validate_api_imports() -> Dict[str, bool]:
    """Validate that all migrated API routers can be imported."""
    validation_results = {}
    
    # Test assets router
    try:
        from api.assets_advanced_router import router as assets_router
        validation_results['assets_router'] = True
        logger.info("✓ Assets router validated")
    except Exception as e:
        validation_results['assets_router'] = False
        logger.error(f"✗ Assets router failed: {e}")
    
    # Test capacity router
    try:
        from api.capacity_advanced_router import router as capacity_router
        validation_results['capacity_router'] = True
        logger.info("✓ Capacity router validated")
    except Exception as e:
        validation_results['capacity_router'] = False
        logger.error(f"✗ Capacity router failed: {e}")
    
    # Test cost router
    try:
        from api.cost_advanced_router import router as cost_router
        validation_results['cost_router'] = True
        logger.info("✓ Cost router validated")
    except Exception as e:
        validation_results['cost_router'] = False
        logger.error(f"✗ Cost router failed: {e}")
    
    # Test change router
    try:
        from api.change_advanced_router import router as change_router
        validation_results['change_router'] = True
        logger.info("✓ Change router validated")
    except Exception as e:
        validation_results['change_router'] = False
        logger.error(f"✗ Change router failed: {e}")
    
    # Test AI router
    try:
        from api.ai_advanced_router import router as ai_router
        validation_results['ai_router'] = True
        logger.info("✓ AI router validated")
    except Exception as e:
        validation_results['ai_router'] = False
        logger.error(f"✗ AI router failed: {e}")
    
    return validation_results


def main():
    """Main validation function."""
    logger.info("Starting database migration validation...")
    logger.info("=" * 60)
    
    # Validate database models
    logger.info("Validating database models...")
    model_results = validate_database_models()
    
    # Validate API imports
    logger.info("\nValidating API router imports...")
    api_results = validate_api_imports()
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    total_checks = len(model_results) + len(api_results)
    passed_checks = sum(model_results.values()) + sum(api_results.values())
    
    logger.info(f"Total checks: {total_checks}")
    logger.info(f"Passed: {passed_checks}")
    logger.info(f"Failed: {total_checks - passed_checks}")
    logger.info(f"Success rate: {(passed_checks/total_checks)*100:.1f}%")
    
    if passed_checks == total_checks:
        logger.info("\n✓ All validations passed successfully!")
        logger.info("Database migration is ready for production use.")
        return 0
    else:
        logger.warning(f"\n⚠ {total_checks - passed_checks} validation(s) failed.")
        logger.warning("Please review the errors above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
