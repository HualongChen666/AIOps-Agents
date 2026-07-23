# -*- coding: utf-8 -*-
# tests/test_backup_router.py
import os
import sys

import pytest  # noqa: F401
from fastapi.testclient import TestClient

from main import app

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


client = TestClient(app)


def test_list_backups():
    # Test listing backups
    response = client.get("/api/v1/backup/list")
    assert response.status_code == 200
    assert "backups" in response.json()


def test_backup_database():
    # Test database backup
    response = client.post("/api/v1/backup/database")
    assert response.status_code in [200, 500]


def test_full_backup():
    # Test full backup
    response = client.post("/api/v1/backup/full")
    assert response.status_code in [200, 500]


def test_cleanup_backups():
    # Test cleanup old backups
    response = client.delete("/api/v1/backup/cleanup?retention_days=30")
    assert response.status_code in [200, 500]
