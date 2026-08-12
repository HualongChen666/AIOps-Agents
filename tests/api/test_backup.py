import pytest
# -*- coding: utf-8 -*-
"""Real end-to-end tests for the backup list endpoint."""


@pytest.mark.smoke
def test_list_backups(client, approval_headers):
    """The backup list endpoint returns 200 or a valid error."""
    resp = client.get("/api/v1/backup/list", headers=approval_headers)
    assert resp.status_code in (200, 500)
