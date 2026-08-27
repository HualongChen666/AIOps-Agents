# -*- coding: utf-8 -*-
"""
AI Advanced Router Database Integration Tests
AI高级路由数据库集成测试

验证AI高级路由完全迁移到数据库存储，移除内存字典fallback
"""

import pytest
from sqlalchemy.orm import Session

from core.auth_db import get_session
from core.models import (
    AIFineTuningJobDB,
    AIRunbookDB,
    AIAnalysisReportDB,
    AIKnowledgeBaseDB,
)


class TestAIFineTuningDB:
    """AI微调数据库测试"""

    def test_fine_tuning_job_db_operations(self):
        """测试微调任务数据库操作"""
        db = get_session()
        try:
            # 创建微调任务
            job = AIFineTuningJobDB(
                id="TEST-FINE-TUNING-001",
                model_name="test-model",
                dataset="test-dataset",
                status="pending",
                progress=0.0,
                job_metadata=None,
            )
            db.add(job)
            db.commit()

            # 查询微调任务
            retrieved = db.query(AIFineTuningJobDB).filter(
                AIFineTuningJobDB.id == "TEST-FINE-TUNING-001"
            ).first()
            assert retrieved is not None
            assert retrieved.model_name == "test-model"
            assert retrieved.status == "pending"

            # 更新微调任务
            retrieved.status = "completed"
            retrieved.progress = 100.0
            db.commit()

            # 验证更新
            updated = db.query(AIFineTuningJobDB).filter(
                AIFineTuningJobDB.id == "TEST-FINE-TUNING-001"
            ).first()
            assert updated.status == "completed"
            assert updated.progress == 100.0

            # 清理
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()


class TestAIRunbookDB:
    """AI运行手册数据库测试"""

    def test_runbook_db_operations(self):
        """测试运行手册数据库操作"""
        db = get_session()
        try:
            # 创建运行手册
            runbook = AIRunbookDB(
                id="TEST-RUNBOOK-001",
                title="Test Runbook",
                description="Test runbook for database migration",
                steps=["step1", "step2", "step3"],
                runbook_metadata=None,
            )
            db.add(runbook)
            db.commit()

            # 查询运行手册
            retrieved = db.query(AIRunbookDB).filter(
                AIRunbookDB.id == "TEST-RUNBOOK-001"
            ).first()
            assert retrieved is not None
            assert retrieved.title == "Test Runbook"
            assert len(retrieved.steps) == 3

            # 清理
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()


class TestAIAnalysisReportDB:
    """AI分析报告数据库测试"""

    def test_analysis_report_db_operations(self):
        """测试分析报告数据库操作"""
        db = get_session()
        try:
            # 创建分析报告
            report = AIAnalysisReportDB(
                id="TEST-REPORT-001",
                analysis_type="log_analysis",
                results={"anomalies": 5, "patterns": ["pattern1", "pattern2"]},
                report_metadata=None,
            )
            db.add(report)
            db.commit()

            # 查询分析报告
            retrieved = db.query(AIAnalysisReportDB).filter(
                AIAnalysisReportDB.id == "TEST-REPORT-001"
            ).first()
            assert retrieved is not None
            assert retrieved.analysis_type == "log_analysis"
            assert retrieved.results["anomalies"] == 5

            # 清理
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()


class TestAIKnowledgeBaseDB:
    """AI知识库数据库测试"""

    def test_knowledge_base_db_operations(self):
        """测试知识库数据库操作"""
        db = get_session()
        try:
            # 创建知识库
            kb = AIKnowledgeBaseDB(
                id="TEST-KB-001",
                kb_name="Test Knowledge Base",
                kb_type="vector",
                document_count=100,
                kb_metadata=None,
            )
            db.add(kb)
            db.commit()

            # 查询知识库
            retrieved = db.query(AIKnowledgeBaseDB).filter(
                AIKnowledgeBaseDB.id == "TEST-KB-001"
            ).first()
            assert retrieved is not None
            assert retrieved.kb_name == "Test Knowledge Base"
            assert retrieved.document_count == 100

            # 清理
            db.delete(retrieved)
            db.commit()
        finally:
            db.close()


class TestAIRouterIntegration:
    """AI路由集成测试"""

    def test_no_memory_fallback(self):
        """测试没有内存字典fallback"""
        # 验证内存字典已被移除
        from api.ai_advanced_router import _get_fine_tuning_jobs, _set_fine_tuning_job

        # 这些函数现在应该只接受db参数，没有Optional
        import inspect
        sig = inspect.signature(_get_fine_tuning_jobs)
        params = list(sig.parameters.keys())
        
        # 应该只有db参数，没有Optional
        assert "db" in params
        assert len(params) == 1  # 只有db参数

    def test_database_only_operations(self):
        """测试仅数据库操作"""
        db = get_session()
        try:
            # 测试数据库操作函数
            from api.ai_advanced_router import _get_fine_tuning_jobs, _set_fine_tuning_job
            from api.ai_advanced_router import FineTuningJobResponse, JobStatus

            # 创建测试数据
            job = FineTuningJobResponse(
                id="TEST-INTEGRATION-001",
                base_model="gpt-3.5-turbo",
                model_name="integration-test-model",
                status=JobStatus.PENDING,
                progress=0.0,
                epoch=0,
                total_epochs=10,
                loss=0.0,
                learning_rate=0.001,
                created_at="2024-01-01T00:00:00Z",
            )

            # 保存到数据库
            _set_fine_tuning_job(job, db)

            # 从数据库读取
            jobs = _get_fine_tuning_jobs(db)
            assert "TEST-INTEGRATION-001" in jobs
            assert jobs["TEST-INTEGRATION-001"].model_name == "integration-test-model"

            # 清理
            db_job = db.query(AIFineTuningJobDB).filter(
                AIFineTuningJobDB.id == "TEST-INTEGRATION-001"
            ).first()
            if db_job:
                db.delete(db_job)
                db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])