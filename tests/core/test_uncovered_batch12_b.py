# -*- coding: utf-8 -*-
"""Functional tests for core.causal.impact, core.token_blacklist,
core.security_input_validator, core.ai.rag.reranker and core.enhanced_caching.
"""

import asyncio
import fnmatch
import json
import sys
import types
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from starlette.middleware import Middleware
from starlette.responses import JSONResponse

from core.ai.rag.reranker import (
    CrossEncoderReranker,
    MMRReranker,
    Reranker,
    RerankingPipeline,
)
from core.ai.rag.retriever import RetrievalResult
from core.ai.rag.vectorizer import DocumentChunk
from core.causal.graph import CausalEdge, CausalGraph, CausalStrength
from core.causal.impact import ImpactAnalyzer
from core.enhanced_caching import (
    CacheInvalidationStrategy,
    CacheWarmer,
    RedisCacheBackend,
    setup_enhanced_caching,
    smart_cache,
)
from core.security_input_validator import (
    SecurityInputValidator,
    SecurityInputValidatorMiddleware,
    add_input_validation_middleware,
    create_security_middleware,
    get_security_validator,
    reset_security_validator,
)
from core.token_blacklist import (
    blacklist_jti,
    blacklist_token,
    cleanup_expired,
    is_blacklisted,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.causal.impact
# ---------------------------------------------------------------------------
def _build_causal_graph():
    g = CausalGraph("infra")
    g.add_edge(CausalEdge("db", "cpu", CausalStrength.STRONG, 0.9))
    g.add_edge(CausalEdge("cpu", "api", CausalStrength.MODERATE, 0.8))
    g.add_edge(CausalEdge("db", "api", CausalStrength.WEAK, 0.7))
    g.add_node("net")
    return g


def test_analyze_change_impact():
    g = _build_causal_graph()
    analyzer = ImpactAnalyzer(g)
    assessment = analyzer.analyze_change_impact({"db"}, change_magnitude=1.0)

    assert "cpu" in assessment.affected_nodes
    assert "api" in assessment.affected_nodes
    assert assessment.impact_scores["cpu"] == pytest.approx(0.75)
    assert assessment.impact_scores["api"] == pytest.approx(0.25)
    assert assessment.total_impact == pytest.approx(0.5)
    assert assessment.critical_path == ["db", "cpu"]


def test_analyze_change_impact_isolated_node():
    g = _build_causal_graph()
    analyzer = ImpactAnalyzer(g)
    assessment = analyzer.analyze_change_impact({"net"})
    assert assessment.affected_nodes == set()
    assert assessment.impact_scores == {}
    assert assessment.total_impact == 0.0
    assert assessment.critical_path == []


def test_predict_cascade_failure_cascade():
    g = _build_causal_graph()
    analyzer = ImpactAnalyzer(g)
    failed = analyzer.predict_cascade_failure({"db"}, failure_threshold=0.5)
    assert set(failed) == {"db", "cpu", "api"}


def test_predict_cascade_failure_no_propagation():
    g = _build_causal_graph()
    analyzer = ImpactAnalyzer(g)
    failed = analyzer.predict_cascade_failure({"db"}, failure_threshold=0.95)
    assert set(failed) == {"db"}


def test_identify_critical_nodes():
    g = _build_causal_graph()
    analyzer = ImpactAnalyzer(g)
    ranked = analyzer.identify_critical_nodes()
    by_node = {node: score for node, score in ranked}
    assert by_node["db"] > by_node["cpu"] > 0
    assert by_node["api"] == 0.0
    assert by_node["net"] == 0.0


# ---------------------------------------------------------------------------
# core.token_blacklist
# ---------------------------------------------------------------------------
class FakeTokenSession:
    first_return = None
    delete_count = 0
    added = []
    committed = []

    @classmethod
    def reset(cls):
        cls.first_return = None
        cls.delete_count = 0
        cls.added = []
        cls.committed = []

    def __init__(self):
        pass

    def query(self, model):
        return self

    def filter(self, *conditions):
        return self

    def first(self):
        return self.__class__.first_return

    def delete(self, synchronize_session=False):
        return self.__class__.delete_count

    def add(self, obj):
        self.__class__.added.append(obj)

    def commit(self):
        self.__class__.committed.append(True)

    def close(self):
        pass


def _fake_session_local():
    return FakeTokenSession()


@pytest.fixture
def patch_token_session(monkeypatch):
    FakeTokenSession.reset()
    monkeypatch.setattr("core.token_blacklist.SessionLocal", _fake_session_local)
    yield
    FakeTokenSession.reset()


def test_is_blacklisted_empty():
    assert is_blacklisted("") is False


def test_is_blacklisted_true(patch_token_session):
    FakeTokenSession.first_return = types.SimpleNamespace()
    assert is_blacklisted("jti-123") is True


def test_is_blacklisted_false(patch_token_session):
    FakeTokenSession.first_return = None
    assert is_blacklisted("jti-123") is False


def test_blacklist_jti_adds(patch_token_session):
    FakeTokenSession.first_return = None
    blacklist_jti("jti-456", expires_at=datetime.utcnow())
    assert len(FakeTokenSession.added) == 1
    assert FakeTokenSession.committed
    assert FakeTokenSession.added[0].jti == "jti-456"


def test_blacklist_jti_existing_skips(patch_token_session):
    FakeTokenSession.first_return = types.SimpleNamespace()
    blacklist_jti("jti-456")
    assert FakeTokenSession.added == []


def test_blacklist_jti_empty():
    FakeTokenSession.reset()
    blacklist_jti("")
    assert FakeTokenSession.added == []


def test_cleanup_expired(patch_token_session):
    FakeTokenSession.delete_count = 3
    removed = cleanup_expired()
    assert removed == 3
    assert FakeTokenSession.committed


def test_blacklist_token_valid(patch_token_session):
    FakeTokenSession.first_return = None
    exp = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    token = jwt.encode({"jti": "revoke-me", "exp": exp}, "secret", algorithm="HS256")
    blacklist_token(token, "secret", "HS256")
    assert len(FakeTokenSession.added) == 1
    assert FakeTokenSession.added[0].jti == "revoke-me"
    assert FakeTokenSession.added[0].expires_at is not None


def test_blacklist_token_invalid():
    FakeTokenSession.reset()
    blacklist_token("not-a-jwt", "secret", "HS256")
    assert FakeTokenSession.added == []


# ---------------------------------------------------------------------------
# core.security_input_validator
# ---------------------------------------------------------------------------
@pytest.fixture
def validator():
    return SecurityInputValidator()


@pytest.mark.parametrize(
    "value,input_type,expected_valid,expected_error",
    [
        ("safe text", "general", True, None),
        (123, "general", False, "Input must be a string"),
        ("<script>alert(1)</script>", "general", False, "XSS"),
        ("1 OR 1=1", "general", False, "SQL"),
        ("../../etc/passwd", "path", False, "path traversal"),
        ("safe.txt", "filename", True, None),
        ("; cat /etc/passwd", "command", False, "command injection"),
        ("hello", "command", True, None),
    ],
)
def test_validate_string(validator, value, input_type, expected_valid, expected_error):
    is_valid, error = validator.validate_string(value, input_type)
    assert is_valid is expected_valid
    if expected_error:
        assert expected_error in (error or "")


def test_sanitize_string(validator):
    dirty = (
        "<script>alert(1)</script>"
        "<style>body{}</style>"
        "<a href='javascript:alert(1)'>click</a>"
        "<img src='data:text/html,xxx'>"
        " expression(alert(1))"
    )
    clean = validator.sanitize_string(dirty)
    assert "<script>" not in clean
    assert "javascript:" not in clean
    assert "<style>" not in clean
    assert "&lt;" in clean or clean == ""


def test_sanitize_string_non_str(validator):
    assert validator.sanitize_string(123) == "123"


def test_validate_dict_and_list(validator):
    is_valid, error = validator.validate_dict({"name": "safe", "items": ["a", "b"]})
    assert is_valid is True

    is_valid, error = validator.validate_dict({
        "name": "safe",
        "nested": {"bad": "<script>alert(1)</script>"},
    })
    assert is_valid is False
    assert "XSS" in error

    is_valid, error = validator.validate_list(["ok", "1 OR 1=1"])
    assert is_valid is False
    assert "SQL" in error


def test_validate_any(validator):
    assert validator.validate_any("safe")[0] is True
    assert validator.validate_any({"k": "v"})[0] is True
    assert validator.validate_any(["1 OR 1=1"])[0] is False
    assert validator.validate_any(42)[0] is True


def test_security_validator_singleton():
    reset_security_validator()
    v1 = get_security_validator()
    v2 = get_security_validator()
    assert v1 is v2
    reset_security_validator()


def test_create_security_middleware():
    mw = create_security_middleware()
    assert isinstance(mw, Middleware)
    assert mw.cls is SecurityInputValidatorMiddleware


def test_add_input_validation_middleware():
    app = MagicMock()
    add_input_validation_middleware(app)
    assert app.add_middleware.called
    call = app.add_middleware.call_args
    assert call.args[0] is SecurityInputValidatorMiddleware


@pytest.fixture
def middleware_app():
    app = MagicMock()
    return SecurityInputValidatorMiddleware(app)


def _make_request(method, path, query_params=None, path_params=None, body=None, json_exc=None):
    request = MagicMock()
    request.method = method
    request.url = types.SimpleNamespace(path=path)
    request.query_params = query_params or {}
    request.path_params = path_params or {}
    if json_exc:
        request.json = AsyncMock(side_effect=json_exc)
    else:
        request.json = AsyncMock(return_value=body)
    return request


def test_middleware_skips_options(middleware_app):
    request = _make_request("OPTIONS", "/submit")
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 200
    call_next.assert_awaited_once()


def test_middleware_skips_health_path(middleware_app):
    request = _make_request("GET", "/health")
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 200
    call_next.assert_awaited_once()


def test_middleware_invalid_query(middleware_app):
    request = _make_request("GET", "/search", query_params={"q": "<script>alert(1)</script>"})
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 400
    call_next.assert_not_awaited()


def test_middleware_invalid_body(middleware_app):
    request = _make_request("POST", "/submit", body={"payload": "1 OR 1=1"})
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 400


def test_middleware_body_not_json(middleware_app):
    request = _make_request("POST", "/submit", body=None, json_exc=ValueError("not json"))
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 200
    call_next.assert_awaited_once()


def test_middleware_invalid_path(middleware_app):
    request = _make_request("GET", "/items/123", path_params={"id": "1 OR 'a'='a'"})
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 400


def test_middleware_passes_valid(middleware_app):
    request = _make_request(
        "POST",
        "/submit",
        query_params={"q": "ok"},
        body={"name": "safe"},
        path_params={"id": "123"},
    )
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 200
    call_next.assert_awaited_once()


def test_middleware_fail_open(monkeypatch, middleware_app):
    request = _make_request("GET", "/boom", query_params={"q": "ok"})
    bad_validator = SecurityInputValidator()
    monkeypatch.setattr(bad_validator, "validate_dict", MagicMock(side_effect=RuntimeError("boom")))
    middleware_app.validator = bad_validator
    call_next = AsyncMock(return_value=JSONResponse({"ok": 1}))
    response = asyncio.run(middleware_app.dispatch(request, call_next))
    assert response.status_code == 200
    call_next.assert_awaited_once()


# ---------------------------------------------------------------------------
# core.ai.rag.reranker
# ---------------------------------------------------------------------------
def _make_chunk(text, embedding=None):
    return DocumentChunk(
        id="c1",
        document_id="d1",
        content=text,
        chunk_index=0,
        metadata={},
        embedding=embedding,
    )


def _make_result(text, score=0.5, embedding=None):
    return RetrievalResult(
        chunk=_make_chunk(text, embedding=embedding),
        score=score,
        metadata={},
    )


def test_reranker_base_raises():
    with pytest.raises(NotImplementedError):
        asyncio.run(Reranker().rerank("q", [], 5))


def test_cross_encoder_no_results():
    reranker = CrossEncoderReranker()
    assert asyncio.run(reranker.rerank("q", [], 5)) == []


def test_cross_encoder_loads_and_reranks(monkeypatch):
    class FakeCrossEncoder:
        def __init__(self, model_name, device="cpu"):
            self.model_name = model_name
            self.device = device

        def predict(self, pairs):
            return [0.3, 0.1, 0.2]

    fake_module = types.SimpleNamespace(CrossEncoder=FakeCrossEncoder)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    reranker = CrossEncoderReranker()
    results = [_make_result("a"), _make_result("b"), _make_result("c")]
    ranked = asyncio.run(reranker.rerank("q", results, 2))
    assert len(ranked) == 2
    assert ranked[0].score > ranked[1].score


def test_cross_encoder_import_unavailable(monkeypatch):
    fake_module = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    reranker = CrossEncoderReranker()
    results = [_make_result("a")]
    assert asyncio.run(reranker.rerank("q", results, 1)) == results


def test_cross_encoder_predict_exception(monkeypatch):
    class BadCrossEncoder:
        def __init__(self, *a, **k):
            pass

        def predict(self, pairs):
            raise RuntimeError("model down")

    fake_module = types.SimpleNamespace(CrossEncoder=BadCrossEncoder)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    reranker = CrossEncoderReranker()
    results = [_make_result("a"), _make_result("b")]
    ranked = asyncio.run(reranker.rerank("q", results, 1))
    assert len(ranked) == 1


def test_mmr_no_results():
    reranker = MMRReranker(lambda_param=0.5)
    assert asyncio.run(reranker.rerank("q", [], 5)) == []


def test_mmr_reranks_by_diversity():
    reranker = MMRReranker(lambda_param=0.5)
    results = [
        _make_result("a", 0.9, embedding=[1.0, 0.0, 0.0]),
        _make_result("b", 0.8, embedding=[0.0, 1.0, 0.0]),
        _make_result("c", 0.7, embedding=[0.99, 0.1, 0.0]),
    ]
    ranked = asyncio.run(reranker.rerank("q", results, 2))
    assert len(ranked) == 2
    assert ranked[0].chunk.content == "a"
    assert ranked[1].chunk.content == "b"


def test_mmr_no_embeddings():
    reranker = MMRReranker(lambda_param=0.5)
    results = [_make_result("a", 0.9), _make_result("b", 0.8)]
    ranked = asyncio.run(reranker.rerank("q", results, 2))
    assert len(ranked) == 2
    assert ranked[0].chunk.content == "a"


def test_mmr_rerank_exception(monkeypatch):
    reranker = MMRReranker()
    results = [_make_result("a"), _make_result("b")]
    monkeypatch.setattr(
        reranker, "_compute_similarity", MagicMock(side_effect=RuntimeError("boom"))
    )
    ranked = asyncio.run(reranker.rerank("q", results, 2))
    assert len(ranked) == 2


def test_mmr_compute_similarity():
    reranker = MMRReranker()
    c1 = _make_chunk("a", embedding=[1.0, 0.0])
    c2 = _make_chunk("b", embedding=[0.0, 1.0])
    c3 = _make_chunk("c", embedding=None)
    c4 = _make_chunk("d", embedding=[0.0, 0.0])
    assert reranker._compute_similarity(c1, c2) == 0.0
    assert reranker._compute_similarity(c1, c3) == 0.0
    assert reranker._compute_similarity(c1, c1) == 1.0
    assert reranker._compute_similarity(c1, c4) == 0.0


def test_reranking_pipeline():
    class NoOpReranker(Reranker):
        async def rerank(self, query, results, top_k):
            return results[:top_k]

    mmr = MMRReranker(lambda_param=0.5)
    pipeline = RerankingPipeline([NoOpReranker(), mmr])
    results = [
        _make_result("a", 0.9, embedding=[1.0, 0.0]),
        _make_result("b", 0.8, embedding=[0.0, 1.0]),
    ]
    ranked = asyncio.run(pipeline.rerank("q", results, 2))
    assert len(ranked) == 2


# ---------------------------------------------------------------------------
# core.enhanced_caching
# ---------------------------------------------------------------------------
class FakeRedisClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._store = {}

    def ping(self):
        return True

    def get(self, key):
        return self._store.get(key)

    def setex(self, key, ttl, value):
        self._store[key] = value

    def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    def keys(self, pattern):
        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    def info(self):
        return {
            "connected_clients": 1,
            "used_memory_human": "1M",
            "db0": {"keys": 0},
            "keyspace_hits": 5,
            "keyspace_misses": 2,
        }


class BadPingRedisClient(FakeRedisClient):
    def ping(self):
        raise RuntimeError("redis down")


class BadInfoRedisClient(FakeRedisClient):
    def info(self):
        raise RuntimeError("info failed")


@pytest.fixture
def fake_redis(monkeypatch):
    monkeypatch.setattr("core.enhanced_caching.redis.Redis", FakeRedisClient)


def test_redis_backend_get_set_delete(fake_redis):
    backend = RedisCacheBackend()
    assert backend.set("key1", {"a": 1}) is True
    assert backend.get("key1") == {"a": 1}
    assert backend.delete("key1") is True
    assert backend.get("key1") is None


def test_redis_backend_flush_pattern(fake_redis):
    backend = RedisCacheBackend()
    backend.set("user:1", "x")
    backend.set("user:2", "y")
    backend.set("other:1", "z")
    assert backend.flush_pattern("user:*") == 2
    assert backend.get("user:1") is None
    assert backend.get("other:1") == "z"


def test_redis_backend_get_stats(fake_redis):
    backend = RedisCacheBackend()
    stats = backend.get_stats()
    assert stats["connected_clients"] == 1
    assert "hits" in stats


def test_redis_backend_no_client(monkeypatch):
    monkeypatch.setattr("core.enhanced_caching.redis.Redis", BadPingRedisClient)
    backend = RedisCacheBackend()
    assert backend.client is None
    assert backend.get("x") is None
    assert backend.set("x", 1) is False
    assert backend.delete("x") is False
    assert backend.flush_pattern("x:*") == 0
    assert backend.get_stats() == {"error": "Not connected"}


def test_redis_backend_info_error(monkeypatch):
    monkeypatch.setattr("core.enhanced_caching.redis.Redis", BadInfoRedisClient)
    backend = RedisCacheBackend()
    stats = backend.get_stats()
    assert "error" in stats


def test_cache_warmer():
    backend = MagicMock()
    warmer = CacheWarmer(backend)

    async def sample_task():
        return {"k1": "v1", "k2": "v2"}

    warmer.register_warmup_task(sample_task)
    assert len(warmer.warmup_tasks) == 1
    asyncio.run(warmer.warmup_cache())
    assert backend.set.call_count == 2


def test_cache_invalidation(fake_redis):
    backend = RedisCacheBackend()
    backend.set("users:1", "x")
    backend.set("users:2", "y")
    CacheInvalidationStrategy.invalidate_by_prefix(backend, "users")
    assert backend.get("users:1") is None

    backend.set("tag:x:1", "a")
    CacheInvalidationStrategy.invalidate_by_tags(backend, ["x"])
    assert backend.get("tag:x:1") is None

    CacheInvalidationStrategy.invalidate_by_time(backend, 3600)

    not_redis = MagicMock()
    CacheInvalidationStrategy.invalidate_by_prefix(not_redis, "foo")


@pytest.mark.parametrize("backend", [None, MagicMock()])
def test_smart_cache(backend):
    if backend is None:
        target = MagicMock()
    else:
        backend.get.return_value = None
        target = backend

    call_count = {"n": 0}

    @smart_cache(ttl=60, key_prefix="calc", cache_backend=backend)
    async def calc(a, b):
        call_count["n"] += 1
        return a + b

    assert asyncio.run(calc(1, 2)) == 3
    if backend:
        backend.set.assert_called_once()
    assert call_count["n"] == 1


def test_smart_cache_hit_and_condition():
    backend = MagicMock()
    backend.get.return_value = {"cached": True}

    @smart_cache(ttl=120, cache_backend=backend, condition=lambda a, b: a > 0)
    async def calc(a, b):
        return a + b

    assert asyncio.run(calc(1, 2)) == {"cached": True}
    backend.get.assert_called_once()
    backend.set.assert_not_called()

    backend.get.return_value = None
    assert asyncio.run(calc(1, 5)) == 6
    backend.set.assert_called_once()


async def _warm_task():
    return {"system:config": {"v": 1}}


def test_setup_enhanced_caching(fake_redis):
    result = asyncio.run(setup_enhanced_caching())
    assert result["status"] == "success"
    assert result["backend"] == "redis"
    assert "cache_stats" in result
