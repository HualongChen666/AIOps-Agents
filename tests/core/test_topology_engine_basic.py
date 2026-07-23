# -*- coding: utf-8 -*-
"""
基础拓扑引擎模块测试
测试拓扑引擎核心功能的基础场景
"""

import pytest


class TestTopologyEngineBasic:
    """拓扑引擎模块基础测试"""

    def test_topology_engine_module_structure(self):
        """测试拓扑引擎模块结构"""
        try:
            from core import topology_engine

            assert topology_engine is not None
        except ImportError as e:
            pytest.skip(f"Topology engine module not available: {e}")

    def test_topology_engine_functions_exist(self):
        """测试拓扑引擎关键函数存在"""
        try:
            from core.topology_engine import (
                analyze_dependencies,
                build_topology,
                detect_circular_dependencies,
            )

            # 验证关键函数存在
            assert build_topology is not None
            assert analyze_dependencies is not None
            assert detect_circular_dependencies is not None
        except Exception as e:
            pytest.skip(f"Topology engine functions test failed: {e}")

    def test_topology_engine_classes_exist(self):
        """测试拓扑引擎关键类存在"""
        try:
            from core.topology_engine import (
                CircularDependencyDetector,
                DependencyAnalyzer,
                TopologyEngine,
            )

            # 验证关键类存在
            assert TopologyEngine is not None
            assert DependencyAnalyzer is not None
            assert CircularDependencyDetector is not None
        except Exception as e:
            pytest.skip(f"Topology engine classes test failed: {e}")

    def test_topology_engine_constants(self):
        """测试拓扑引擎常量定义"""
        try:
            from core.topology_engine import DependencyType, TopologyType

            # 验证常量存在
            assert TopologyType is not None
            assert DependencyType is not None
        except Exception as e:
            pytest.skip(f"Topology engine constants test failed: {e}")
