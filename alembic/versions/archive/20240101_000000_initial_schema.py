# -*- coding: utf-8 -*-
"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

🔧 P0-3: 初始数据库迁移 - 创建所有表
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建所有表"""

    # 创建用户表
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mfa_secret", sa.String(length=255), nullable=True),
        sa.Column("recovery_codes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)

    # 创建告警表
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("host", sa.String(length=100), nullable=True),
        sa.Column(
            "platform",
            sa.String(length=20),
            nullable=False,
            server_default="windows",
        ),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="P3"),
        sa.Column("bis_score", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("prev_suppressed", sa.Integer(), nullable=True),
        sa.Column("approval_id", sa.String(length=100), nullable=True),
        sa.Column("repair_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_alerts_detected_at", "alerts", ["detected_at"], unique=False)
    op.create_index("idx_alerts_level_status", "alerts", ["level", "status"], unique=False)
    op.create_index("idx_alerts_host_level", "alerts", ["host", "level"], unique=False)
    op.create_index("ix_alerts_category", "alerts", ["category"], unique=False)
    op.create_index("ix_alerts_host", "alerts", ["host"], unique=False)
    op.create_index("ix_alerts_level", "alerts", ["level"], unique=False)
    op.create_index("ix_alerts_status", "alerts", ["status"], unique=False)

    # 创建修复记录表
    op.create_table(
        "repair_records",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("alert_id", sa.String(length=100), nullable=True),
        sa.Column("alert_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("script_key", sa.String(length=100), nullable=False),
        sa.Column("script_name", sa.String(length=200), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("repair_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repair_duration_sec", sa.Float(), nullable=False),
        sa.Column(
            "platform",
            sa.String(length=20),
            nullable=False,
            server_default="windows",
        ),
        sa.Column("host", sa.String(length=100), nullable=True),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("return_code", sa.Integer(), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("params", postgresql.JSON(), nullable=True),
        sa.Column("approval_id", sa.String(length=100), nullable=True),
        sa.Column("executor", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_repair_records_alert_id", "repair_records", ["alert_id"], unique=False)
    op.create_index(
        "idx_repair_records_repair_time", "repair_records", ["repair_time"], unique=False
    )
    op.create_index("idx_repair_records_script_key", "repair_records", ["script_key"], unique=False)
    op.create_index("idx_repair_records_success", "repair_records", ["success"], unique=False)

    # 创建待审批记录表
    op.create_table(
        "pending_approvals",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("alert_id", sa.String(length=100), nullable=False),
        sa.Column("alert_json", sa.Text(), nullable=False),
        sa.Column("rule_name", sa.String(length=100), nullable=False),
        sa.Column("script_key", sa.String(length=100), nullable=False),
        sa.Column("proposal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("approver", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("host", sa.String(length=100), nullable=True),
        sa.Column(
            "platform",
            sa.String(length=20),
            nullable=False,
            server_default="windows",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_pending_approvals_alert_id", "pending_approvals", ["alert_id"], unique=False
    )
    op.create_index(
        "idx_pending_approvals_submitted_at",
        "pending_approvals",
        ["submitted_at"],
        unique=False,
    )
    op.create_index("idx_pending_approvals_status", "pending_approvals", ["status"], unique=False)

    # 创建审计日志表
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=50), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index(
        "idx_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index("idx_audit_logs_user", "audit_logs", ["username"], unique=False)
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"], unique=False)
    op.create_index("ix_audit_logs_username", "audit_logs", ["username"], unique=False)

    # 创建系统指标历史表
    op.create_table(
        "system_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("host", sa.String(length=100), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("cpu_core_count", sa.Integer(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("memory_used_gb", sa.Float(), nullable=True),
        sa.Column("memory_total_gb", sa.Float(), nullable=True),
        sa.Column("disk_metrics", postgresql.JSON(), nullable=True),
        sa.Column("network_recv_speed_mb", sa.Float(), nullable=True),
        sa.Column("network_sent_speed_mb", sa.Float(), nullable=True),
        sa.Column("top_processes", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_system_metrics_host_timestamp",
        "system_metrics",
        ["host", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    """删除所有表"""
    op.drop_index("idx_system_metrics_host_timestamp", table_name="system_metrics")
    op.drop_table("system_metrics")

    op.drop_index("ix_audit_logs_username", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("idx_audit_logs_user", table_name="audit_logs")
    op.drop_index("idx_audit_logs_resource", table_name="audit_logs")
    op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_pending_approvals_status", table_name="pending_approvals")
    op.drop_index("idx_pending_approvals_submitted_at", table_name="pending_approvals")
    op.drop_index("idx_pending_approvals_alert_id", table_name="pending_approvals")
    op.drop_table("pending_approvals")

    op.drop_index("idx_repair_records_success", table_name="repair_records")
    op.drop_index("idx_repair_records_script_key", table_name="repair_records")
    op.drop_index("idx_repair_records_repair_time", table_name="repair_records")
    op.drop_index("idx_repair_records_alert_id", table_name="repair_records")
    op.drop_table("repair_records")

    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_level", table_name="alerts")
    op.drop_index("ix_alerts_host", table_name="alerts")
    op.drop_index("ix_alerts_category", table_name="alerts")
    op.drop_index("idx_alerts_host_level", table_name="alerts")
    op.drop_index("idx_alerts_level_status", table_name="alerts")
    op.drop_index("idx_alerts_detected_at", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
