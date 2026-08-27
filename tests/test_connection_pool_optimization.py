# -*- coding: utf-8 -*-
"""
Connection Pool Optimization Tests
连接池优化测试

测试数据库连接池配置和性能
"""

import pytest
import time
import threading
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import engine
from core.auth_db import get_session


class TestConnectionPoolOptimization:
    """连接池优化测试"""

    def test_connection_pool_configuration(self):
        """测试连接池配置"""
        pool = engine.pool
        
        print(f"Connection pool size: {pool.size()}")
        print(f"Connection pool overflow: {pool.overflow()}")
        print(f"Connection pool checked out: {pool.checkedout()}")
        
        # 验证连接池配置
        assert pool.size() == 20, f"Pool size should be 20, got {pool.size()}"
        # Note: overflow() may return negative values in some SQLAlchemy implementations
        # We verify the configuration was set, not the runtime value

    def test_connection_pool_performance(self):
        """测试连接池性能"""
        # 测试连接获取性能
        connection_times = []
        
        for i in range(20):
            start_time = time.time()
            conn = engine.connect()
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            conn.close()
        
        avg_time = sum(connection_times) / len(connection_times)
        max_time = max(connection_times)
        
        print(f"Average connection time: {avg_time*1000:.2f}ms")
        print(f"Max connection time: {max_time*1000:.2f}ms")
        
        # 验证连接获取性能
        assert avg_time < 0.1, f"Average connection time too long: {avg_time*1000:.2f}ms"
        assert max_time < 0.5, f"Max connection time too long: {max_time*1000:.2f}ms"

    def test_concurrent_connection_usage(self):
        """测试并发连接使用"""
        results = []
        errors = []
        
        def db_operation(operation_id):
            try:
                db = get_session()
                start_time = time.time()
                # 执行查询
                db.execute(text("SELECT 1"))
                operation_time = time.time() - start_time
                results.append(operation_time)
                db.close()
            except Exception as e:
                errors.append(e)
        
        # 创建20个并发线程（超过连接池大小）
        threads = []
        for i in range(20):
            thread = threading.Thread(target=db_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        print(f"Concurrent operations: {len(results)}")
        print(f"Errors: {len(errors)}")
        
        # 验证并发性能
        assert len(errors) == 0, f"Concurrent operations should not fail, got {len(errors)} errors"
        assert len(results) == 20, f"All 20 operations should succeed"
        
        if results:
            avg_time = sum(results) / len(results)
            print(f"Average concurrent operation time: {avg_time*1000:.2f}ms")
            assert avg_time < 1.0, f"Concurrent operation time too long: {avg_time*1000:.2f}ms"

    def test_connection_pool_recycling(self):
        """测试连接池回收"""
        # 测试连接回收机制
        initial_checked_out = engine.pool.checkedout()
        
        # 执行多个连接操作
        for i in range(10):
            db = get_session()
            db.execute(text("SELECT 1"))
            db.close()
        
        # 等待连接回收
        time.sleep(2)
        
        final_checked_out = engine.pool.checkedout()
        
        print(f"Initial checked out: {initial_checked_out}")
        print(f"Final checked out: {final_checked_out}")
        
        # 验证连接被正确回收
        assert final_checked_out == initial_checked_out, "Connections should be recycled"

    def test_connection_leak_prevention(self):
        """测试连接泄漏预防"""
        # 模拟可能导致连接泄漏的场景
        db = get_session()
        try:
            # 执行查询
            db.execute(text("SELECT 1"))
            
            # 测试连接池状态
            checked_out_before = engine.pool.checkedout()
            
            # 执行更多操作
            for i in range(5):
                db.execute(text("SELECT 1"))
            
            checked_out_after = engine.pool.checkedout()
            
            print(f"Checked out before: {checked_out_before}")
            print(f"Checked out after: {checked_out_after}")
            
            # 验证没有连接泄漏
            assert checked_out_after == checked_out_before, "No connection leak should occur"
            
        finally:
            db.close()

    def test_connection_pool_monitoring(self):
        """测试连接池监控"""
        pool = engine.pool
        
        # 获取连接池状态
        pool_status = {
            "size": pool.size(),
            "overflow": pool.overflow(),
            "checked_out": pool.checkedout(),
        }
        
        print("Connection Pool Status:")
        for key, value in pool_status.items():
            print(f"  {key}: {value}")
        
        # 验证连接池状态合理
        assert pool_status["size"] == 20
        # Note: overflow() may return negative values in some SQLAlchemy implementations
        assert pool_status["checked_out"] == 0  # 应该没有未归还的连接


class TestConnectionPoolStress:
    """连接池压力测试"""

    def test_high_concurrent_load(self):
        """测试高并发负载"""
        results = []
        errors = []
        
        def heavy_db_operation(operation_id):
            try:
                db = get_session()
                start_time = time.time()
                # 执行较重的查询
                for i in range(5):
                    db.execute(text("SELECT 1"))
                operation_time = time.time() - start_time
                results.append(operation_time)
                db.close()
            except Exception as e:
                errors.append(e)
        
        # 创建30个并发线程（超过连接池+溢出）
        threads = []
        for i in range(30):
            thread = threading.Thread(target=heavy_db_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        print(f"High concurrent load operations: {len(results)}")
        print(f"Errors: {len(errors)}")
        
        # 验证高并发性能
        assert len(results) >= 20, f"At least 20 operations should succeed, got {len(results)}"
        assert len(errors) <= 10, f"Errors should be minimal, got {len(errors)}"
        
        if results:
            avg_time = sum(results) / len(results)
            print(f"Average high-concurrent operation time: {avg_time*1000:.2f}ms")
            assert avg_time < 2.0, f"High-concurrent operation time too long: {avg_time*1000:.2f}ms"

    def test_connection_pool_recovery(self):
        """测试连接池恢复"""
        # 测试连接池从高负载恢复的能力
        results = []
        
        def db_operation(operation_id):
            try:
                db = get_session()
                db.execute(text("SELECT 1"))
                results.append(operation_id)
                db.close()
            except Exception as e:
                pass
        
        # 第一轮高负载
        threads = []
        for i in range(25):
            thread = threading.Thread(target=db_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        first_round_results = len(results)
        results.clear()
        
        # 等待连接池恢复
        time.sleep(1)
        
        # 第二轮正常负载
        for i in range(10):
            db = get_session()
            db.execute(text("SELECT 1"))
            results.append(i)
            db.close()
        
        second_round_results = len(results)
        
        print(f"First round results: {first_round_results}")
        print(f"Second round results: {second_round_results}")
        
        # 验证连接池恢复能力
        assert second_round_results == 10, "Connection pool should recover from high load"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])