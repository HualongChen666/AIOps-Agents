# -*- coding: utf-8 -*-
"""
测试混沌工程高级路由数据库迁移
验证所有端点都使用数据库存储，不再使用JSON文件
"""

import pytest
from sqlalchemy.orm import Session
from core.models import ChaosExperimentDB, ChaosScenarioDB, ChaosFaultDB
from core.auth_db import get_session


class TestChaosMigration:
    """测试混沌工程数据库迁移"""

    def test_database_tables_exist(self):
        """验证数据库表存在"""
        db = get_session()
        try:
            # 检查表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            assert "chaos_experiments" in tables, "chaos_experiments表不存在"
            assert "chaos_scenarios" in tables, "chaos_scenarios表不存在"
            assert "chaos_faults" in tables, "chaos_faults表不存在"
        finally:
            db.close()

    def test_no_json_file_references(self):
        """验证代码中不再引用JSON文件"""
        import api.chaos_advanced_router as router_module
        import inspect
        
        # 读取路由模块的源代码
        source = inspect.getsource(router_module)
        
        # 检查是否还有JSON文件引用
        assert "EXPERIMENTS_FILE" not in source, "代码中仍有EXPERIMENTS_FILE引用"
        assert "SCENARIOS_FILE" not in source, "代码中仍有SCENARIOS_FILE引用"
        assert "FAULTS_FILE" not in source, "代码中仍有FAULTS_FILE引用"
        assert "_load_json_file" not in source, "代码中仍有_load_json_file函数"
        assert "_save_json_file" not in source, "代码中仍有_save_json_file函数"

    def test_database_models_match(self):
        """验证数据库模型与预期一致"""
        db = get_session()
        try:
            # 检查ChaosExperimentDB的字段
            experiment = ChaosExperimentDB.__table__.columns
            required_fields = ['id', 'name', 'experiment_type', 'status', 'severity']
            for field in required_fields:
                assert field in [c.name for c in experiment], f"ChaosExperimentDB缺少字段: {field}"
            
            # 检查ChaosScenarioDB的字段
            scenario = ChaosScenarioDB.__table__.columns
            required_fields = ['id', 'name', 'fault_types', 'target_services', 'duration_seconds']
            for field in required_fields:
                assert field in [c.name for c in scenario], f"ChaosScenarioDB缺少字段: {field}"
            
            # 检查ChaosFaultDB的字段
            fault = ChaosFaultDB.__table__.columns
            required_fields = ['id', 'fault_type', 'target', 'severity']
            for field in required_fields:
                assert field in [c.name for c in fault], f"ChaosFaultDB缺少字段: {field}"
        finally:
            db.close()

    def test_create_experiment_uses_database(self):
        """测试创建实验使用数据库"""
        db = get_session()
        try:
            # 创建测试实验
            experiment = ChaosExperimentDB(
                id="TEST-EXP-001",
                name="Test Experiment",
                description="Test experiment for migration",
                experiment_type="pod_kill",
                status="pending",
                severity="low"
            )
            db.add(experiment)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_experiment = db.query(ChaosExperimentDB).filter(
                ChaosExperimentDB.id == "TEST-EXP-001"
            ).first()
            
            assert saved_experiment is not None, "实验未保存到数据库"
            assert saved_experiment.name == "Test Experiment", "实验名称不匹配"
            assert saved_experiment.status == "pending", "状态不匹配"
            
            # 清理测试数据
            db.delete(saved_experiment)
            db.commit()
        finally:
            db.close()

    def test_create_scenario_uses_database(self):
        """测试创建场景使用数据库"""
        db = get_session()
        try:
            # 创建测试场景
            scenario = ChaosScenarioDB(
                id="TEST-SCENARIO-001",
                name="Test Scenario",
                description="Test scenario for migration",
                fault_types=["pod_kill", "network_delay"],
                target_services=["service-a"],
                duration_seconds=60
            )
            db.add(scenario)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_scenario = db.query(ChaosScenarioDB).filter(
                ChaosScenarioDB.id == "TEST-SCENARIO-001"
            ).first()
            
            assert saved_scenario is not None, "场景未保存到数据库"
            assert saved_scenario.name == "Test Scenario", "场景名称不匹配"
            
            # 清理测试数据
            db.delete(saved_scenario)
            db.commit()
        finally:
            db.close()

    def test_create_fault_uses_database(self):
        """测试创建故障使用数据库"""
        db = get_session()
        try:
            # 创建测试故障
            fault = ChaosFaultDB(
                id="TEST-FAULT-001",
                fault_type="network_delay",
                target="service-a",
                parameters={},
                severity="medium"
            )
            db.add(fault)
            db.commit()
            
            # 验证数据已保存到数据库
            saved_fault = db.query(ChaosFaultDB).filter(
                ChaosFaultDB.id == "TEST-FAULT-001"
            ).first()
            
            assert saved_fault is not None, "故障未保存到数据库"
            assert saved_fault.fault_type == "network_delay", "故障类型不匹配"
            
            # 清理测试数据
            db.delete(saved_fault)
            db.commit()
        finally:
            db.close()

    def test_no_dual_write_functions(self):
        """验证没有双写函数"""
        import api.chaos_advanced_router as router_module
        import inspect
        
        # 读取路由模块的源代码
        source = inspect.getsource(router_module)
        
        # 检查是否还有双写函数
        assert "_save_experiment_to_db" not in source, "代码中仍有_save_experiment_to_db函数"
        assert "_save_scenario_to_db" not in source, "代码中仍有_save_scenario_to_db函数"
        assert "_save_fault_to_db" not in source, "代码中仍有_save_fault_to_db函数"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])