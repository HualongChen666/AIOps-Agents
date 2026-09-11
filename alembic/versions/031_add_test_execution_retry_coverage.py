# -*- coding: utf-8 -*-
"""Add retry_count / coverage columns to test_executions.

``api/test_automation_advanced_router`` increments ``retry_count`` when an
execution is retried and echoes ``coverage`` in generated reports, but the
``TestExecutionDB`` model never declared either column — the retry and report
endpoints therefore raised ``AttributeError`` at runtime.

Revision ID: 031
Revises: 030
Create Date: 2026-09-11
"""
import sqlalchemy as sa
from alembic import op

revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "test_executions",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "test_executions",
        sa.Column("coverage", sa.Float(), nullable=True),
    )


def downgrade():
    op.drop_column("test_executions", "coverage")
    op.drop_column("test_executions", "retry_count")
