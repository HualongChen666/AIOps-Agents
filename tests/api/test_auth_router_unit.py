# -*- coding: utf-8 -*-
"""Unit tests for auth_router functions that require isolated database state."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth_router import _user_dict, _UserOut, register_admin
from core.auth_db import Base, User
from core.auth_service import hash_password


@pytest.fixture
def unit_test_db():
    """Create an isolated in-memory SQLite database for unit tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    engine.dispose()


def test_register_admin_success_empty_db(unit_test_db):
    """Bootstrap admin registration succeeds when no users exist (lines 74-89)."""
    # Verify database is empty
    assert unit_test_db.query(User).count() == 0

    # Create a mock request
    class MockRequest:
        username = "bootstrap_admin"
        password = "bootstrap123"

    # Call the register_admin function directly
    result = register_admin(MockRequest(), unit_test_db)

    # Verify the result
    assert isinstance(result, _UserOut)
    assert result.username == "bootstrap_admin"
    assert result.role == "admin"
    assert result.is_active is True
    assert result.id is not None

    # Verify user was created in database
    user = unit_test_db.query(User).filter(User.username == "bootstrap_admin").first()
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True


def test_register_admin_fails_when_users_exist(unit_test_db):
    """Bootstrap admin registration fails when users already exist (lines 74-78)."""
    # Create a user first
    existing_user = User(username="existing", role="operator", is_active=True)
    existing_user.password_hash = hash_password("password123")
    unit_test_db.add(existing_user)
    unit_test_db.commit()

    # Create a mock request
    class MockRequest:
        username = "bootstrap_admin"
        password = "bootstrap123"

    # Call the register_admin function and expect an exception
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        register_admin(MockRequest(), unit_test_db)

    assert exc_info.value.status_code == 400
    assert "Bootstrap registration only allowed when no users exist" in str(exc_info.value.detail)


def test_user_dict_conversion():
    """Test the _user_dict helper function."""
    user = User(
        id=1,
        username="testuser",
        role="operator",
        is_active=True,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    user.password_hash = hash_password("password")

    result = _user_dict(user)
    assert isinstance(result, _UserOut)
    assert result.id == 1
    assert result.username == "testuser"
    assert result.role == "operator"
    assert result.is_active is True
    assert result.created_at == datetime(2024, 1, 1, 12, 0, 0)
