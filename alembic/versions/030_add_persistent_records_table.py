# -*- coding: utf-8 -*-
"""Add persistent_records document store table.

Advanced API routers (release / database / repair / …) used to keep their
entities in module-level dicts, losing everything on restart.  This revision
adds the durable, namespaced JSON document table that now backs them.

Revision ID: 030
Revises: 029
Create Date: 2026-09-10
"""
from alembic import op

revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None

NEW_TABLES = ('persistent_records',)


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
