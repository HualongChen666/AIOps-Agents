# -*- coding: utf-8 -*-
"""
测试业务影响高级路由数据库迁移
验证所有端点都使用数据库存储，不再使用JSON文件
"""

import pytest
from sqlalchemy.orm import Session
from core.models import BusinessImpactAnalysisDB, BusinessImpactDependencyDB, BusinessImpactReportDB
from core.auth_db import get_session


class TestBusinessImpactMigration:
    """测试业务影响数据库迁移"""

    def test_database_tables_exist(self):
        """验证数据库表存在"""
        db = get_session()
        try:
            # 检查表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            assert "business_impact_analysis" in tables, "business_impact_analysis表不存在"
            assert "business_impact_dependencies" in tables, "business_impact_dependencies表不存在"
            assert "business_impact_reports" in tables, "business_impact_reports表不存在"
        finally:
            db.close()

    def test_no_json_file_references(self):
        """验证代码中不再引用JSON文件"""
        import api.business_impact_advanced_router as router_module
        import inspect
        
        # 读取路由模块的源代码
        source = inspect.getsource(router_module)
        
        # 检查是否还有JSON文件引用
        assert "ANALYSIS_FILE" not in source, "代码中仍有ANALYSIS_FILE引用"
        assert "DEPENDENCIES_FILE" not in source, "代码中仍有DEPENDENCIES_FILE引用"
        assert "REPORTS_FILE" not in source, "代码中仍有REPORTS_FILE引用"
        assert "_load_json_file" not in source, "代码中仍有_load_json_file函数"
        assert "_save_json_file" not in source, "代码中仍有_save_json_file函数"

    def test_database_models_match(self):
        """验证数据库模型与预期一致"""
        db = get_session()
        try:
            # 检查BusinessImpactAnalysisDB的字段
            analysis = BusinessImpactAnalysisDB.__table__.columns
            required_fields = ['id', 'service_name', 'analysis_type', 'time_range', 
                            'include_dependencies', 'include_ux_metrics', 'status']
            for field in required_fields:
                assert field in [c.name for c in analysis], f"BusinessImpactAnalysisDB缺少字段: {field}"
            
            # 检查BusinessImpactDependencyDB的字段
            dependency = BusinessImpactDependencyDB.__table__.columns
            required_fields = ['id', 'source_service', 'target_service', 'dependency_type', 'criticality']
            for field in required_fields:
                assert field in [c.name for c in dependency], f"BusinessImpactDependencyDB缺少字段: {field}"
            
            # 检查BusinessImpactReportDB的字段
            report = BusinessImpactReportDB.__table__.columns
            required_fields = ['id', 'title', 'service_names', 'time_range', 'include_recommendations']
            for field in required_fields:
                assert field in [c.name for c in report], f"BusinessImpactReportDB缺少字段: {field}"
        finally:
            db.close()

    def test_create_analysis_uses_database(self):
        """测试创建分析使用数据库"""
        db = get_session()
        try:
            # 创建测试分析
            analysis = BusinessImpactAnalysisDB(
                id="TEST-ANALYSIS-001",
                service_name="test-service",
                analysis_type="full",
                time_range="1h",
                include_dependencies=True,
                include_ux_metrics=True,
                status="pending"
            )
            db.add(analysis)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_analysis = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == "TEST-ANALYSIS-001"
            ).first()
            
            assert saved_analysis is not None, "分析未保存到数据库"
            assert saved_analysis.service_name == "test-service", "服务名称不匹配"
            assert saved_analysis.status == "pending", "状态不匹配"
            
            # 清理测试数据
            db.delete(saved_analysis)
            db.commit()
        finally:
            db.close()

    def test_create_dependency_uses_database(self):
        """测试创建依赖关系使用数据库"""
        db = get_session()
        try:
            # 创建测试依赖关系
            dependency = BusinessImpactDependencyDB(
                id="TEST-DEP-001",
                source_service="service-a",
                target_service="service-b",
                dependency_type="api_call",
                criticality="high"
            )
            db.add(dependency)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_dependency = db.query(BusinessImpactDependencyDB).filter(
                BusinessImpactDependencyDB.id == "TEST-DEP-001"
            ).first()
            
            assert saved_dependency is not None, "依赖关系未保存到数据库"
            assert saved_dependency.source_service == "service-a", "源服务不匹配"
            assert saved_dependency.target_service == "service-b", "目标服务不匹配"
            
            # 清理测试数据
            db.delete(saved_dependency)
            db.commit()
        finally:
            db.close()

    def test_create_report_uses_database(self):
        """测试创建报告使用数据库"""
        db = get_session()
        try:
            # 创建测试报告
            report = BusinessImpactReportDB(
                id="TEST-RPT-001",
                title="Test Report",
                service_names=["service-a", "service-b"],
                time_range="1h",
                include_recommendations=True
            )
            db.add(report)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_report = db.query(BusinessImpactReportDB).filter(
                BusinessImpactReportDB.id == "TEST-RPT-001"
            ).first()
            
            assert saved_report is not None, "报告未保存到数据库"
            assert saved_report.title == "Test Report", "报告名称不匹配"
            
            # 清理测试数据
            db.delete(saved_report)
            db.commit()
        finally:
            db.close()

    def test_no_dual_write_functions(self):
        """验证没有双写函数"""
        import api.business_impact_advanced_router as router_module
        import inspect
        
        # 读取路由模块的源代码
        source = inspect.getsource(router_module)
        
        # 检查是否还有双写函数
        assert "_save_analysis_to_db" not in source, "代码中仍有_save_analysis_to_db函数"
        assert "_save_dependency_to_db" not in source, "代码中仍有_save_dependency_to_db函数"
        assert "_save_report_to_db" not in source, "代码中仍有_save_report_to_db函数"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])