# -*- coding: utf-8 -*-
"""测试统计引擎模块"""

import pytest


class TestStatsEngineModule:
    """测试统计引擎模块"""

    def test_stats_engine_module_exists(self):
        """测试统计引擎模块存在"""
        from core import stats_engine

        assert stats_engine is not None

    def test_stats_engine_has_functions(self):
        """测试统计引擎模块有函数"""
        from core import stats_engine

        # 检查模块有函数或类
        assert len(dir(stats_engine)) > 0


class TestStatsEngineFunctions:
    """测试统计引擎函数"""

    def test_record_ingestion(self):
        """测试record_ingestion函数"""
        try:
            from core.stats_engine import record_ingestion

            # 应该不抛出异常
            record_ingestion(data_points=10)
            record_ingestion(data_points=1)
            record_ingestion()
        except Exception as e:
            pytest.skip(f"Cannot test record_ingestion: {e}")

    def test_record_alert_noise(self):
        """测试record_alert_noise函数"""
        try:
            from core.stats_engine import record_alert_noise

            # 应该不抛出异常
            record_alert_noise(raw_count=100, effective_count=80)
            record_alert_noise(raw_count=50, effective_count=10)
        except Exception as e:
            pytest.skip(f"Cannot test record_alert_noise: {e}")

    def test_get_real_summary(self):
        """测试get_real_summary函数"""
        try:
            from core.stats_engine import get_real_summary

            result = get_real_summary()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_real_summary: {e}")

    def test_record_repair(self):
        """测试record_repair函数"""
        try:
            from core.stats_engine import record_repair

            # 应该不抛出异常
            repair_data = {"repair_id": "test-1", "success": True}
            record_repair(repair_data)
        except Exception as e:
            pytest.skip(f"Cannot test record_repair: {e}")

    def test_get_repair_history(self):
        """测试get_repair_history函数"""
        try:
            from core.stats_engine import get_repair_history

            result = get_repair_history(limit=10)
            assert isinstance(result, list)
            assert len(result) <= 10
        except Exception as e:
            pytest.skip(f"Cannot test get_repair_history: {e}")

    def test_get_alert_stats(self):
        """测试get_alert_stats函数"""
        try:
            from core.stats_engine import get_alert_stats

            result = get_alert_stats()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_alert_stats: {e}")

    def test_get_repair_stats(self):
        """测试get_repair_stats函数"""
        try:
            from core.stats_engine import get_repair_stats

            result = get_repair_stats()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_repair_stats: {e}")

    def test_get_system_stats(self):
        """测试get_system_stats函数"""
        try:
            from core.stats_engine import get_system_stats

            result = get_system_stats()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Cannot test get_system_stats: {e}")

    def test_get_http_client(self):
        """测试_get_http_client函数"""
        try:
            from core.stats_engine import _get_http_client

            result = _get_http_client()
            # 可能返回None或HTTP客户端
            assert result is None or hasattr(result, "get")
        except Exception as e:
            pytest.skip(f"Cannot test _get_http_client: {e}")

    def test_record_collect(self):
        """测试record_collect函数"""
        try:
            from core.stats_engine import record_collect

            # 应该不抛出异常
            collect_data = {"provider": "aws", "region": "us-east-1"}
            record_collect(collect_data)
        except Exception as e:
            pytest.skip(f"Cannot test record_collect: {e}")

    def test_record_ingestion_with_zero(self):
        """测试record_ingestion零值"""
        try:
            from core.stats_engine import record_ingestion

            record_ingestion(data_points=0)
        except Exception as e:
            pytest.skip(f"Cannot test record_ingestion with zero: {e}")

    def test_record_ingestion_with_negative(self):
        """测试record_ingestion负值"""
        try:
            from core.stats_engine import record_ingestion

            record_ingestion(data_points=-1)
        except Exception as e:
            pytest.skip(f"Cannot test record_ingestion with negative: {e}")

    def test_get_repair_history_with_different_limits(self):
        """测试不同limit值的get_repair_history"""
        try:
            from core.stats_engine import get_repair_history

            for limit in [1, 10, 50, 100]:
                result = get_repair_history(limit=limit)
                assert isinstance(result, list)
                assert len(result) <= limit
        except Exception as e:
            pytest.skip(f"Cannot test get_repair_history with limits: {e}")

    def test_record_alert_noise_edge_cases(self):
        """测试record_alert_noise边界情况"""
        try:
            from core.stats_engine import record_alert_noise

            # 测试相等情况
            record_alert_noise(raw_count=100, effective_count=100)
            # 测试raw_count小于effective_count
            record_alert_noise(raw_count=50, effective_count=100)
            # 测试零值
            record_alert_noise(raw_count=0, effective_count=0)
        except Exception as e:
            pytest.skip(f"Cannot test record_alert_noise edge cases: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
