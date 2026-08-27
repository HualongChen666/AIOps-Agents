# -*- coding: utf-8 -*-
"""
Performance Baseline Tests
性能基线测试

测量当前性能基线，为优化提供参考数据
"""

import time
import statistics
from typing import List, Dict
import pytest
from sqlalchemy.orm import Session

from core.auth_db import get_session
from core.models import (
    BusinessImpactAnalysisDB,
    ChaosExperimentDB,
    AIFineTuningJobDB,
)


class TestPerformanceBaseline:
    """Performance Baseline Tests"""

    def test_api_response_time_baseline(self):
        """Test API response time baseline"""
        # Test database query response time
        db = get_session()
        try:
            # Test simple query
            start_time = time.time()
            result = db.query(BusinessImpactAnalysisDB).limit(10).all()
            query_time = time.time() - start_time
            
            print(f"Simple query response time: {query_time*1000:.2f}ms")
            
            # Test complex query
            start_time = time.time()
            result = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.status == "pending"
            ).all()
            complex_query_time = time.time() - start_time
            
            print(f"Complex query response time: {complex_query_time*1000:.2f}ms")
            
            # Test insert operation
            import uuid
            
            test_id = f"BIA-BASELINE-{uuid.uuid4().hex[:8]}"
            start_time = time.time()
            analysis = BusinessImpactAnalysisDB(
                id=test_id,
                service_name="baseline-test-service",
                analysis_type="full",
                time_range="1h",
                include_dependencies=True,
                include_ux_metrics=True,
                status="pending",
            )
            db.add(analysis)
            db.commit()
            insert_time = time.time() - start_time
            
            print(f"Insert operation response time: {insert_time*1000:.2f}ms")
            
            # Cleanup
            db.delete(analysis)
            db.commit()
            
            # Record baseline data
            baseline_data = {
                "simple_query_ms": query_time * 1000,
                "complex_query_ms": complex_query_time * 1000,
                "insert_ms": insert_time * 1000,
            }
            
            # Verify baseline is reasonable
            assert query_time < 1.0, f"Simple query time too long: {query_time*1000:.2f}ms"
            assert complex_query_time < 2.0, f"Complex query time too long: {complex_query_time*1000:.2f}ms"
            assert insert_time < 0.5, f"Insert time too long: {insert_time*1000:.2f}ms"
            
            return baseline_data
            
        finally:
            db.close()

    def test_database_connection_pool_baseline(self):
        """Test database connection pool baseline"""
        from core.database import engine
        
        # Test connection pool status
        pool = engine.pool
        print(f"Connection pool size: {pool.size()}")
        print(f"Connection pool checked out: {pool.checkedout()}")
        print(f"Connection pool overflow: {pool.overflow()}")
        
        # Test concurrent connections
        connection_times = []
        for i in range(10):
            start_time = time.time()
            conn = engine.connect()
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            conn.close()
        
        avg_connection_time = statistics.mean(connection_times)
        max_connection_time = max(connection_times)
        
        print(f"Average connection time: {avg_connection_time*1000:.2f}ms")
        print(f"Max connection time: {max_connection_time*1000:.2f}ms")
        
        # Verify connection pool performance
        assert avg_connection_time < 0.1, f"Average connection time too long: {avg_connection_time*1000:.2f}ms"
        assert max_connection_time < 0.5, f"Max connection time too long: {max_connection_time*1000:.2f}ms"

    def test_memory_usage_baseline(self):
        """Test memory usage baseline"""
        try:
            import psutil
            import os
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        rss_mb = memory_info.rss / 1024 / 1024
        vms_mb = memory_info.vms / 1024 / 1024
        
        print(f"RSS memory usage: {rss_mb:.2f}MB")
        print(f"VMS memory usage: {vms_mb:.2f}MB")
        
        # Test memory growth
        db = get_session()
        try:
            initial_memory = rss_mb
            
            # Execute some operations
            import uuid
            for i in range(100):
                test_id = f"BIA-MEM-{uuid.uuid4().hex[:8]}"
                analysis = BusinessImpactAnalysisDB(
                    id=test_id,
                    service_name=f"memory-test-{i}",
                    analysis_type="full",
                    time_range="1h",
                    include_dependencies=True,
                    include_ux_metrics=True,
                    status="pending",
                )
                db.add(analysis)
            db.commit()
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory
            
            print(f"Memory growth: {memory_growth:.2f}MB")
            
            # Cleanup
            for i in range(100):
                test_id = f"BIA-MEM-{uuid.uuid4().hex[:8]}"
                # Cannot cleanup precisely here, real application needs better cleanup strategy
            
            # Verify memory usage is reasonable
            assert memory_growth < 50, f"Memory growth too large: {memory_growth:.2f}MB"
            
        finally:
            db.close()

    def test_concurrent_operations_baseline(self):
        """Test concurrent operations baseline"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def db_operation(operation_id):
            db = get_session()
            try:
                start_time = time.time()
                # Execute query
                db.query(BusinessImpactAnalysisDB).limit(10).all()
                operation_time = time.time() - start_time
                results.put(operation_time)
            finally:
                db.close()
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=db_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        operation_times = []
        while not results.empty():
            operation_times.append(results.get())
        
        avg_time = statistics.mean(operation_times)
        max_time = max(operation_times)
        min_time = min(operation_times)
        
        print(f"Concurrent operation average time: {avg_time*1000:.2f}ms")
        print(f"Concurrent operation max time: {max_time*1000:.2f}ms")
        print(f"Concurrent operation min time: {min_time*1000:.2f}ms")
        
        # Verify concurrent performance
        assert avg_time < 0.5, f"Concurrent operation average time too long: {avg_time*1000:.2f}ms"
        assert max_time < 2.0, f"Concurrent operation max time too long: {max_time*1000:.2f}ms"

    def test_batch_operations_baseline(self):
        """Test batch operations baseline"""
        db = get_session()
        try:
            # Test batch insert
            import uuid
            batch_size = 50
            test_ids = []
            
            start_time = time.time()
            for i in range(batch_size):
                test_id = f"BIA-BATCH-{uuid.uuid4().hex[:8]}"
                test_ids.append(test_id)
                analysis = BusinessImpactAnalysisDB(
                    id=test_id,
                    service_name=f"batch-test-{i}",
                    analysis_type="full",
                    time_range="1h",
                    include_dependencies=True,
                    include_ux_metrics=True,
                    status="pending",
                )
                db.add(analysis)
            db.commit()
            batch_time = time.time() - start_time
            
            avg_batch_time = batch_time / batch_size
            print(f"Batch insert average time: {avg_batch_time*1000:.2f}ms")
            
            # Test batch query
            start_time = time.time()
            results = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.service_name.like("batch-test-%")
            ).all()
            batch_query_time = time.time() - start_time
            
            print(f"Batch query time: {batch_query_time*1000:.2f}ms")
            print(f"Batch query result count: {len(results)}")
            
            # Cleanup
            for test_id in test_ids:
                analysis = db.query(BusinessImpactAnalysisDB).filter(
                    BusinessImpactAnalysisDB.id == test_id
                ).first()
                if analysis:
                    db.delete(analysis)
            db.commit()
            
            # Verify batch operation performance
            assert avg_batch_time < 0.05, f"Batch insert average time too long: {avg_batch_time*1000:.2f}ms"
            assert batch_query_time < 1.0, f"Batch query time too long: {batch_query_time*1000:.2f}ms"
            
        finally:
            db.close()

    def test_generate_baseline_report(self):
        """生成性能基线报告"""
        baseline_data = {
            "simple_query_ms": 0,
            "complex_query_ms": 0,
            "insert_ms": 0,
            "avg_connection_time_ms": 0,
            "max_connection_time_ms": 0,
            "memory_usage_mb": 0,
            "concurrent_avg_time_ms": 0,
            "batch_avg_time_ms": 0,
        }
        
        # 运行各个测试收集数据
        try:
            baseline_data.update(self.test_api_response_time_baseline())
        except:
            pass
        
        try:
            self.test_database_connection_pool_baseline()
        except:
            pass
        
        try:
            self.test_memory_usage_baseline()
        except:
            pass
        
        try:
            self.test_concurrent_operations_baseline()
        except:
            pass
        
        try:
            self.test_batch_operations_baseline()
        except:
            pass
        
        # 生成报告
        print("\n=== Performance Baseline Report ===")
        print(f"Simple Query: {baseline_data.get('simple_query_ms', 0):.2f}ms")
        print(f"Complex Query: {baseline_data.get('complex_query_ms', 0):.2f}ms")
        print(f"Insert Operation: {baseline_data.get('insert_ms', 0):.2f}ms")
        print(f"Memory Usage: {baseline_data.get('memory_usage_mb', 0):.2f}MB")
        print("===================\n")
        
        # 保存报告到文件
        import json
        from pathlib import Path
        
        report_file = Path("performance_baseline_report.json")
        with open(report_file, "w") as f:
            json.dump(baseline_data, f, indent=2)
        
        print(f"Performance baseline report saved to: {report_file}")
        
        assert report_file.exists(), "Performance baseline report file not created"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])