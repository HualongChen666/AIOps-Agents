# -*- coding: utf-8 -*-
# alembic/env.py
# 🔧 P0-3: Alembic环境配置
# 配置Alembic使用core.models中的ORM模型

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context
from config import POSTGRES_URL
from core.models import Base

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入配置

# 导入ORM模型Base

# Alembic Config对象
config = context.config

# 设置数据库URL，允许通过环境变量覆盖（用于本地 SQLite 测试或 CI）
config.set_main_option(
    "sqlalchemy.url", os.getenv("ALEMBIC_DATABASE_URL", POSTGRES_URL)
)

# 解释配置文件的日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据
target_metadata = Base.metadata

# 其他值可以从config中获取
# my_important_option = config.get_main_option("my_important_option")


def run_migrations_offline() -> None:
    """在'离线'模式下运行迁移。

    这会配置上下文，只需一个URL而不是Engine，尽管仍然需要Engine对象来声明元数据。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在'在线'模式下运行迁移。

    在这种情况下，我们需要创建一个Engine并将其与连接关联起来。
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
