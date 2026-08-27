# -*- coding: utf-8 -*-
"""
Dual Write Logic Tests
双写逻辑测试

测试JSON文件和数据库的双写逻辑正确性
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


class TestBusinessImpactDualWrite:
    """业务影响双写逻辑测试"""

    def test_save_analysis_to_db(self):
        """测试保存分析到数据库"""
        db = get_session()
        try:
            analysis_data = {
                "id": f"BIA-TEST-{uuid.uuid4().hex[:8]}",
                "service_name": "test-service",
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

            # Import the dual-write function
            from api.business_impact_advanced_router import _save_analysis_to_db

            _save_analysis_to_db(db, analysis_data)

            # Verify database has the record
            retrieved = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == analysis_data["id"]
            ).first()
            assert retrieved is not None
            assert retrieved.service_name == "test-service"
            assert retrieved.status == "pending"

            # Clean up
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()

    def test_save_dependency_to_db(self):
        """测试保存依赖关系到数据库"""
        db = get_session()
        try:
            dependency_data = {
                "id": f"DEP-TEST-{uuid.uuid4().hex[:8]}",
                "source_service": "service-a",
                "target_service": "service-b",
                "dependency_type": "api_call",
                "criticality": "high",
                "description": "Test dependency",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.business_impact_advanced_router import _save_dependency_to_db

            _save_dependency_to_db(db, dependency_data)

            # Verify database has the record
            retrieved = db.query(BusinessImpactDependencyDB).filter(
                BusinessImpactDependencyDB.id == dependency_data["id"]
            ).first()
            assert retrieved is not None
            assert retrieved.source_service == "service-a"
            assert retrieved.target_service == "service-b"

            # Clean up
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()

    def test_save_report_to_db(self):
        """测试保存报告到数据库"""
        db = get_session()
        try:
            report_data = {
                "id": f"RPT-TEST-{uuid.uuid4().hex[:8]}",
                "title": "Test Report",
                "service_names": ["service-a", "service-b"],
                "time_range": "24h",
                "include_recommendations": True,
                "summary": {"total_services": 2},
                "service_data": [],
                "recommendations": [],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.business_impact_advanced_router import _save_report_to_db

            _save_report_to_db(db, report_data)

            # Verify database has the record
            retrieved = db.query(BusinessImpactReportDB).filter(
                BusinessImpactReportDB.id == report_data["id"]
            ).first()
            assert retrieved is not None
            assert retrieved.title == "Test Report"

            # Clean up
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()


class TestChaosEngineeringDualWrite:
    """混沌工程双写逻辑测试"""

    def test_save_experiment_to_db(self):
        """测试保存实验到数据库"""
        db = get_session()
        try:
            experiment_data = {
                "id": f"EXP-TEST-{uuid.uuid4().hex[:8]}",
                "name": "Test Experiment",
                "description": "Test experiment description",
                "experiment_type": "latency_injection",
                "parameters": {"delay_ms": 500},
                "severity": "medium",
                "status": "pending",
                "tags": ["network", "test"],
                "result": None,
                "error": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.chaos_advanced_router import _save_experiment_to_db

            _save_experiment_to_db(db, experiment_data)

            # Verify database has the record
            retrieved = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == experiment_data["id"]
            ).first()
            assert retrieved is not None
            assert retrieved.name == "Test Experiment"
            assert retrieved.status == "pending"

            # Clean up
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()

    def test_save_scenario_to_db(self):
        """测试保存场景到数据库"""
        db = get_session()
        try:
            scenario_data = {
                "id": f"SCN-TEST-{uuid.uuid4().hex[:8]}",
                "name": "Test Scenario",
                "description": "Test scenario description",
                "fault_types": ["network_latency", "disk_failure"],
                "target_services": ["service-a", "service-b"],
                "duration_seconds": 300,
                "auto_rollback": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.chaos_advanced_router import _save_scenario_to_db

            _save_scenario_to_db(db, scenario_data)

            # Verify database has the record
            retrieved = db.query(ChaosScenarioDB).filter(
                ChaosScenarioDB.id == scenario_data["id"]
            ).first()
            assert retrieved is not None
            assert retrieved.name == "Test Scenario"

            # Clean up
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()

    def test_save_fault_to_db(self):
        """测试保存故障到数据库"""
        db = get_session()
        try:
            fault_data = {
                "id": f"FLT-TEST-{uuid.uuid4().hex[:8]}",
                "fault_type": "network_latency",
                "target": "service-a",
                "parameters": {"delay_ms": 500},
                "severity": "high",
                "status": "pending",
                "result": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }

            from api.chaos_advanced_router import _save_fault_to_db

            _save_fault_to_db(db, fault_data)

            # Verify database has the record
            retrieved = db.query(ChaosFaultDB).filter(
                ChaosFaultDB.id == fault_data["id"]
            ).first()
            assert retrieved is not None
            assert retrieved.fault_type == "network_latency"
            assert retrieved.target == "service-a"

            # Clean up
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()


class TestDualWriteErrorHandling:
    """双写错误处理测试"""

    def test_database_error_fallback(self):
        """测试数据库错误时的回退行为"""
        from api.business_impact_advanced_router import _save_analysis_to_db
        from fastapi import HTTPException

        db = get_session()
        try:
            # Test with invalid data that should cause database error
            invalid_data = {
                "id": "INVALID-ID",
                "service_name": None,  # This should cause an error
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

            # This should raise an HTTPException
            with pytest.raises(HTTPException):
                _save_analysis_to_db(db, invalid_data)
        finally:
            db.close()

    def test_json_file_persistence(self):
        """测试JSON文件持久化仍然工作"""
        from api.business_impact_advanced_router import _save_json_file, _load_json_file
        from pathlib import Path
        import tempfile
        import os

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = Path(f.name)
            test_data = [{"id": "test-1", "name": "Test"}]
            json.dump(test_data, f)

        try:
            # Test save
            new_data = [{"id": "test-2", "name": "Test 2"}]
            _save_json_file(temp_file, new_data)

            # Test load
            loaded = _load_json_file(temp_file)
            assert len(loaded) == 1
            assert loaded[0]["id"] == "test-2"
        finally:
            # Clean up
            if temp_file.exists():
                os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])