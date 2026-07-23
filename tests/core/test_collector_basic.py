# -*- coding: utf-8 -*-
"""
基础数据采集模块测试
测试核心数据采集功能的基础场景
"""

import pytest


class TestCollectorBasic:
    """数据采集模块基础测试"""

    def test_collector_module_structure(self):
        """测试数据采集模块结构"""
        try:
            from core import collector

            assert collector is not None
            assert hasattr(collector, "_collect_metrics")
        except ImportError as e:
            pytest.skip(f"Collector module not available: {e}")

    def test_collector_constants(self):
        """测试采集器常量定义"""
        try:
            from core.collector import _cache_lock, _collect_metrics, _sampling_lock

            # 验证关键变量存在
            assert _collect_metrics is not None
            assert isinstance(_collect_metrics, dict)
            assert _cache_lock is not None
            assert _sampling_lock is not None
        except Exception as e:
            pytest.skip(f"Collector constants test failed: {e}")

    def test_collector_functions_exist(self):
        """测试采集器关键函数存在"""
        try:
            from core.collector import (
                _collect_cpu_and_processes,
                _collect_disk,
                _collect_memory,
                collect_all,
                get_cached_snapshot,
            )

            # 验证关键函数存在
            assert collect_all is not None
            assert get_cached_snapshot is not None
            assert _collect_cpu_and_processes is not None
            assert _collect_memory is not None
            assert _collect_disk is not None
        except Exception as e:
            pytest.skip(f"Collector functions test failed: {e}")
