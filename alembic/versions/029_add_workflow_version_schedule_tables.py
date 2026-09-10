# -*- coding: utf-8 -*-
"""Add workflow version and schedule tables.

``DatabaseWorkflowRepository`` previously no-op'd its version/schedule
methods (marked "not implemented in DB yet").  This revision adds the
backing tables so those operations persist for real:

* ``workflow_versions``  — immutable version snapshots per workflow
* ``workflow_schedules`` — cron-scheduled workflow tasks

Revision ID: 029
Revises: 028
Create Date: 2026-09-10
"""
from alembic import op

revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None

#: New tables introduced by this revision.
NEW_TABLES = (
    'workflow_versions',
    'workflow_schedules',
)


def _tables():
    from core.models import Base

    return [Base.metadata.tables[name] for name in NEW_TABLES
            if name in Base.metadata.tables]


def upgrade():
    from core.models import Base

    Base.metadata.create_all(bind=op.get_bind(), tables=_tables(), checkfirst=True)


def downgrade():
    from core.models import Base

    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables(), checkfirst=True)
