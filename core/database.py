# -*- coding: utf-8 -*-
# core/database.py
# Database base and configuration
# This module provides the SQLAlchemy Base to avoid circular imports

import logging
import os

from sqlalchemy import create_engine, orm
from sqlalchemy.orm import sessionmaker

# SQLAlchemy declarative base
Base = orm.declarative_base()

# Database engine for synchronous operations
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
try:
    os.makedirs(_DATA_DIR, exist_ok=True)
except OSError as exc:
    logging.error(f"Failed to create data directory {_DATA_DIR}: {exc}")
    raise
_DB_PATH = os.environ.get(
    "AIOPS_TEST_DB_PATH", os.path.join(_DATA_DIR, "aiops.db").replace(os.sep, "/")
)

engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session for synchronous operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
