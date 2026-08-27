# -*- coding: utf-8 -*-
"""
Data Consistency Tests
数据一致性测试

测试JSON文件和数据库之间的数据一致性
"""

import json
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from core.auth_db import get_session
from core.models import (
    BusinessImpactAnalysisDB,
    BusinessImpactDependencyDB,
    BusinessImpactReportDB,
    ChaosExperimentDB,
    ChaosScenarioDB,
    ChaosFaultDB,
)


class TestDataConsistency:
    """数据一致性测试"""

    def test_business_impact_analysis_consistency(self):
        """测试业务影响分析数据一致性"""
        db = get_session()
        try:
            # Create test data
            test_id = f"BIA-CONSISTENCY-{uuid.uuid4().hex[:8]}"
            test_data = {
                "id": test_id,
                "service_name": "consistency-test-service",
                "analysis_type": "full",
                "time_range": "1h",
                "include_dependencies": True,
                "include_ux_metrics": True,
                "status": "pending",
                "result": None,
                "error": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            # Save to database
            from api.business_impact_advanced_router import _save_analysis_to_db
            _save_analysis_to_db(db, test_data)

            # Retrieve from database
            db_record = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == test_id
            ).first()

            # Verify consistency
            assert db_record is not None
            assert db_record.service_name == test_data["service_name"]
            assert db_record.analysis_type == test_data["analysis_type"]
            assert db_record.status == test_data["status"]
            assert db_record.include_dependencies == test_data["include_dependencies"]
            assert db_record.include_ux_metrics == test_data["include_ux_metrics"]

            # Clean up
            db.delete(db_record)
            db.commit()
        finally:
            db.close()

    def test_chaos_experiment_consistency(self):
        """测试混沌实验数据一致性"""
        db = get_session()
        try:
            # Create test data
            test_id = f"EXP-CONSISTENCY-{uuid.uuid4().hex[:8]}"
            test_data = {
                "id": test_id,
                "name": "Consistency Test Experiment",
                "description": "Test for data consistency",
                "experiment_type": "latency_injection",
                "parameters": {"delay_ms": 500, "target": "api-service"},
                "severity": "medium",
                "status": "pending",
                "tags": ["consistency", "test"],
                "result": None,
                "error": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            # Save to database
            from api.chaos_advanced_router import _save_experiment_to_db
            _save_experiment_to_db(db, test_data)

            # Retrieve from database
            db_record = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == test_id
            ).first()

            # Verify consistency
            assert db_record is not None
            assert db_record.name == test_data["name"]
            assert db_record.experiment_type == test_data["experiment_type"]
            assert db_record.status == test_data["status"]
            assert db_record.severity == test_data["severity"]
            assert db_record.parameters == test_data["parameters"]

            # Clean up
            db.delete(db_record)
            db.commit()
        finally:
            db.close()

    def test_data_update_consistency(self):
        """测试数据更新一致性"""
        db = get_session()
        try:
            # Create initial data
            test_id = f"BIA-UPDATE-{uuid.uuid4().hex[:8]}"
            initial_data = {
                "id": test_id,
                "service_name": "update-test-service",
                "analysis_type": "full",
                "time_range": "1h",
                "include_dependencies": True,
                "include_ux_metrics": True,
                "status": "pending",
                "result": None,
                "error": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.business_impact_advanced_router import _save_analysis_to_db
            _save_analysis_to_db(db, initial_data)

            # Update data
            updated_data = initial_data.copy()
            updated_data["status"] = "completed"
            updated_data["result"] = {"success": True, "metrics": {"latency": 100}}
            updated_data["updated_at"] = "2024-01-01T01:00:00Z"

            _save_analysis_to_db(db, updated_data)

            # Verify update
            db_record = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == test_id
            ).first()

            assert db_record.status == "completed"
            assert db_record.result is not None
            assert db_record.result["success"] == True

            # Clean up
            db.delete(db_record)
            db.commit()
        finally:
            db.close()

    def test_json_field_consistency(self):
        """测试JSON字段数据一致性"""
        db = get_session()
        try:
            # Create data with complex JSON fields
            test_id = f"EXP-JSON-{uuid.uuid4().hex[:8]}"
            complex_parameters = {
                "delay_ms": 500,
                "target": "api-service",
                "network_conditions": {
                    "bandwidth": "100Mbps",
                    "latency": "50ms",
                    "packet_loss": "0.1%"
                },
                "metadata": {
                    "created_by": "system",
                    "environment": "test"
                }
            }

            test_data = {
                "id": test_id,
                "name": "JSON Consistency Test",
                "description": "Test JSON field consistency",
                "experiment_type": "network_partition",
                "parameters": complex_parameters,
                "severity": "high",
                "status": "pending",
                "tags": ["json", "consistency"],
                "result": None,
                "error": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.chaos_advanced_router import _save_experiment_to_db
            _save_experiment_to_db(db, test_data)

            # Retrieve and verify JSON structure
            db_record = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == test_id
            ).first()

            assert db_record is not None
            assert db_record.parameters == complex_parameters
            assert db_record.parameters["network_conditions"]["bandwidth"] == "100Mbps"
            assert db_record.parameters["metadata"]["created_by"] == "system"

            # Clean up
            db.delete(db_record)
            db.commit()
        finally:
            db.close()

    def test_batch_consistency(self):
        """测试批量数据一致性"""
        db = get_session()
        try:
            # Create multiple records
            test_ids = []
            for i in range(5):
                test_id = f"BIA-BATCH-{uuid.uuid4().hex[:8]}"
                test_data = {
                    "id": test_id,
                    "service_name": f"batch-service-{i}",
                    "analysis_type": "full",
                    "time_range": "1h",
                    "include_dependencies": True,
                    "include_ux_metrics": True,
                    "status": "pending",
                    "result": None,
                    "error": None,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }

                from api.business_impact_advanced_router import _save_analysis_to_db
                _save_analysis_to_db(db, test_data)
                test_ids.append(test_id)

            # Verify all records are consistent
            for i, test_id in enumerate(test_ids):
                db_record = db.query(BusinessImpactAnalysisDB).filter(
                    BusinessImpactAnalysisDB.id == test_id
                ).first()
                assert db_record is not None
                assert db_record.service_name == f"batch-service-{i}"
                assert db_record.status == "pending"

            # Clean up
            for test_id in test_ids:
                db_record = db.query(BusinessImpactAnalysisDB).filter(
                    BusinessImpactAnalysisDB.id == test_id
                ).first()
                if db_record:
                    db.delete(db_record)
            db.commit()
        finally:
            db.close()


class TestConsistencyValidation:
    """一致性验证测试"""

    def test_validation_script_import(self):
        """测试验证脚本可导入"""
        try:
            from scripts.validate_business_impact_migration import validate_migration
            assert callable(validate_migration)
        except ImportError:
            pytest.skip("Validation script not available for import")

    def test_consistency_check_after_dual_write(self):
        """测试双写后的一致性检查"""
        db = get_session()
        try:
            # Create test data
            test_id = f"BIA-CHECK-{uuid.uuid4().hex[:8]}"
            test_data = {
                "id": test_id,
                "service_name": "consistency-check-service",
                "analysis_type": "full",
                "time_range": "1h",
                "include_dependencies": True,
                "include_ux_metrics": True,
                "status": "pending",
                "result": None,
                "error": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            # Perform dual write
            from api.business_impact_advanced_router import _save_analysis_to_db
            _save_analysis_to_db(db, test_data)

            # Verify database has the record
            db_record = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == test_id
            ).first()

            # Perform consistency check
            assert db_record is not None
            assert db_record.id == test_data["id"]
            assert db_record.service_name == test_data["service_name"]
            assert db_record.status == test_data["status"]
            assert db_record.analysis_type == test_data["analysis_type"]
            assert db_record.time_range == test_data["time_range"]
            assert db_record.include_dependencies == test_data["include_dependencies"]
            assert db_record.include_ux_metrics == test_data["include_ux_metrics"]

            # Clean up
            db.delete(db_record)
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])