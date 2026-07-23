---
name: database-migration
description: Database schema management and Alembic migrations
argument-hint: "[migration_description]"
allowed-tools:
  - read_file
  - write_to_file
  - edit
  - multi_edit
  - grep_search
  - find_by_name
  - bash
  - command_status
  - todo_list
  - skill
  - list_resources
  - read_resource
  - search_web
  - read_url_content
triggers:
  - user
  - model
subagent: false
priority: high
auto-apply:
  - "数据库迁移"
  - "Alembic 迁移"
  - "Schema 变更"
  - "数据库修改"
  - "创建迁移"
  - "数据库升级"
file-patterns:
  - "alembic/**/*.py"
  - "alembic.ini"
  - "**/models.py"
  - "**/schema*.py"
keywords:
  - "数据库"
  - "database"
  - "迁移"
  - "migration"
  - "schema"
  - "Alembic"
  - "表"
  - "table"
  - "字段"
  - "column"
---

# Database Migration Skill

## Purpose
Specialized skill for database schema management and migration using Alembic in the AIOps Agent project.

## Auto-approved Tools
- read
- write
- edit
- grep
- find_file_by_name
- exec

## Skill Instructions

### Alembic Configuration

#### Project Structure
```
alembic/
├── versions/          # Migration files
│   ├── 20240101_000000_initial_schema.py
│   └── 20240102_120000_add_user_table.py
├── env.py            # Alembic environment
└── script.py.mako    # Migration template

alembic.ini           # Alembic configuration
```

### Migration Workflow

#### Creating New Migration
```bash
# Generate migration script
alembic revision --autogenerate -m "description of changes"

# Create empty migration script
alembic revision -m "description of changes"

# Specific revision message format
alembic revision -m "add_user_table_with_timestamps"
```

#### Migration File Template
```python
"""add_user_table_with_timestamps

Revision ID: 20240102_120000
Revises: 20240101_000000
Create Date: 2024-01-02 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '20240102_120000'
down_revision = '20240101_000000'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade():
    """Downgrade database schema."""
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
```

### Common Migration Patterns

#### Adding New Table
```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_new_table_id', 'new_table', ['id'])

def downgrade():
    op.drop_index('ix_new_table_id', table_name='new_table')
    op.drop_table('new_table')
```

#### Adding Column to Existing Table
```python
def upgrade():
    op.add_column('existing_table', sa.Column('new_column', sa.String(length=100), nullable=True))

def downgrade():
    op.drop_column('existing_table', 'new_column')
```

#### Adding Column with Default Value
```python
def upgrade():
    op.add_column('users', sa.Column('status', sa.String(length=50), server_default='active', nullable=False))

def downgrade():
    op.drop_column('users', 'status')
```

#### Creating Index
```python
def upgrade():
    op.create_index('ix_table_column', 'table_name', ['column_name'])
    # Composite index
    op.create_index('ix_table_columns', 'table_name', ['column1', 'column2'])
    # Unique index
    op.create_index('ix_table_unique', 'table_name', ['column_name'], unique=True)

def downgrade():
    op.drop_index('ix_table_unique', table_name='table_name')
```

#### Adding Foreign Key
```python
def upgrade():
    op.add_column('posts', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_posts_user_id_users', 
        'posts', 
        'users', 
        ['user_id'], 
        ['id']
    )

def downgrade():
    op.drop_constraint('fk_posts_user_id_users', 'posts', type_='foreignkey')
    op.drop_column('posts', 'user_id')
```

#### Changing Column Type
```python
def upgrade():
    op.alter_column('table_name', 'column_name', 
                   existing_type=sa.String(length=100),
                   type_=sa.String(length=255))

def downgrade():
    op.alter_column('table_name', 'column_name',
                   existing_type=sa.String(length=255),
                   type_=sa.String(length=100))
```

#### Making Column Nullable/Non-Nullable
```python
def upgrade():
    # Make nullable
    op.alter_column('table_name', 'column_name', nullable=True)
    # Make non-nullable (ensure data exists first)
    op.alter_column('table_name', 'column_name', nullable=False)

def downgrade():
    op.alter_column('table_name', 'column_name', nullable=True)
```

#### Adding Constraints
```python
def upgrade():
    # Unique constraint
    op.create_unique_constraint('uq_table_column', 'table_name', ['column_name'])
    # Check constraint
    op.create_check_constraint('ck_table_column_positive', 'table_name', 'column_name >= 0')

def downgrade():
    op.drop_constraint('ck_table_column_positive', 'table_name', type_='check')
    op.drop_constraint('uq_table_column', 'table_name', type_='unique')
```

### PostgreSQL-Specific Operations

#### Using PostgreSQL Types
```python
def upgrade():
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('metadata', postgresql.HSTORE(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('events')
```

#### Using PostgreSQL Functions
```python
def upgrade():
    # Create trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON users 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    op.execute("DROP TRIGGER update_users_updated_at ON users")
    op.execute("DROP FUNCTION update_updated_at_column()")
```

#### Using ENUM Types
```python
def upgrade():
    # Create ENUM type
    status_enum = postgresql.ENUM(
        'active', 'inactive', 'pending', 
        name='userstatus'
    )
    status_enum.create(op.get_bind())
    
    # Add column with ENUM
    op.add_column('users', sa.Column('status', status_enum, nullable=True))

def downgrade():
    op.drop_column('users', 'status')
    postgresql.ENUM(name='userstatus').drop(op.get_bind())
```

### Running Migrations

#### Basic Commands
```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade +1  # Next migration
alembic upgrade 20240102_120000  # Specific revision

# Downgrade
alembic downgrade -1  # Previous migration
alembic downgrade base  # All migrations

# Show current version
alembic current

# Show migration history
alembic history

# Show SQL for migration (dry run)
alembic upgrade head --sql
```

#### Development Workflow
```bash
# 1. Make model changes in SQLAlchemy models
# 2. Generate migration
alembic revision --autogenerate -m "descriptive message"

# 3. Review generated migration
# 4. Test migration
alembic upgrade head --sql

# 5. Apply migration
alembic upgrade head

# 6. Verify changes
# 7. Test downgrade
alembic downgrade -1
alembic upgrade head
```

### Data Migrations

#### Seeding Initial Data
```python
def upgrade():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from models import User
    
    bind = op.get_bind()
    session = sessionmaker(bind=bind)()
    
    try:
        # Create initial users
        admin_user = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        session.add(admin_user)
        session.commit()
    finally:
        session.close()

def downgrade():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import delete
    from models import User
    
    bind = op.get_bind()
    session = sessionmaker(bind=bind)()
    
    try:
        # Remove seeded data
        session.execute(delete(User).where(User.username == 'admin'))
        session.commit()
    finally:
        session.close()
```

#### Data Transformation
```python
def upgrade():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import update
    
    bind = op.get_bind()
    session = sessionmaker(bind=bind)()
    
    try:
        # Transform existing data
        session.execute(
            update(User)
            .where(User.status == None)
            .values(status='active')
        )
        session.commit()
    finally:
        session.close()

def downgrade():
    # Revert transformation if possible
    pass
```

### Best Practices

#### Migration Naming Convention
- Use snake_case
- Be descriptive
- Include table name if applicable
- Format: `action_table_description`
- Examples:
  - `add_user_table`
  - `add_index_to_posts_created_at`
  - `remove_status_column_from_users`

#### Review Checklist
Before applying migrations:
- [ ] Review generated migration file
- [ ] Test on development database
- [ ] Ensure downgrade is implemented
- [ ] Check for data loss potential
- [ ] Verify foreign key constraints
- [ ] Test with production-like data
- [ ] Document breaking changes
- [ ] Plan for minimal downtime

#### Safety Precautions
```bash
# Always backup before major migrations
pg_dump dbname > backup.sql

# Test migrations on staging first
alembic upgrade head

# Use transactions for data migrations
# Consider using --sql flag for review
alembic upgrade head --sql > migration.sql
```

### Troubleshooting

#### Common Issues

**Migration conflicts in team:**
```bash
# Resolve by creating new migration
alembic merge -m "merge migrations" <revision1> <revision2>
```

**Autogenerate not detecting changes:**
- Ensure models are properly imported in env.py
- Check metadata configuration
- Verify model attributes

**Migration fails midway:**
```bash
# Check current state
alembic current

# Stamp to specific revision
alembic stamp <revision>

# Resolve and continue
alembic upgrade head
```

### Testing Migrations

#### Migration Testing
```python
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.mark.asyncio
async def test_migration():
    """Test migration up and down."""
    # Setup test database
    engine = create_engine("sqlite:///:memory:")
    
    # Run migration
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")
    
    command.upgrade(alembic_config, "head")
    
    # Verify schema
    # Test with data
    
    # Test downgrade
    command.downgrade(alembic_config, "base")
```

## When to Invoke
Invoke this skill automatically when:
- Database schema changes are needed
- Creating new tables or columns
- Adding indexes or constraints
- Data migrations or transformations
- Performance optimization via schema changes
- Setting up database for new features

## GitLab 上传权限控制

### 项目配置
- **项目目录**: `C:\AIOps_Agent_bak`
- **GitLab项目**: `Hualong_Chen/neurosync-agent-tool-platform`
- **上传控制**: 严格启用，需要明确用户指令

### 上传权限规则
- ❌ **禁止**: 未经用户明确指令的任何GitLab上传操作
- ✅ **允许**: 仅在用户明确给出上传指令时执行上传
- **上传指令格式**: "将某一个目录(含目录中的子目录和文件)或者某一个/几个文件(具体文件名)上传到我的gitlab中"

### 数据库迁移安全检查
在执行任何可能涉及GitLab操作时：
1. 验证是否为只读操作（搜索、查看等）
2. 如果是写入操作，检查是否有明确的上传指令
3. 确认操作不会违反上传控制规则
4. 记录所有GitLab相关操作

## Project-Specific Context
This project uses:
- Alembic for migrations
- PostgreSQL database
- SQLAlchemy 2.0 async ORM
- Located in `alembic/` directory
- Async database patterns
- PostgreSQL-specific features (JSONB, ARRAY, etc.)