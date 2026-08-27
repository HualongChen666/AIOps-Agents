# -*- coding: utf-8 -*-
"""
Database Migration Tests
数据库迁移测试

测试Alembic迁移脚本的正确性和完整性
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from core.database import engine, SessionLocal
from core.models import (
    BusinessImpactAnalysisDB,
    BusinessImpactDependencyDB,
    BusinessImpactReportDB,
    ChaosExperimentDB,
    ChaosScenarioDB,
    ChaosFaultDB,
)


class TestBusinessImpactMigration:
    """业务影响迁移测试"""

    def test_business_impact_analysis_table_exists(self):
        """测试业务影响分析表是否存在"""
        inspector = inspect(engine)
        assert "business_impact_analysis" in inspector.get_table_names()

    def test_business_impact_analysis_columns(self):
        """测试业务影响分析表列结构"""
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("business_impact_analysis")]
        expected_columns = [
            "id",
            "service_name",
            "analysis_type",
            "time_range",
            "include_dependencies",
            "include_ux_metrics",
            "status",
            "result",
            "error",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in columns

    def test_business_impact_dependency_table_exists(self):
        """测试业务影响依赖关系表是否存在"""
        inspector = inspect(engine)
        assert "business_impact_dependencies" in inspector.get_table_names()

    def test_business_impact_dependency_columns(self):
        """测试业务影响依赖关系表列结构"""
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("business_impact_dependencies")]
        expected_columns = [
            "id",
            "source_service",
            "target_service",
            "dependency_type",
            "criticality",
            "description",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in columns

    def test_business_impact_report_table_exists(self):
        """测试业务影响报告表是否存在"""
        inspector = inspect(engine)
        assert "business_impact_reports" in inspector.get_table_names()

    def test_business_impact_report_columns(self):
        """测试业务影响报告表列结构"""
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("business_impact_reports")]
        expected_columns = [
            "id",
            "title",
            "service_names",
            "time_range",
            "include_recommendations",
            "summary",
            "service_data",
            "recommendations",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in columns


class TestChaosEngineeringMigration:
    """混沌工程迁移测试"""

    def test_chaos_experiment_table_exists(self):
        """测试混沌实验表是否存在"""
        inspector = inspect(engine)
        assert "chaos_experiments" in inspector.get_table_names()

    def test_chaos_experiment_columns(self):
        """测试混沌实验表列结构"""
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("chaos_experiments")]
        expected_columns = [
            "id",
            "name",
            "description",
            "experiment_type",
            "parameters",
            "severity",
            "status",
            "tags",
            "result",
            "error",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in columns

    def test_chaos_scenario_table_exists(self):
        """测试混沌场景表是否存在"""
        inspector = inspect(engine)
        assert "chaos_scenarios" in inspector.get_table_names()

    def test_chaos_scenario_columns(self):
        """测试混沌场景表列结构"""
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("chaos_scenarios")]
        expected_columns = [
            "id",
            "name",
            "description",
            "fault_types",
            "target_services",
            "duration_seconds",
            "auto_rollback",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in columns

    def test_chaos_fault_table_exists(self):
        """测试混沌故障表是否存在"""
        inspector = inspect(engine)
        assert "chaos_faults" in inspector.get_table_names()

    def test_chaos_fault_columns(self):
        """测试混沌故障表列结构"""
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("chaos_faults")]
        expected_columns = [
            "id",
            "fault_type",
            "target",
            "parameters",
            "severity",
            "status",
            "result",
            "created_at",
            "updated_at",
        ]
        for col in expected_columns:
            assert col in columns


class TestDatabaseCRUD:
    """数据库CRUD操作测试"""

    def test_create_business_impact_analysis(self):
        """测试创建业务影响分析记录"""
        import uuid
        db = SessionLocal()
        try:
            unique_id = f"BIA-TEST-{uuid.uuid4().hex[:8]}"
            analysis = BusinessImpactAnalysisDB(
                id=unique_id,
                service_name="test-service",
                analysis_type="full",
                time_range="1h",
                include_dependencies=True,
                include_ux_metrics=True,
                status="pending",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)

            retrieved = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == unique_id
            ).first()
            assert retrieved is not None
            assert retrieved.service_name == "test-service"
            assert retrieved.status == "pending"
            
            # Clean up
            db.delete(analysis)
            db.commit()
        finally:
            db.close()

    def test_create_chaos_experiment(self):
        """测试创建混沌实验记录"""
        import uuid
        db = SessionLocal()
        try:
            unique_id = f"EXP-TEST-{uuid.uuid4().hex[:8]}"
            experiment = ChaosExperimentDB(
                id=unique_id,
                name="Test Experiment",
                description="Test experiment for migration",
                experiment_type="latency_injection",
                parameters={"delay_ms": 500},
                severity="medium",
                status="pending",
            )
            db.add(experiment)
            db.commit()
            db.refresh(experiment)

            retrieved = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == unique_id
            ).first()
            assert retrieved is not None
            assert retrieved.name == "Test Experiment"
            assert retrieved.status == "pending"
            
            # Clean up
            db.delete(experiment)
            db.commit()
        finally:
            db.close()


class TestIndexCreation:
    """索引创建测试"""

    def test_business_impact_analysis_indexes(self):
        """测试业务影响分析表索引"""
        inspector = inspect(engine)
        indexes = inspector.get_indexes("business_impact_analysis")
        index_names = [idx["name"] for idx in indexes]
        assert "idx_business_impact_analysis_service_name" in index_names
        assert "idx_business_impact_analysis_status" in index_names
        assert "idx_business_impact_analysis_created_at" in index_names

    def test_chaos_experiment_indexes(self):
        """测试混沌实验表索引"""
        inspector = inspect(engine)
        indexes = inspector.get_indexes("chaos_experiments")
        index_names = [idx["name"] for idx in indexes]
        assert "idx_chaos_experiments_name" in index_names
        assert "idx_chaos_experiments_status" in index_names
        assert "idx_chaos_experiments_severity" in index_names
        assert "idx_chaos_experiments_created_at" in index_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])