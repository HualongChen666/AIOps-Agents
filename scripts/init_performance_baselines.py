#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize Performance Baselines
初始化性能基准线数据
"""

import asyncio
import sys
from pathlib import Path

from core.db_engine import AsyncSessionLocal
from core.models import PerformanceBaseline

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def init_api_baselines():
    """初始化API性能基准线"""
    api_baselines = [
        {
            "baseline_id": "baseline-api-health",
            "baseline_name": "Health Check API Baseline",
            "baseline_type": "api",
            "component": "/health",
            "operation": "GET",
            "target_p95_ms": 5.0,
            "target_p99_ms": 10.0,
            "target_throughput": 10000.0,
            "target_error_rate": 0.001,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-api-alerts",
            "baseline_name": "Alerts API Baseline",
            "baseline_type": "api",
            "component": "/api/v1/alerts",
            "operation": "GET",
            "target_p95_ms": 50.0,
            "target_p99_ms": 100.0,
            "target_throughput": 1000.0,
            "target_error_rate": 0.01,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-api-metrics",
            "baseline_name": "Metrics API Baseline",
            "baseline_type": "api",
            "component": "/api/v1/metrics/summary",
            "operation": "GET",
            "target_p95_ms": 100.0,
            "target_p99_ms": 200.0,
            "target_throughput": 500.0,
            "target_error_rate": 0.01,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-api-topology",
            "baseline_name": "Topology API Baseline",
            "baseline_type": "api",
            "component": "/api/v1/topology",
            "operation": "GET",
            "target_p95_ms": 200.0,
            "target_p99_ms": 500.0,
            "target_throughput": 200.0,
            "target_error_rate": 0.02,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-api-ai-inference",
            "baseline_name": "AI Inference API Baseline",
            "baseline_type": "api",
            "component": "/api/v1/ai/inference",
            "operation": "POST",
            "target_p95_ms": 2000.0,
            "target_p99_ms": 5000.0,
            "target_throughput": 50.0,
            "target_error_rate": 0.05,
            "environment": "dev",
        },
    ]

    async with AsyncSessionLocal() as session:
        for baseline_data in api_baselines:
            # 检查是否已存在
            from sqlalchemy import select

            stmt = select(PerformanceBaseline).where(
                PerformanceBaseline.baseline_id == baseline_data["baseline_id"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"基准线已存在，跳过: {baseline_data['baseline_id']}")
                continue

            baseline = PerformanceBaseline(**baseline_data, created_by="system")
            session.add(baseline)
            print(f"创建API基准线: {baseline_data['baseline_id']}")

        await session.commit()
        print(f"✅ API基准线初始化完成，共 {len(api_baselines)} 条")


async def init_database_baselines():
    """初始化数据库性能基准线"""
    db_baselines = [
        {
            "baseline_id": "baseline-db-select-single",
            "baseline_name": "Single SELECT Baseline",
            "baseline_type": "database",
            "component": "alerts",
            "operation": "SELECT_SINGLE",
            "target_p95_ms": 5.0,
            "target_p99_ms": 10.0,
            "target_throughput": 10000.0,
            "target_error_rate": 0.001,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-db-select-batch",
            "baseline_name": "Batch SELECT Baseline",
            "baseline_type": "database",
            "component": "alerts",
            "operation": "SELECT_BATCH_100",
            "target_p95_ms": 20.0,
            "target_p99_ms": 50.0,
            "target_throughput": 1000.0,
            "target_error_rate": 0.01,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-db-insert-single",
            "baseline_name": "Single INSERT Baseline",
            "baseline_type": "database",
            "component": "alerts",
            "operation": "INSERT_SINGLE",
            "target_p95_ms": 10.0,
            "target_p99_ms": 20.0,
            "target_throughput": 5000.0,
            "target_error_rate": 0.001,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-db-insert-batch",
            "baseline_name": "Batch INSERT Baseline",
            "baseline_type": "database",
            "component": "alerts",
            "operation": "INSERT_BATCH_100",
            "target_p95_ms": 100.0,
            "target_p99_ms": 200.0,
            "target_throughput": 100.0,
            "target_error_rate": 0.01,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-db-connection-pool",
            "baseline_name": "Connection Pool Baseline",
            "baseline_type": "database",
            "component": "connection_pool",
            "operation": "ACQUIRE",
            "target_p95_ms": 5.0,
            "target_p99_ms": 10.0,
            "target_throughput": 5000.0,
            "target_error_rate": 0.001,
            "environment": "dev",
        },
    ]

    async with AsyncSessionLocal() as session:
        for baseline_data in db_baselines:
            # 检查是否已存在
            from sqlalchemy import select

            stmt = select(PerformanceBaseline).where(
                PerformanceBaseline.baseline_id == baseline_data["baseline_id"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"基准线已存在，跳过: {baseline_data['baseline_id']}")
                continue

            baseline = PerformanceBaseline(**baseline_data, created_by="system")
            session.add(baseline)
            print(f"创建数据库基准线: {baseline_data['baseline_id']}")

        await session.commit()
        print(f"✅ 数据库基准线初始化完成，共 {len(db_baselines)} 条")


async def init_ai_baselines():
    """初始化AI性能基准线"""
    ai_baselines = [
        {
            "baseline_id": "baseline-ai-llm-short",
            "baseline_name": "LLM Short Prompt Baseline",
            "baseline_type": "ai",
            "component": "gpt-3.5-turbo",
            "operation": "INFERENCE_SHORT",
            "target_p95_ms": 500.0,
            "target_p99_ms": 1000.0,
            "target_throughput": 10.0,
            "target_error_rate": 0.02,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-ai-llm-medium",
            "baseline_name": "LLM Medium Prompt Baseline",
            "baseline_type": "ai",
            "component": "gpt-3.5-turbo",
            "operation": "INFERENCE_MEDIUM",
            "target_p95_ms": 1000.0,
            "target_p99_ms": 2000.0,
            "target_throughput": 5.0,
            "target_error_rate": 0.03,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-ai-rag-e2e",
            "baseline_name": "RAG End-to-End Baseline",
            "baseline_type": "ai",
            "component": "rag_pipeline",
            "operation": "END_TO_END",
            "target_p95_ms": 5000.0,
            "target_p99_ms": 10000.0,
            "target_throughput": 2.0,
            "target_error_rate": 0.05,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-ai-vector-search",
            "baseline_name": "Vector Search Baseline",
            "baseline_type": "ai",
            "component": "qdrant",
            "operation": "VECTOR_SEARCH_1000D",
            "target_p95_ms": 100.0,
            "target_p99_ms": 200.0,
            "target_throughput": 100.0,
            "target_error_rate": 0.01,
            "environment": "dev",
        },
        {
            "baseline_id": "baseline-ai-agent-orchestration",
            "baseline_name": "Agent Orchestration Baseline",
            "baseline_type": "ai",
            "component": "langgraph",
            "operation": "PARALLEL_AGENTS_5",
            "target_p95_ms": 1000.0,
            "target_p99_ms": 2000.0,
            "target_throughput": 1.0,
            "target_error_rate": 0.05,
            "environment": "dev",
        },
    ]

    async with AsyncSessionLocal() as session:
        for baseline_data in ai_baselines:
            # 检查是否已存在
            from sqlalchemy import select

            stmt = select(PerformanceBaseline).where(
                PerformanceBaseline.baseline_id == baseline_data["baseline_id"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"基准线已存在，跳过: {baseline_data['baseline_id']}")
                continue

            baseline = PerformanceBaseline(**baseline_data, created_by="system")
            session.add(baseline)
            print(f"创建AI基准线: {baseline_data['baseline_id']}")

        await session.commit()
        print(f"✅ AI基准线初始化完成，共 {len(ai_baselines)} 条")


async def main():
    """主函数"""
    print("=" * 60)
    print("初始化性能基准线数据")
    print("=" * 60)

    try:
        # 初始化API基准线
        print("\n[1/3] 初始化API性能基准线...")
        await init_api_baselines()

        # 初始化数据库基准线
        print("\n[2/3] 初始化数据库性能基准线...")
        await init_database_baselines()

        # 初始化AI基准线
        print("\n[3/3] 初始化AI性能基准线...")
        await init_ai_baselines()

        print("\n" + "=" * 60)
        print("✅ 性能基准线初始化完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
