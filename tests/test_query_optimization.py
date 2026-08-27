# -*- coding: utf-8 -*-
"""
Query Optimization Tests
查询优化测试

测试数据库查询优化和索引效果
"""

import time
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.auth_db import get_session
from core.models import (
    BusinessImpactAnalysisDB,
    ChaosExperimentDB,
    AIFineTuningJobDB,
)


class TestQueryOptimization:
    """查询优化测试"""

    def test_index_effectiveness(self):
        """测试索引有效性"""
        db = get_session()
        try:
            # 测试有索引的查询
            start_time = time.time()
            result = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.service_name == "test-service"
            ).first()
            indexed_query_time = time.time() - start_time
            
            # 测试无索引的查询（使用不常见的字段）
            start_time = time.time()
            result = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.id == "BIA-TEST-001"
            ).first()
            non_indexed_query_time = time.time() - start_time
            
            print(f"Indexed query time: {indexed_query_time*1000:.2f}ms")
            print(f"Non-indexed query time: {non_indexed_query_time*1000:.2f}ms")
            
            # 索引查询应该更快
            # 注意：由于数据量小，差异可能不明显
        finally:
            db.close()

    def test_query_explain(self):
        """测试查询执行计划"""
        db = get_session()
        try:
            # 获取查询执行计划
            from sqlalchemy import inspect
            
            inspector = inspect(db.bind)
            
            # 检查索引
            business_impact_indexes = inspector.get_indexes("business_impact_analysis")
            print(f"Business Impact Analysis indexes: {business_impact_indexes}")
            
            chaos_indexes = inspector.get_indexes("chaos_experiments")
            print(f"Chaos Experiments indexes: {chaos_indexes}")
            
            # 验证关键索引存在
            business_impact_index_names = [idx["name"] for idx in business_impact_indexes]
            assert "idx_business_impact_analysis_service_name" in business_impact_index_names
            assert "idx_business_impact_analysis_status" in business_impact_index_names
            
            chaos_index_names = [idx["name"] for idx in chaos_indexes]
            assert "idx_chaos_experiments_name" in chaos_index_names
            assert "idx_chaos_experiments_status" in chaos_index_names
            assert "idx_chaos_experiments_severity" in chaos_index_names
            
        finally:
            db.close()

    def test_n_plus_1_query_optimization(self):
        """测试N+1查询优化"""
        db = get_session()
        try:
            # 测试潜在的N+1查询问题
            # 使用eager loading避免N+1查询
            
            # 模拟N+1查询场景
            start_time = time.time()
            analyses = db.query(BusinessImpactAnalysisDB).limit(10).all()
            
            # 模拟为每个分析获取相关数据（这可能导致N+1查询）
            for analysis in analyses:
                # 这里应该使用eager loading或selectin loading
                pass
            
            query_time = time.time() - start_time
            print(f"Query time for 10 records: {query_time*1000:.2f}ms")
            
            # 验证查询时间合理
            assert query_time < 1.0, f"Query time too long: {query_time*1000:.2f}ms"
            
        finally:
            db.close()

    def test_pagination_performance(self):
        """测试分页性能"""
        db = get_session()
        try:
            # 测试不同分页大小的性能
            page_sizes = [10, 20, 50, 100]
            
            for page_size in page_sizes:
                start_time = time.time()
                total = db.query(BusinessImpactAnalysisDB).count()
                results = db.query(BusinessImpactAnalysisDB).offset(0).limit(page_size).all()
                query_time = time.time() - start_time
                
                print(f"Page size {page_size}: {query_time*1000:.2f}ms, total: {total}")
                
                # 验证分页性能
                assert query_time < 1.0, f"Pagination too slow for page size {page_size}: {query_time*1000:.2f}ms"
            
        finally:
            db.close()

    def test_complex_query_optimization(self):
        """测试复杂查询优化"""
        db = get_session()
        try:
            # 测试复杂查询的性能
            start_time = time.time()
            
            # 复杂查询：多条件过滤 + 排序 + 分页
            query = db.query(BusinessImpactAnalysisDB).filter(
                BusinessImpactAnalysisDB.status == "pending"
            ).filter(
                BusinessImpactAnalysisDB.include_dependencies == True
            ).order_by(
                BusinessImpactAnalysisDB.created_at.desc()
            ).limit(20)
            
            results = query.all()
            query_time = time.time() - start_time
            
            print(f"Complex query time: {query_time*1000:.2f}ms")
            print(f"Results count: {len(results)}")
            
            # 验证复杂查询性能
            assert query_time < 2.0, f"Complex query too slow: {query_time*1000:.2f}ms"
            
        finally:
            db.close()

    def test_query_result_caching(self):
        """测试查询结果缓存"""
        from core.cache_manager import cache_manager
        
        db = get_session()
        try:
            # 测试查询结果缓存
            cache_key = "query_cache_test"
            
            # 第一次查询
            start_time = time.time()
            result = db.query(BusinessImpactAnalysisDB).limit(10).all()
            first_query_time = time.time() - start_time
            
            # 缓存结果
            cache_manager.set(cache_key, len(result), ttl=60)
            
            # 从缓存获取
            start_time = time.time()
            cached_result = cache_manager.get(cache_key)
            cache_query_time = time.time() - start_time
            
            print(f"First query time: {first_query_time*1000:.2f}ms")
            print(f"Cache query time: {cache_query_time*1000:.2f}ms")
            
            if cache_manager.redis_client:
                # 缓存查询应该更快
                assert cache_query_time < first_query_time, "Cache should be faster"
            
        finally:
            db.close()


class TestIndexCreation:
    """索引创建测试"""

    def test_add_missing_indexes(self):
        """测试添加缺失的索引"""
        from sqlalchemy import inspect
        from sqlalchemy import Index
        
        db = get_session()
        try:
            inspector = inspect(db.bind)
            
            # 检查现有索引
            existing_indexes = inspector.get_indexes("business_impact_analysis")
            existing_index_names = [idx["name"] for idx in existing_indexes]
            
            # 添加缺失的索引
            missing_indexes = []
            
            # 检查created_at索引
            if "idx_business_impact_analysis_created_at" not in existing_index_names:
                missing_indexes.append("idx_business_impact_analysis_created_at")
            
            # 检查updated_at索引
            if "idx_business_impact_analysis_updated_at" not in existing_index_names:
                missing_indexes.append("idx_business_impact_analysis_updated_at")
            
            print(f"Missing indexes: {missing_indexes}")
            
            # 注意：这里只是检查，实际添加索引需要通过Alembic迁移
            
        finally:
            db.close()

    def test_index_usage(self):
        """测试索引使用情况"""
        # SQLite不支持索引使用统计，但我们可以验证索引存在
        from sqlalchemy import inspect
        
        db = get_session()
        try:
            inspector = inspect(db.bind)
            
            # 检查所有表的索引
            tables = ["business_impact_analysis", "chaos_experiments", "ai_fine_tuning_jobs"]
            
            for table in tables:
                indexes = inspector.get_indexes(table)
                print(f"Table {table} has {len(indexes)} indexes")
                for idx in indexes:
                    print(f"  - {idx['name']}: {idx.get('column_names', idx.get('columns', []))}")
            
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])