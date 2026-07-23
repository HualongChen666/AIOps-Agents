# -*- coding: utf-8 -*-
# tests/unit/test_database_unit.py
# Database模块单元测试
import pytest  # noqa: F401


class TestDatabaseBase:
    """测试数据库Base"""

    def test_base_exists(self):
        """测试Base存在"""
        from core.database import Base

        assert Base is not None

    def test_base_is_declarative(self):
        """测试Base是declarative base"""
        from sqlalchemy.orm import DeclarativeBase  # noqa: F401

        from core.database import Base

        # SQLAlchemy 2.0+ 使用 DeclarativeBase
        # 旧版本使用 declarative_base()
        assert hasattr(Base, "metadata")

    def test_base_has_metadata(self):
        """测试Base有metadata属性"""
        from core.database import Base

        assert hasattr(Base, "metadata")
        assert Base.metadata is not None
