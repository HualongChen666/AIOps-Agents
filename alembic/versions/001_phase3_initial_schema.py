"""Phase 3 initial persistence schema.

Revision ID: 001
Revises:
Create Date: 2026-07-29 17:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_history",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("alert_id", sa.String(100), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alert_history_alert_id", "alert_history", ["alert_id"])
    op.create_index("ix_alert_history_created_at", "alert_history", ["created_at"])

    op.create_table(
        "repair_records",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("alert_id", sa.String(100), nullable=True),
        sa.Column("alert_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("script_key", sa.String(100), nullable=False),
        sa.Column("script_name", sa.String(200), nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("repair_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repair_duration_sec", sa.Float, nullable=False),
        sa.Column("platform", sa.String(20), nullable=False, server_default="windows"),
        sa.Column("host", sa.String(100), nullable=True),
        sa.Column("output", sa.Text, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("return_code", sa.Integer, nullable=False),
        sa.Column("risk", sa.String(20), nullable=False),
        sa.Column("params", sa.JSON, nullable=True),
        sa.Column("approval_id", sa.String(100), nullable=True),
        sa.Column("executor", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_repair_records_alert_id", "repair_records", ["alert_id"])
    op.create_index("ix_repair_records_success", "repair_records", ["success"])
    op.create_index("ix_repair_records_repair_time", "repair_records", ["repair_time"])
    op.create_index("ix_repair_records_script_key", "repair_records", ["script_key"])

    op.create_table(
        "pending_approvals",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("alert_id", sa.String(100), nullable=False),
        sa.Column("alert_json", sa.Text, nullable=False),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("script_key", sa.String(100), nullable=False),
        sa.Column("proposal", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("approver", sa.String(50), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pending_approvals_alert_id", "pending_approvals", ["alert_id"])
    op.create_index("ix_pending_approvals_status", "pending_approvals", ["status"])
    op.create_index("ix_pending_approvals_submitted_at", "pending_approvals", ["submitted_at"])

    op.create_table(
        "verify_records",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("repair_id", sa.String(100), nullable=True),
        sa.Column("alert_id", sa.String(100), nullable=True),
        sa.Column("strategy", sa.String(50), nullable=True),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("duration_sec", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_verify_records_repair_id", "verify_records", ["repair_id"])
    op.create_index("ix_verify_records_alert_id", "verify_records", ["alert_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("username", sa.String(50), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "hardware_remediation_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.String(100), nullable=True),
        sa.Column("device", sa.String(200), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("dry_run", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column("executed_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hardware_remediation_alert_id", "hardware_remediation_log", ["alert_id"])
    op.create_index("ix_hardware_remediation_action", "hardware_remediation_log", ["action"])
    op.create_index(
        "ix_hardware_remediation_created_at", "hardware_remediation_log", ["created_at"]
    )


def downgrade() -> None:
    op.drop_table("hardware_remediation_log")
    op.drop_table("audit_logs")
    op.drop_table("verify_records")
    op.drop_table("pending_approvals")
    op.drop_table("repair_records")
    op.drop_table("alert_history")
