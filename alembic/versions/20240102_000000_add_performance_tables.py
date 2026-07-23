# -*- coding: utf-8 -*-
"""Add performance tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

🔧 P0-3: 添加性能基准测试相关表
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加性能表"""

    # 创建性能指标表
    op.create_table(
        "performance_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("test_id", sa.String(length=100), nullable=False),
        sa.Column("test_name", sa.String(length=200), nullable=False),
        sa.Column("test_type", sa.String(length=50), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("mean_time_ms", sa.Float(), nullable=False),
        sa.Column("min_time_ms", sa.Float(), nullable=False),
        sa.Column("max_time_ms", sa.Float(), nullable=False),
        sa.Column("p50_time_ms", sa.Float(), nullable=True),
        sa.Column("p95_time_ms", sa.Float(), nullable=True),
        sa.Column("p99_time_ms", sa.Float(), nullable=True),
        sa.Column("std_dev_ms", sa.Float(), nullable=True),
        sa.Column("throughput_ops", sa.Float(), nullable=True),
        sa.Column("qps", sa.Float(), nullable=True),
        sa.Column("error_rate", sa.Float(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=True),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("cpu_usage", sa.Float(), nullable=True),
        sa.Column("memory_usage", sa.Float(), nullable=True),
        sa.Column("disk_io", sa.Float(), nullable=True),
        sa.Column("network_io", sa.Float(), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("data_volume", sa.String(length=50), nullable=True),
        sa.Column("pool_size", sa.Integer(), nullable=True),
        sa.Column("connection_count", sa.Integer(), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("git_commit", sa.String(length=50), nullable=True),
        sa.Column("git_branch", sa.String(length=50), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_performance_metrics_test_id", "test_id"),
        sa.Index("idx_performance_metrics_test_type", "test_type"),
        sa.Index("idx_performance_metrics_component", "component"),
        sa.Index("idx_performance_metrics_timestamp", "timestamp"),
        sa.Index("idx_performance_metrics_environment", "environment"),
    )

    # 创建性能基准表
    op.create_table(
        "performance_baselines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("baseline_id", sa.String(length=100), nullable=False),
        sa.Column("baseline_name", sa.String(length=200), nullable=False),
        sa.Column("baseline_type", sa.String(length=50), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("target_p95_ms", sa.Float(), nullable=False),
        sa.Column("target_p99_ms", sa.Float(), nullable=True),
        sa.Column("target_throughput", sa.Float(), nullable=True),
        sa.Column("target_error_rate", sa.Float(), nullable=True),
        sa.Column("regression_threshold", sa.Float(), nullable=False, server_default="0.1"),
        sa.Column("critical_threshold", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("baseline_id"),
        sa.Index("idx_performance_baselines_baseline_id", "baseline_id"),
        sa.Index("idx_performance_baselines_component", "component"),
        sa.Index("idx_performance_baselines_environment", "environment"),
        sa.Index("idx_performance_baselines_is_active", "is_active"),
    )

    # 创建性能趋势表
    op.create_table(
        "performance_trends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trend_id", sa.String(length=100), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("trend_direction", sa.String(length=20), nullable=True),
        sa.Column("trend_magnitude", sa.Float(), nullable=True),
        sa.Column("trend_significance", sa.String(length=20), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("deviation_from_baseline", sa.Float(), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_performance_trends_trend_id", "trend_id"),
        sa.Index("idx_performance_trends_component", "component"),
        sa.Index("idx_performance_trends_timestamp", "timestamp"),
        sa.Index("idx_performance_trends_environment", "environment"),
    )

    # 创建性能回归记录表
    op.create_table(
        "performance_regressions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("regression_id", sa.String(length=100), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("deviation", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("git_commit", sa.String(length=50), nullable=True),
        sa.Column("git_branch", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("acknowledged_by", sa.String(length=50), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regression_id"),
        sa.Index("idx_performance_regressions_regression_id", "regression_id"),
        sa.Index("idx_performance_regressions_component", "component"),
        sa.Index("idx_performance_regressions_severity", "severity"),
        sa.Index("idx_performance_regressions_status", "status"),
        sa.Index("idx_performance_regressions_detected_at", "detected_at"),
    )


def downgrade() -> None:
    """删除性能表"""

    op.drop_index("idx_performance_regressions_detected_at", table_name="performance_regressions")
    op.drop_index("idx_performance_regressions_status", table_name="performance_regressions")
    op.drop_index("idx_performance_regressions_severity", table_name="performance_regressions")
    op.drop_index("idx_performance_regressions_component", table_name="performance_regressions")
    op.drop_index("idx_performance_regressions_regression_id", table_name="performance_regressions")
    op.drop_table("performance_regressions")

    op.drop_index("idx_performance_trends_environment", table_name="performance_trends")
    op.drop_index("idx_performance_trends_timestamp", table_name="performance_trends")
    op.drop_index("idx_performance_trends_component", table_name="performance_trends")
    op.drop_index("idx_performance_trends_trend_id", table_name="performance_trends")
    op.drop_table("performance_trends")

    op.drop_index("idx_performance_baselines_is_active", table_name="performance_baselines")
    op.drop_index("idx_performance_baselines_environment", table_name="performance_baselines")
    op.drop_index("idx_performance_baselines_component", table_name="performance_baselines")
    op.drop_index("idx_performance_baselines_baseline_id", table_name="performance_baselines")
    op.drop_table("performance_baselines")

    op.drop_index("idx_performance_metrics_environment", table_name="performance_metrics")
    op.drop_index("idx_performance_metrics_timestamp", table_name="performance_metrics")
    op.drop_index("idx_performance_metrics_component", table_name="performance_metrics")
    op.drop_index("idx_performance_metrics_test_type", table_name="performance_metrics")
    op.drop_index("idx_performance_metrics_test_id", table_name="performance_metrics")
    op.drop_table("performance_metrics")
