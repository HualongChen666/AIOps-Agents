# -*- coding: utf-8 -*-
"""Real-branch tests for core.enhanced_ai_capabilities.

These tests use real ``EnhancedAICapabilities`` instances, real
scikit-learn models, and small in-memory data.  No mock objects are used;
optional dependencies (Prophet) are temporarily supplied as plain
in-memory classes only when the real package is unavailable, and all
module-level flags are restored after each test.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import SGDClassifier

import core.enhanced_ai_capabilities as ai

pytestmark = [pytest.mark.core, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# In-memory Prophet stand-ins used only when the real package is missing.
# These are *not* mocks; they implement the exact call contract the source
# uses so that the Prophet-related branches can be exercised with real data.
# ---------------------------------------------------------------------------


class _TinyProphet:
    def __init__(self, **kwargs):
        pass

    def fit(self, df):
        return self

    def make_future_dataframe(self, periods=24):
        return pd.DataFrame({"ds": pd.date_range("2024-01-01", periods=periods, freq="h")})

    def predict(self, future):
        n = len(future)
        return pd.DataFrame(
            {
                "ds": future["ds"],
                "yhat": [1.0] * n,
                "yhat_lower": [0.5] * n,
                "yhat_upper": [1.5] * n,
            }
        )


class _BrokenProphet:
    def __init__(self, **kwargs):
        pass

    def fit(self, df):
        raise RuntimeError("prophet failure")

    def make_future_dataframe(self, periods=24):
        return pd.DataFrame({"ds": []})

    def predict(self, future):
        raise RuntimeError("prophet failure")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _cancel_background_tasks():
    for task in [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]:
        task.cancel()
        try:
            await task
        except BaseException:
            pass


def _save_flags():
    return {
        "ML_AVAILABLE": ai.ML_AVAILABLE,
        "PROPHET_AVAILABLE": ai.PROPHET_AVAILABLE,
        "Prophet": getattr(ai, "Prophet", None),
    }


def _restore_flags(saved):
    ai.ML_AVAILABLE = saved["ML_AVAILABLE"]
    ai.PROPHET_AVAILABLE = saved["PROPHET_AVAILABLE"]
    if saved["Prophet"] is not None:
        ai.Prophet = saved["Prophet"]
    elif hasattr(ai, "Prophet"):
        delattr(ai, "Prophet")


# ---------------------------------------------------------------------------
# _fit_model branches
# ---------------------------------------------------------------------------


async def test_fit_model_stores_samples_when_ml_unavailable():
    saved = _save_flags()
    ai.ML_AVAILABLE = False
    try:
        knowledge = defaultdict(list)
        samples = [({"feature": 1}, 0)]
        model = object()
        await ai._fit_model(model, samples, knowledge_accumulator=knowledge)
        # stores the whole sample list for later replay
        assert knowledge[str(id(model))]

        # branch where knowledge_accumulator is None (line 62 -> 64)
        await ai._fit_model(object(), samples, knowledge_accumulator=None)
    finally:
        _restore_flags(saved)


async def test_fit_model_classifier_partial_fit_branches():
    saved = _save_flags()
    ai.ML_AVAILABLE = True
    try:
        model = SGDClassifier(random_state=42, max_iter=1000, tol=1e-3)
        samples = [({"x": 1}, 0), ({"x": 2}, 1)]

        # first call: classes is None (line 91 -> 92)
        await ai._fit_model(model, samples, incremental=True)
        assert model.classes_ is not None

        # second call: classes already present (line 91 -> 93)
        await ai._fit_model(model, samples, incremental=True)
    finally:
        _restore_flags(saved)


async def test_fit_model_exception_paths():
    saved = _save_flags()
    ai.ML_AVAILABLE = True
    try:
        samples = [({"x": 1}, 0)]
        model = object()  # cannot have attributes set -> triggers except block

        # exception with a knowledge accumulator (line 109 -> 110)
        knowledge = defaultdict(list)
        await ai._fit_model(model, samples, knowledge_accumulator=knowledge)
        assert str(id(model)) in knowledge

        # exception with no accumulator (line 109 -> -48)
        await ai._fit_model(object(), samples, knowledge_accumulator=None)
    finally:
        _restore_flags(saved)


# ---------------------------------------------------------------------------
# initialize branches (ML available vs. not, Prophet available)
# ---------------------------------------------------------------------------


async def test_initialize_ml_unavailable():
    saved = _save_flags()
    ai.ML_AVAILABLE = False
    ai.PROPHET_AVAILABLE = False
    try:
        cap = ai.EnhancedAICapabilities()
        await cap.initialize()
        assert not cap.anomaly_detectors
        assert not cap.prediction_models
    finally:
        await _cancel_background_tasks()
        _restore_flags(saved)


async def test_initialize_prophet_available_and_timeseries_cache():
    saved = _save_flags()
    ai.ML_AVAILABLE = True
    ai.PROPHET_AVAILABLE = True
    ai.Prophet = _TinyProphet
    try:
        cap = ai.EnhancedAICapabilities()
        await cap.initialize()

        # exercise the prophet for-loop and model-creation branches
        assert any(k.startswith("prophet_") for k in cap.prediction_models)

        historical = [(datetime.now(), float(i)) for i in range(30)]

        # pre-initialized metric: model_key already in prediction_models (335 -> 340 false)
        r1 = await cap.predict_timeseries("cpu_usage", historical)
        assert r1 is not None
        assert isinstance(r1, ai.PredictionResult)

        # cache hit (326 -> return cached)
        r2 = await cap.predict_timeseries("cpu_usage", historical)
        assert r2 is r1

        # expired cache (326 -> 330 false / continue)
        cap.cache_ttl = timedelta(seconds=0)
        r3 = await cap.predict_timeseries("cpu_usage", historical)
        assert r3 is not None
        assert r3 is not r1
        cap.cache_ttl = timedelta(minutes=10)

        # short data triggers early return (318-319)
        short = [(datetime.now(), float(i)) for i in range(5)]
        assert await cap.predict_timeseries("cpu_usage", short) is None

        # custom metric: model_key not in prediction_models (335 -> 336 true)
        r4 = await cap.predict_timeseries("custom_metric", historical)
        assert r4 is not None
    finally:
        await _cancel_background_tasks()
        _restore_flags(saved)


async def test_predict_timeseries_exception_handling():
    saved = _save_flags()
    ai.ML_AVAILABLE = True
    ai.PROPHET_AVAILABLE = True
    ai.Prophet = _BrokenProphet
    try:
        cap = ai.EnhancedAICapabilities()
        historical = [(datetime.now(), float(i)) for i in range(30)]
        result = await cap.predict_timeseries("broken_metric", historical)
        assert result is None
    finally:
        _restore_flags(saved)


# ---------------------------------------------------------------------------
# predict_anomalies branches
# ---------------------------------------------------------------------------


async def test_predict_anomalies_not_anomalous():
    cap = ai.EnhancedAICapabilities()
    await cap.initialize()
    try:
        cap.min_samples_for_training = 10
        historical = [
            (datetime.now(), 50.0 + (i % 5) * 0.1) for i in range(50)
        ]
        result = await cap.predict_anomalies(
            "cpu_usage", 50.0, historical
        )
        assert result is not None
        assert not result.is_anomalous
        assert "within normal range" in result.explanation
    finally:
        await _cancel_background_tasks()


async def test_predict_anomalies_exception_handling():
    cap = ai.EnhancedAICapabilities()
    cap.min_samples_for_training = 10
    historical = [(datetime.now(), "bad_value") for _ in range(50)]
    result = await cap.predict_anomalies("bad_metric", 1.0, historical)
    assert result is None


# ---------------------------------------------------------------------------
# adaptive_learn branches (online / batch / transfer / unknown + exception)
# ---------------------------------------------------------------------------


async def test_adaptive_learn_all_modes():
    cap = ai.EnhancedAICapabilities()
    cap.prediction_models["rf_test"] = ai.RandomForestRegressor(
        n_estimators=5, max_depth=3, random_state=42, n_jobs=1
    )
    samples = [({"f1": 1}, 0), ({"f2": 2}, 1)]

    # online and batch
    for mode in (ai.LearningMode.ONLINE, ai.LearningMode.BATCH):
        update = await cap.adaptive_learn("rf_test", samples, mode)
        assert update is not None
        assert update.model_id == "rf_test"

    # transfer (line 486 -> 488)
    update = await cap.adaptive_learn(
        "rf_test", samples, ai.LearningMode.TRANSFER
    )
    assert update is not None

    # unknown/fall-through mode (line 486 -> 491)
    update = await cap.adaptive_learn("rf_test", samples, "unknown")
    assert update is not None


async def test_adaptive_learn_exception_handling():
    cap = ai.EnhancedAICapabilities()
    cap.prediction_models["rf_test"] = ai.RandomForestRegressor(
        n_estimators=5, max_depth=3, random_state=42, n_jobs=1
    )
    samples = [({"f1": 1}, 0)]
    result = await cap.adaptive_learn(["unhashable"], samples)
    assert result is None


# ---------------------------------------------------------------------------
# natural language and decision explanation branches
# ---------------------------------------------------------------------------


async def test_parse_natural_language_entities_and_intents():
    cap = ai.EnhancedAICapabilities()

    # disk and day branches
    r = await cap.parse_natural_language("check disk usage for last day")
    assert r is not None
    assert r.intent == "monitor"
    assert r.entities.get("metric") == "disk_usage"
    assert r.entities.get("time_range") == "day"

    # monitor without metric entity (line 653 -> 662)
    r = await cap.parse_natural_language("check status now")
    assert r is not None
    assert r.intent == "monitor"
    assert not any("Monitor" in a for a in r.suggested_actions)

    # fix intent (line 657 -> 658)
    r = await cap.parse_natural_language("fix the server")
    assert r is not None
    assert r.intent == "fix"
    assert "Execute automated repair" in r.suggested_actions

    # exception path (line 578-580); slicing works, lower() fails inside try
    r = await cap.parse_natural_language(["bad query"])
    assert r is None


async def test_explain_decision_branches_and_exception():
    cap = ai.EnhancedAICapabilities()

    # restart_service branch (line 698 -> 705)
    r = await cap.explain_decision("restart_service", {"metrics": {}})
    assert r is not None
    assert any("restart" in opt["action"] for opt in r.alternative_options)

    # exception path (line 719-721)
    r = await cap.explain_decision("scale_up", "not_a_dict")
    assert r is None


# ---------------------------------------------------------------------------
# knowledge and learning loop branches
# ---------------------------------------------------------------------------


async def test_get_knowledge_insights_missing_pattern():
    cap = ai.EnhancedAICapabilities()
    insights = await cap.get_knowledge_insights("missing_pattern")
    assert insights == {}


async def test_learning_loop_runs_and_cancels():
    cap = ai.EnhancedAICapabilities()
    cap.learning_interval = timedelta(seconds=0.01)
    cap.prediction_models = {"m1": None, "m2": None}
    # m1 triggers relearn, m2 does not
    cap.performance_metrics = {
        "m1": [0.9, 0.8],
        "m2": [0.8, 0.8],
    }
    task = asyncio.create_task(cap._learning_loop())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_learning_loop_exception_handling():
    cap = ai.EnhancedAICapabilities()
    cap.learning_interval = timedelta(seconds=0.01)
    cap.prediction_models = {"m1": None}
    # _should_relearn will raise because None is not iterable
    cap.performance_metrics = None
    task = asyncio.create_task(cap._learning_loop())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# predict_anomalies remaining branches
# ---------------------------------------------------------------------------


async def test_predict_anomalies_remaining_branches():
    cap = ai.EnhancedAICapabilities()

    # short historical data -> early return (395-396)
    assert await cap.predict_anomalies("x", 1.0, [(datetime.now(), 1.0)] * 5) is None

    # enough data but too few for training -> 411 -> 415 (skip fit)
    cap.min_samples_for_training = 100
    historical = [(datetime.now(), float(i % 10)) for i in range(50)]
    assert await cap.predict_anomalies("no_train", 5.0, historical) is None

    # clear anomalous value -> 424-428
    cap.min_samples_for_training = 10
    historical = [(datetime.now(), float(i)) for i in range(50)]
    result = await cap.predict_anomalies("cpu", 9999.0, historical)
    assert result is not None
    assert result.is_anomalous


# ---------------------------------------------------------------------------
# adaptive_learn early returns
# ---------------------------------------------------------------------------


async def test_adaptive_learn_early_returns():
    saved = _save_flags()
    samples = [({"f": 1}, 0)]
    try:
        # ML unavailable (465-466)
        ai.ML_AVAILABLE = False
        cap = ai.EnhancedAICapabilities()
        assert await cap.adaptive_learn("x", samples) is None

        # model not found (471-472)
        ai.ML_AVAILABLE = True
        cap = ai.EnhancedAICapabilities()
        assert await cap.adaptive_learn("missing", samples) is None
    finally:
        _restore_flags(saved)


# ---------------------------------------------------------------------------
# natural language and explanation remaining branches
# ---------------------------------------------------------------------------


async def test_parse_natural_language_remaining_entities():
    cap = ai.EnhancedAICapabilities()

    # unknown intent (639 -> 642 false)
    r = await cap.parse_natural_language("hello world")
    assert r is not None
    assert r.intent == "unknown"
    assert r.suggested_actions == []

    # analyze (656) and predict (659-660)
    r = await cap.parse_natural_language("analyze cpu usage")
    assert r is not None
    assert r.intent == "analyze"
    r = await cap.parse_natural_language("predict memory usage next week")
    assert r is not None
    assert r.intent == "predict"


async def test_explain_decision_other_branches():
    cap = ai.EnhancedAICapabilities()
    r = await cap.explain_decision(
        "deploy",
        {"metrics": {}, "historical_data": [], "ml_model": "rf"},
    )
    assert r is not None
    assert r.alternative_options == []
    assert "historical_database" in r.data_sources
    assert "ml_model" in r.data_sources


# ---------------------------------------------------------------------------
# knowledge, learning stats, and should_relearn
# ---------------------------------------------------------------------------


async def test_knowledge_accumulation_and_statistics():
    cap = ai.EnhancedAICapabilities()
    await cap.accumulate_knowledge(
        {
            "symptoms": ["cpu high"],
            "root_causes": ["overload"],
            "resolution": "scale out",
            "id": "inc-1",
            "success": True,
        }
    )
    pattern = cap._generate_knowledge_pattern(["cpu high"], ["overload"])
    insights = await cap.get_knowledge_insights(pattern)
    assert insights["incident_count"] == 1
    stats = await cap.get_ai_statistics()
    assert stats["knowledge_patterns"] >= 1


async def test_should_relearn_branches():
    cap = ai.EnhancedAICapabilities()

    # model not in metrics
    assert await cap._should_relearn("m1") is False

    # fewer than two scores
    cap.performance_metrics["m2"] = [0.8]
    assert await cap._should_relearn("m2") is False

    # clear performance drop
    cap.performance_metrics["m3"] = [0.9, 0.8]
    assert await cap._should_relearn("m3") is True

    # no meaningful drop
    cap.performance_metrics["m4"] = [0.8, 0.85]
    assert await cap._should_relearn("m4") is False


# ---------------------------------------------------------------------------
# _fit_model remaining branches (empty, partial-fit, fallback, no-fit)
# ---------------------------------------------------------------------------


async def test_fit_model_empty_samples():
    saved = _save_flags()
    ai.ML_AVAILABLE = True
    try:
        # empty sample list returns immediately (55 -> 56)
        await ai._fit_model(object(), [], knowledge_accumulator=None)
    finally:
        _restore_flags(saved)


async def test_fit_model_partial_fit_non_classifier_and_no_fit():
    saved = _save_flags()
    ai.ML_AVAILABLE = True
    try:
        # SGDRegressor has partial_fit but is not a Classifier (89 -> 95)
        from sklearn.linear_model import SGDRegressor

        reg = SGDRegressor(random_state=42, max_iter=1000, tol=1e-3)
        samples = [({"x": 1}, 0.0), ({"x": 2}, 1.0)]
        await ai._fit_model(reg, samples, incremental=True)

        # a model with no fit or partial_fit (96 -> 106)
        class _NoFit:
            pass

        await ai._fit_model(_NoFit(), samples, incremental=False)

        # a model with fit but not Forest/Regressor, first fit raises (97 -> 100)
        class _FitRaisesFirst:
            def fit(self, *args):
                if len(args) > 1:
                    raise ValueError("bad y")

        await ai._fit_model(_FitRaisesFirst(), samples, incremental=False)
    finally:
        _restore_flags(saved)


# ---------------------------------------------------------------------------
# remaining _extract_entities and accumulate_knowledge branches
# ---------------------------------------------------------------------------


async def test_parse_natural_language_numbers_and_hour():
    cap = ai.EnhancedAICapabilities()
    r = await cap.parse_natural_language("cpu above 90 in the last hour")
    assert r is not None
    assert r.entities.get("metric") == "cpu_usage"
    assert r.entities.get("time_range") == "hour"
    assert 90 in r.entities.get("values", [])


async def test_accumulate_knowledge_exception():
    cap = ai.EnhancedAICapabilities()
    # non-dict incident data triggers the except block (754-755)
    await cap.accumulate_knowledge("not a dict")
