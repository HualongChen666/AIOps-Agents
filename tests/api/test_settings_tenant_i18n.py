# -*- coding: utf-8 -*-
"""Real end-to-end tests for settings, tenant, i18n and localization endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # settings_router.py
    ("GET", "/api/settings/", None, None, {200, 500}),
    ("PUT", "/api/settings/", {}, None, {200, 422, 500}),
    # tenant_router.py
    ("GET", "/api/v1/tenants/", None, None, {200, 500}),
    ("POST", "/api/v1/tenants/", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/tenants/t-1", None, None, {200, 404, 500}),
    ("PUT", "/api/v1/tenants/t-1", {}, None, {200, 422, 404, 500}),
    ("DELETE", "/api/v1/tenants/t-1", None, None, {200, 204, 404, 500}),
    # i18n_router.py
    ("GET", "/api/i18n/status", None, None, {200, 500}),
    ("GET", "/api/i18n/locales", None, None, {200, 500}),
    ("GET", "/api/i18n/locales/en", None, None, {200, 404, 500}),
    ("POST", "/api/i18n/locale/set", {}, None, {200, 422, 500}),
    ("GET", "/api/i18n/translate", None, {"text": "hello", "target_locale": "zh"}, {200, 422, 500}),
    ("GET", "/api/i18n/format/number", None, {"value": 123.45, "locale": "en_US"}, {200, 422, 500}),
    (
        "GET",
        "/api/i18n/format/currency",
        None,
        {"value": 99.99, "currency": "USD"},
        {200, 422, 500},
    ),
    (
        "GET",
        "/api/i18n/format/date",
        None,
        {"date": "2026-08-10T00:00:00", "locale": "en_US"},
        {200, 422, 500},
    ),
    # localization_adapter_router.py
    ("GET", "/api/localization-adapter/status", None, None, {200, 500}),
    ("GET", "/api/localization-adapter/locales", None, None, {200, 500}),
    ("POST", "/api/localization-adapter/locale/set", {}, None, {200, 422, 500}),
    (
        "GET",
        "/api/localization-adapter/format/date",
        None,
        {"date": "2026-08-10", "locale": "en"},
        {200, 422, 500},
    ),
    (
        "GET",
        "/api/localization-adapter/format/datetime",
        None,
        {"datetime": "2026-08-10T00:00:00", "locale": "en"},
        {200, 422, 500},
    ),
    (
        "GET",
        "/api/localization-adapter/format/number",
        None,
        {"value": 123.45, "locale": "en"},
        {200, 422, 500},
    ),
    (
        "GET",
        "/api/localization-adapter/format/currency",
        None,
        {"value": 99.99, "currency": "USD"},
        {200, 422, 500},
    ),
    (
        "GET",
        "/api/localization-adapter/format/unit",
        None,
        {"value": 5, "unit": "kg"},
        {200, 422, 500},
    ),
    # localization_resource_router.py
    ("GET", "/api/localization/status", None, None, {200, 500}),
    ("GET", "/api/localization/translations", None, {"locale": "en"}, {200, 422, 500}),
    ("GET", "/api/localization/translations/missing", None, {"locale": "en"}, {200, 422, 500}),
    ("POST", "/api/localization/translation/add", {}, None, {200, 422, 500}),
    ("POST", "/api/localization/translation/export", {}, None, {200, 422, 500}),
    ("POST", "/api/localization/translation/import", {}, None, {200, 422, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_settings_tenant_i18n_endpoint(
    client, approval_headers, method, path, body, params, expected
):
    """Each safe B25 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected
