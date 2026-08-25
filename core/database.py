# -*- coding: utf-8 -*-
# core/database.py
# Database base and configuration
# This module provides the SQLAlchemy Base to avoid circular imports

import os
from sqlalchemy import orm, create_engine
from sqlalchemy.orm import sessionmaker

# SQLAlchemy declarative base
Base = orm.declarative_base()

# Database engine for synchronous operations
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)
_DB_PATH = os.environ.get(
    "AIOPS_TEST_DB_PATH", os.path.join(_DATA_DIR, "aiops.db").replace(os.sep, "/")
)

engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session for synchronous operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
