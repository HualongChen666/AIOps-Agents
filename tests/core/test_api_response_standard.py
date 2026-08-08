# -*- coding: utf-8 -*-
from core.api_response_standard import (
    APIResponse,
    create_error_response,
    create_paginated_response,
    create_success_response,
)


def test_create_success_response():
    payload = {"alert_id": "123"}
    resp = create_success_response(payload)
    assert resp["success"] is True
    assert resp["data"] == payload
    assert "timestamp" in resp
    assert "request_id" in resp


def test_create_error_response():
    resp = create_error_response("resource missing", "ERR_NOT_FOUND", "NotFound")
    assert resp["success"] is False
    assert resp["error_code"] == "ERR_NOT_FOUND"
    assert resp["error"] == "resource missing"


def test_create_paginated_response():
    resp = create_paginated_response(items=[{"id": 1}], total=1, page=1, size=10)
    assert resp["success"] is True
    assert resp["data"]["total"] == 1
    assert resp["data"]["items"][0]["id"] == 1


def test_api_response_object():
    resp = APIResponse(data={"x": 1}, success=True, message="ok")
    d = resp.to_dict()
    assert d["data"]["x"] == 1
    assert d["message"] == "ok"
    assert d["success"] is True
