"""Drop the orphan tables created by 001 that have no ORM model.

Revision ID: 028
Revises: 027
Create Date: 2026-09-10 14:05:00.000000

Migration ``001`` created three tables that no ORM model ever managed and that
no code ever reads or writes::

    alert_history               (no ``__tablename__``, no reader/writer)
    verify_records              (``core/rag_engine.py`` uses this *name* for a
                                 Qdrant collection, not for this SQL table;
                                 ``core/db_engine.insert_verify_record`` is a
                                 log-only compatibility shim)
    hardware_remediation_log    (no ``__tablename__``, no reader/writer)

Because the application creates its schema from ``Base.metadata``
(``core/db_engine.async_init_db`` -> ``create_all``) these tables never exist in
a running deployment, while ``alembic autogenerate`` keeps proposing to drop
them.  This migration removes them so that ``alembic upgrade head`` and the ORM
metadata agree.  ``downgrade`` restores the exact DDL from migration ``001``.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_alert_history_created_at", table_name="alert_history")
    op.drop_index("ix_alert_history_alert_id", table_name="alert_history")
    op.drop_table("alert_history")

    op.drop_index("ix_verify_records_alert_id", table_name="verify_records")
    op.drop_index("ix_verify_records_repair_id", table_name="verify_records")
    op.drop_table("verify_records")

    op.drop_index("ix_hardware_remediation_created_at", table_name="hardware_remediation_log")
    op.drop_index("ix_hardware_remediation_action", table_name="hardware_remediation_log")
    op.drop_index("ix_hardware_remediation_alert_id", table_name="hardware_remediation_log")
    op.drop_table("hardware_remediation_log")


def downgrade() -> None:
    # Restores the DDL exactly as written by migration 001.
    op.create_table(
        "alert_history",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("alert_id", sa.String(100), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_alert_history_alert_id", "alert_history", ["alert_id"])
    op.create_index("ix_alert_history_created_at", "alert_history", ["created_at"])

    op.create_table(
        "verify_records",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("repair_id", sa.String(100), nullable=True),
        sa.Column("alert_id", sa.String(100), nullable=True),
        sa.Column("strategy", sa.String(50), nullable=True),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("duration_sec", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_verify_records_repair_id", "verify_records", ["repair_id"])
    op.create_index("ix_verify_records_alert_id", "verify_records", ["alert_id"])

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
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_hardware_remediation_alert_id", "hardware_remediation_log", ["alert_id"])
    op.create_index("ix_hardware_remediation_action", "hardware_remediation_log", ["action"])
    op.create_index(
        "ix_hardware_remediation_created_at", "hardware_remediation_log", ["created_at"]
    )
