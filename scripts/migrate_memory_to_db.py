#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Data Migration Script
=====================

Migrates existing in-memory data to PostgreSQL database.
This script should be run after all database models are created and migration scripts are executed.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_assets_data(db_session) -> Dict[str, int]:
    """Migrate assets data from memory to database."""
    from api.assets_advanced_router import (
        _asset_inventory_metadata,
        _asset_relationships,
        _asset_lifecycle_data,
        _asset_dependencies,
    )
    from core.models import (
        AssetInventoryMetadata,
        AssetRelationshipDB,
        AssetLifecycleDB,
        AssetDependencyDB,
    )
    
    migration_stats = {
        'inventory_metadata': 0,
        'relationships': 0,
        'lifecycle_data': 0,
        'dependencies': 0,
    }
    
    try:
        # Migrate inventory metadata
        for asset_id, metadata in _asset_inventory_metadata.items():
            existing = db_session.query(AssetInventoryMetadata).filter(
                AssetInventoryMetadata.asset_id == asset_id
            ).first()
            
            if not existing:
                db_record = AssetInventoryMetadata(
                    asset_id=asset_id,
                    metadata=metadata,
                    updated_at=datetime.utcnow(),
                )
                db_session.add(db_record)
                migration_stats['inventory_metadata'] += 1
        
        # Migrate relationships
        for relationship in _asset_relationships:
            existing = db_session.query(AssetRelationshipDB).filter(
                AssetRelationshipDB.source_asset_id == relationship.source_asset_id,
                AssetRelationshipDB.target_asset_id == relationship.target_asset_id
            ).first()
            
            if not existing:
                db_record = AssetRelationshipDB(
                    source_asset_id=relationship.source_asset_id,
                    target_asset_id=relationship.target_asset_id,
                    relationship_type=relationship.relationship_type,
                    metadata=relationship.metadata,
                )
                db_session.add(db_record)
                migration_stats['relationships'] += 1
        
        # Migrate lifecycle data
        for asset_id, lifecycle in _asset_lifecycle_data.items():
            existing = db_session.query(AssetLifecycleDB).filter(
                AssetLifecycleDB.asset_id == asset_id
            ).first()
            
            if not existing:
                db_record = AssetLifecycleDB(
                    asset_id=asset_id,
                    status=lifecycle.status,
                    stage=lifecycle.stage,
                    health_score=lifecycle.health_score,
                    last_updated=lifecycle.last_updated,
                    lifecycle_metadata=lifecycle.metadata,
                )
                db_session.add(db_record)
                migration_stats['lifecycle_data'] += 1
        
        # Migrate dependencies
        for asset_id, dependency in _asset_dependencies.items():
            existing = db_session.query(AssetDependencyDB).filter(
                AssetDependencyDB.asset_id == asset_id
            ).first()
            
            if not existing:
                db_record = AssetDependencyDB(
                    asset_id=asset_id,
                    depends_on=dependency.depends_on,
                    dependency_type=dependency.dependency_type,
                    criticality=dependency.criticality,
                    dependency_metadata=dependency.metadata,
                )
                db_session.add(db_record)
                migration_stats['dependencies'] += 1
        
        db_session.commit()
        logger.info(f"Assets data migration completed: {migration_stats}")
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to migrate assets data: {e}", exc_info=True)
        raise
    
    return migration_stats


def migrate_capacity_data(db_session) -> Dict[str, int]:
    """Migrate capacity data from memory to database."""
    from api.capacity_advanced_router import (
        _capacity_plans,
        _optimization_results,
        _rightsizing_recommendations,
    )
    from core.models import (
        CapacityPlanDB,
        OptimizationResultDB,
        RightsizingRecommendationDB,
    )
    
    migration_stats = {
        'capacity_plans': 0,
        'optimization_results': 0,
        'rightsizing_recommendations': 0,
    }
    
    try:
        # Migrate capacity plans
        for plan_id, plan in _capacity_plans.items():
            existing = db_session.query(CapacityPlanDB).filter(
                CapacityPlanDB.id == plan_id
            ).first()
            
            if not existing:
                db_record = CapacityPlanDB(
                    id=plan_id,
                    name=plan.name,
                    resource_type=plan.resource_type.value,
                    service=plan.service,
                    current_capacity=plan.current_capacity,
                    projected_capacity=plan.projected_capacity,
                    unit=plan.unit,
                    horizon=plan.horizon.value,
                    target_date=plan.target_date,
                    threshold=plan.threshold,
                    recommended_action=plan.recommended_action,
                    estimated_cost=plan.estimated_cost,
                    created_at=plan.created_at,
                    created_by=plan.created_by,
                    status=plan.status,
                    plan_metadata=plan.metadata,
                )
                db_session.add(db_record)
                migration_stats['capacity_plans'] += 1
        
        # Migrate optimization results
        for opt_id, result in _optimization_results.items():
            existing = db_session.query(OptimizationResultDB).filter(
                OptimizationResultDB.id == opt_id
            ).first()
            
            if not existing:
                db_record = OptimizationResultDB(
                    id=opt_id,
                    service=result.service,
                    resource_types=[rt.value for rt in result.resource_types],
                    strategy=result.strategy.value,
                    current_usage=result.current_usage,
                    optimized_usage=result.optimized_usage,
                    savings=result.savings,
                    implementation_steps=result.implementation_steps,
                    created_at=result.created_at,
                    created_by=result.created_by,
                    status=result.status,
                    opt_metadata=result.metadata,
                )
                db_session.add(db_record)
                migration_stats['optimization_results'] += 1
        
        # Migrate rightsizing recommendations
        for recommendation in _rightsizing_recommendations:
            existing = db_session.query(RightsizingRecommendationDB).filter(
                RightsizingRecommendationDB.id == recommendation.id
            ).first()
            
            if not existing:
                db_record = RightsizingRecommendationDB(
                    id=recommendation.id,
                    service=recommendation.service,
                    resource_type=recommendation.resource_type.value,
                    current_spec=recommendation.current_spec,
                    recommended_spec=recommendation.recommended_spec,
                    action=recommendation.action.value,
                    reason=recommendation.reason,
                    priority=recommendation.priority.value,
                    estimated_monthly_savings=recommendation.estimated_monthly_savings,
                    performance_impact=recommendation.performance_impact,
                    implementation_complexity=recommendation.implementation_complexity,
                    created_at=recommendation.created_at,
                    rec_metadata=None,
                )
                db_session.add(db_record)
                migration_stats['rightsizing_recommendations'] += 1
        
        db_session.commit()
        logger.info(f"Capacity data migration completed: {migration_stats}")
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to migrate capacity data: {e}", exc_info=True)
        raise
    
    return migration_stats


def migrate_cost_data(db_session) -> Dict[str, int]:
    """Migrate cost data from memory to database."""
    from api.cost_advanced_router import (
        _budgets,
        _optimization_suggestions,
        _anomalies,
        _alerts,
        _reports,
    )
    from core.models import (
        CostBudgetDB,
        CostOptimizationDB,
        CostAnomalyDB,
        CostAlertDB,
        CostReportDB,
    )
    
    migration_stats = {
        'budgets': 0,
        'optimization_suggestions': 0,
        'anomalies': 0,
        'alerts': 0,
        'reports': 0,
    }
    
    try:
        # Migrate budgets
        for budget_id, budget in _budgets.items():
            existing = db_session.query(CostBudgetDB).filter(
                CostBudgetDB.id == budget_id
            ).first()
            
            if not existing:
                db_record = CostBudgetDB(
                    id=budget_id,
                    name=budget['name'],
                    service=budget['service'],
                    amount=budget['amount'],
                    spent=budget.get('spent', 0.0),
                    remaining=budget['remaining'],
                    period=budget['period'],
                    status=budget['status'],
                    alerts_enabled=budget['alerts_enabled'],
                    created_at=datetime.fromisoformat(budget['created_at']) if budget.get('created_at') else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(budget['updated_at']) if budget.get('updated_at') else datetime.utcnow(),
                    budget_metadata=None,
                )
                db_session.add(db_record)
                migration_stats['budgets'] += 1
        
        # Migrate optimization suggestions
        for opt_id, suggestion in _optimization_suggestions.items():
            existing = db_session.query(CostOptimizationDB).filter(
                CostOptimizationDB.id == opt_id
            ).first()
            
            if not existing:
                db_record = CostOptimizationDB(
                    id=opt_id,
                    service=suggestion.get('resource', '').split()[0] if suggestion.get('resource') else 'unknown',
                    optimization_type=suggestion.get('type', 'unknown'),
                    potential_savings=suggestion.get('projected_savings', 0.0),
                    implementation_effort=suggestion.get('effort', 'medium'),
                    priority=suggestion.get('impact', 'medium'),
                    status=suggestion.get('status', 'pending'),
                    created_at=datetime.fromisoformat(suggestion['created_at']) if suggestion.get('created_at') else datetime.utcnow(),
                    opt_metadata=None,
                )
                db_session.add(db_record)
                migration_stats['optimization_suggestions'] += 1
        
        # Migrate anomalies
        for anomaly in _anomalies:
            existing = db_session.query(CostAnomalyDB).filter(
                CostAnomalyDB.id == anomaly['id']
            ).first()
            
            if not existing:
                db_record = CostAnomalyDB(
                    id=anomaly['id'],
                    service=anomaly['service'],
                    anomaly_type='spike' if 'spike' in anomaly.get('description', '').lower() else 'trend',
                    detected_at=datetime.fromisoformat(anomaly['detected_at']) if anomaly.get('detected_at') else datetime.utcnow(),
                    severity=anomaly['severity'],
                    description=anomaly['description'],
                    affected_amount=anomaly.get('actual_cost', 0.0) - anomaly.get('expected_cost', 0.0),
                    status=anomaly['status'],
                    created_at=datetime.fromisoformat(anomaly['detected_at']) if anomaly.get('detected_at') else datetime.utcnow(),
                    anomaly_metadata=None,
                )
                db_session.add(db_record)
                migration_stats['anomalies'] += 1
        
        # Migrate alerts
        for alert_id, alert in _alerts.items():
            existing = db_session.query(CostAlertDB).filter(
                CostAlertDB.id == alert_id
            ).first()
            
            if not existing:
                db_record = CostAlertDB(
                    id=alert_id,
                    name=alert['name'],
                    alert_type=alert['type'],
                    threshold=alert['threshold'],
                    current_value=alert['current_value'],
                    service='general',
                    status='active' if alert.get('enabled') else 'inactive',
                    notification_channels=alert.get('notification_channels', []),
                    created_at=datetime.fromisoformat(alert['created_at']) if alert.get('created_at') else datetime.utcnow(),
                    alert_metadata=None,
                )
                db_session.add(db_record)
                migration_stats['alerts'] += 1
        
        db_session.commit()
        logger.info(f"Cost data migration completed: {migration_stats}")
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to migrate cost data: {e}", exc_info=True)
        raise
    
    return migration_stats


def main():
    """Main migration function."""
    logger.info("Starting data migration from memory to database...")
    
    try:
        from core.database import SessionLocal
        
        # Create database session
        db_session = SessionLocal()
        
        try:
            # Migrate all data types
            assets_stats = migrate_assets_data(db_session)
            capacity_stats = migrate_capacity_data(db_session)
            cost_stats = migrate_cost_data(db_session)
            
            # Print summary
            total_migrated = sum(assets_stats.values()) + sum(capacity_stats.values()) + sum(cost_stats.values())
            logger.info(f"Data migration completed successfully!")
            logger.info(f"Total records migrated: {total_migrated}")
            logger.info(f"Assets: {assets_stats}")
            logger.info(f"Capacity: {capacity_stats}")
            logger.info(f"Cost: {cost_stats}")
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Data migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
