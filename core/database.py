# -*- coding: utf-8 -*-
# core/database.py
# Database base and configuration
# This module provides the SQLAlchemy Base to avoid circular imports

from sqlalchemy import orm

# SQLAlchemy declarative base
Base = orm.declarative_base()
