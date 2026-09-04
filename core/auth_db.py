# -*- coding: utf-8 -*-
"""SQLAlchemy database layer for RBAC and asset permission management."""

import logging
import os
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)

try:
    from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
except ImportError:  # pragma: no cover
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import Session, relationship, sessionmaker

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
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    disabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    recovery_codes = Column(String, nullable=True)

    permissions = relationship(
        "UserAssetPermission", back_populates="user", cascade="all, delete-orphan"
    )


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, default="default", index=True)
    name = Column(String, nullable=False)
    service = Column(String, nullable=True)
    business_unit = Column(String, nullable=True)
    env = Column(String, nullable=True)
    owner = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    permissions = relationship(
        "UserAssetPermission", back_populates="asset", cascade="all, delete-orphan"
    )


class UserAssetPermission(Base):
    __tablename__ = "user_asset_permissions"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, default="default", index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    permission = Column(String, nullable=False)
    resource_type = Column(String, nullable=False, default="asset")
    conditions = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="permissions")
    asset = relationship("Asset", back_populates="permissions")


def get_session() -> Session:
    return SessionLocal()


def init_db() -> None:
    """Create tables and seed default admin if no users exist."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).first():
            from core.auth_service import hash_password

            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role="admin",
                disabled=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
