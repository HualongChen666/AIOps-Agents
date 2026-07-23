# -*- coding: utf-8 -*-
"""Targeted tests for core.alert_engine pure/helper functions and P2 classes."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.alert_engine as ae


@pytest.fixture(autouse=True)
def _clean_alert_state() -> None:
    """Reset module-level mutable state before each test."""
    ae._ssh_failed_window.clear()
    ae._ssh_last_alert_time.clear()
    ae._dedup_cache.clear()
    ae._ws_subscribers.clear()
    yield
    ae._ssh_failed_window.clear()
    ae._ssh_last_alert_time.clear()
    ae._dedup_cache.clear()
    ae._ws_subscribers.clear()


class TestSSHBruteForce:
    def test_first_call_returns_none(self) -> None:
        assert ae._check_ssh_brute_force("host1", 5) is None

    def test_threshold_trigger(self) -> None:
        ae._check_ssh_brute_force("host1", 5)
        alert = ae._check_ssh_brute_force("host1", 25)
        assert isinstance(alert, dict)
        assert alert["level"] == "critical"
        assert alert["metric"] == "ssh_failed_logins"
        assert "host1" in alert["id"]

    def test_negative_increment_resets_window(self) -> None:
        ae._check_ssh_brute_force("host1", 20)
        # logrotate caused count to drop: should reset the baseline and not alert
        assert ae._check_ssh_brute_force("host1", 2) is None
        # the new baseline is 2; a second sample with the same value still does not alert
        assert ae._check_ssh_brute_force("host1", 2) is None
        # once the count increases above threshold from the new baseline, alert fires
        alert = ae._check_ssh_brute_force("host1", 25)
        assert isinstance(alert, dict)
        assert alert["value"] == 23

    def test_cooldown_prevents_duplicate(self) -> None:
        ae._check_ssh_brute_force("host1", 5)
        ae._check_ssh_brute_force("host1", 25)
        assert ae._check_ssh_brute_force("host1", 45) is None

    def test_cooldown_expires(self) -> None:
        ae._check_ssh_brute_force("host1", 5)
        ae._check_ssh_brute_force("host1", 25)
        ae._ssh_last_alert_time["host1"] = datetime.datetime.now() - datetime.timedelta(
            seconds=ae._SSH_ALERT_COOLDOWN_SEC + 1
        )
        ae._check_ssh_brute_force("host1", 5)
        alert = ae._check_ssh_brute_force("host1", 35)
        assert isinstance(alert, dict)


class TestSSHCacheCleanup:
    def test_cleanup_expired_hosts(self) -> None:
        old = datetime.datetime.now() - datetime.timedelta(seconds=ae._SSH_CACHE_EXPIRY_SEC + 1)
        ae._ssh_failed_window["host1"] = [(old, 10)]
        ae._ssh_last_alert_time["host1"] = old
        ae._cleanup_ssh_brute_force_cache()
        assert "host1" not in ae._ssh_failed_window
        assert "host1" not in ae._ssh_last_alert_time

    def test_max_hosts_eviction(self) -> None:
        ae._SSH_CACHE_MAX_HOSTS = 2  # type: ignore[misc]
        now = datetime.datetime.now()
        ae._ssh_failed_window["h1"] = [(now, 1)]
        ae._ssh_failed_window["h2"] = [(now, 2)]
        ae._ssh_failed_window["h3"] = [(now, 3)]
        ae._cleanup_ssh_brute_force_cache()
        assert len(ae._ssh_failed_window) <= 2


class TestDedup:
    def test_dedup_key(self) -> None:
        assert ae._dedup_key({"metric": "cpu", "level": "warning"}) == "cpu_warning"

    def test_dedup_key_disk_device(self) -> None:
        alert = {"metric": "disk_percent", "level": "critical", "id": "DISK-C:-12:34:56"}
        assert ae._dedup_key(alert) == "disk_percent_critical_C:"

    def test_try_dedup_first_pass(self) -> None:
        assert ae._try_dedup({"metric": "cpu", "level": "warning"}) is False

    def test_try_dedup_second_intercept(self) -> None:
        alert = {"metric": "cpu", "level": "warning"}
        ae._try_dedup(alert)
        assert ae._try_dedup(alert) is True

    def test_try_dedup_window_expires(self) -> None:
        alert = {"metric": "cpu", "level": "warning"}
        assert ae._try_dedup(alert) is False
        # a second call inside the window is intercepted and increments repeat_count
        assert ae._try_dedup(alert) is True
        ae._dedup_cache["cpu_warning"]["last_time"] = datetime.datetime.now() - datetime.timedelta(
            seconds=ae._DEDUP_WINDOW_SEC + 1
        )
        # the window has expired, so the alert passes and reports the suppressed count
        assert ae._try_dedup(alert) is False
        assert alert.get("prev_suppressed") == 1

    def test_dedup_cache_max(self) -> None:
        ae._DEDUP_CACHE_MAX = 2  # type: ignore[misc]
        for i in range(3):
            ae._try_dedup({"metric": f"m{i}", "level": "warning"})
        assert len(ae._dedup_cache) <= 2

    def test_get_dedup_stats(self) -> None:
        ae._try_dedup({"metric": "cpu", "level": "warning"})
        stats = ae.get_dedup_stats()
        assert stats["cache_size"] == 1
        assert stats["active_windows"] == 1

    def test_clear_dedup_cache(self) -> None:
        ae._try_dedup({"metric": "cpu", "level": "warning"})
        assert ae.clear_dedup_cache() == 1
        assert len(ae._dedup_cache) == 0

    def test_clear_ssh_cache(self) -> None:
        ae._ssh_failed_window["h"] = []
        assert ae.clear_ssh_brute_force_cache() == 1
        assert len(ae._ssh_failed_window) == 0

    def test_cleanup_dedup_cache_expired(self) -> None:
        ae._try_dedup({"metric": "cpu", "level": "warning"})
        ae._dedup_cache["cpu_warning"]["last_time"] = datetime.datetime.now() - datetime.timedelta(
            seconds=ae._DEDUP_WINDOW_SEC * 2 + 1
        )
        ae._cleanup_dedup_cache()
        assert "cpu_warning" not in ae._dedup_cache


class TestThresholds:
    def test_safe_float(self) -> None:
        assert ae._safe_float("3.14") == 3.14
        assert ae._safe_float(None, 1.0) == 1.0
        assert ae._safe_float("abc", 2.0) == 2.0

    def test_cpu_levels(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        assert ae._cpu_level(30.0) == "normal"
        assert ae._cpu_level(85.0) == "warning"
        assert ae._cpu_level(96.0) == "critical"

    def test_mem_levels(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        assert ae._mem_level(40.0) == "normal"
        assert ae._mem_level(88.0) == "warning"
        assert ae._mem_level(96.0) == "critical"

    def test_disk_level(self) -> None:
        assert ae._disk_level(50.0) == "normal"
        assert ae._disk_level(92.0) == "warning"
        assert ae._disk_level(99.0) == "critical"

    def test_dynamic_threshold(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": True})
        with patch.object(ae.metrics_history, "get_dynamic_threshold", return_value=(77.0, {})):
            assert ae._get_dynamic_warn_threshold("cpu", 80.0) == 77.0

    def test_dynamic_threshold_disabled(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        assert ae._get_dynamic_warn_threshold("cpu", 80.0) == 80.0

    def test_dynamic_threshold_exception(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": True})
        with patch.object(
            ae.metrics_history, "get_dynamic_threshold", side_effect=RuntimeError("boom")
        ):
            assert ae._get_dynamic_warn_threshold("cpu", 80.0) == 80.0


class TestCheckAndGenerateAlerts:
    def test_empty_metrics(self) -> None:
        assert ae.check_and_generate_alerts({}) == []

    def test_none_metrics(self) -> None:
        assert ae.check_and_generate_alerts({"cpu": None, "memory": None, "disk": None}) == []

    def test_cpu_warning(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        alerts = ae.check_and_generate_alerts({"cpu": {"usage_percent": 85.0}})
        assert len(alerts) == 1
        assert alerts[0]["metric"] == "cpu_percent"

    def test_memory_warning(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        alerts = ae.check_and_generate_alerts({"memory": {"usage_percent": 88.0}})
        assert len(alerts) == 1
        assert alerts[0]["metric"] == "memory_percent"

    def test_disk_warning(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        alerts = ae.check_and_generate_alerts({"disk": [{"device": "C:", "usage_percent": 92.0}]})
        assert len(alerts) == 1
        assert alerts[0]["metric"] == "disk_percent"

    def test_dedup_filters_candidates(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        alerts1 = ae.check_and_generate_alerts({"cpu": {"usage_percent": 85.0}})
        assert len(alerts1) == 1
        # same metric/level should be deduped within window
        assert ae._try_dedup(alerts1[0]) is False
        alerts2 = ae.check_and_generate_alerts({"cpu": {"usage_percent": 86.0}})
        assert len(alerts2) == 1
        assert ae._try_dedup(alerts2[0]) is True


class TestWebSocketAndBroadcast:
    def test_register_unregister_ws(self) -> None:
        ws = MagicMock()
        ae.register_ws(ws)
        assert ws in ae._ws_subscribers
        ae.unregister_ws(ws)
        assert ws not in ae._ws_subscribers

    @pytest.mark.asyncio
    async def test_broadcast_with_subscribers(self) -> None:
        ok_ws = MagicMock()
        ok_ws.send_text = AsyncMock()
        dead_ws = MagicMock()
        dead_ws.send_text = AsyncMock(side_effect=RuntimeError("closed"))
        ae.register_ws(ok_ws)
        ae.register_ws(dead_ws)
        await ae.broadcast({"type": "test"})
        ok_ws.send_text.assert_awaited_once()
        assert dead_ws not in ae._ws_subscribers
        assert ok_ws in ae._ws_subscribers

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers(self) -> None:
        await ae.broadcast({"type": "test"})


class TestSummary:
    @pytest.mark.asyncio
    async def test_get_summary_metrics(self, monkeypatch) -> None:
        with patch("core.stats_engine.get_real_summary", return_value={"alerts": 1}) as m:
            assert await ae.get_summary_metrics() == {"alerts": 1}
            m.assert_called_once()


class TestLinuxSecurityAlerts:
    @pytest.mark.asyncio
    async def test_check_linux_security_alerts(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        with (
            patch("core.db_engine.alert_repository.save", new_callable=AsyncMock) as save,
            patch("core.notify_engine.send_alert_notification", new_callable=AsyncMock) as notify,
            patch("core.auto_heal.try_auto_heal", new_callable=AsyncMock, return_value={}),
            patch("core.alert_engine.broadcast", new_callable=AsyncMock) as broadcast,
        ):
            # Two consecutive samples for the same host are needed to detect an increment.
            linux_results = [
                {
                    "status": "ok",
                    "name": "host1",
                    "metrics": {"ssh_failed_logins": {"value": "25"}},
                },
                {
                    "status": "ok",
                    "name": "host1",
                    "metrics": {"ssh_failed_logins": {"value": "35"}},
                },
            ]
            alerts = await ae.check_linux_security_alerts(linux_results)
            assert len(alerts) == 1
            assert alerts[0]["alert_type"] == "ssh_brute_force"
            save.assert_awaited_once()
            notify.assert_awaited_once()
            broadcast.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_bad_status(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        linux_results = [
            {"status": "error", "name": "host1", "metrics": {"ssh_failed_logins": {"value": "25"}}}
        ]
        with (
            patch("core.db_engine.alert_repository.save", new_callable=AsyncMock),
            patch("core.notify_engine.send_alert_notification", new_callable=AsyncMock),
            patch("core.auto_heal.try_auto_heal", new_callable=AsyncMock, return_value={}),
            patch("core.alert_engine.broadcast", new_callable=AsyncMock),
        ):
            alerts = await ae.check_linux_security_alerts(linux_results)
        assert alerts == []

    @pytest.mark.asyncio
    async def test_check_linux_security_alerts_invalid_value(self, monkeypatch) -> None:
        monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
        linux_results = [
            {"status": "ok", "name": "host1", "metrics": {"ssh_failed_logins": {"value": "ERROR"}}}
        ]
        with (
            patch("core.db_engine.alert_repository.save", new_callable=AsyncMock),
            patch("core.notify_engine.send_alert_notification", new_callable=AsyncMock),
            patch("core.auto_heal.try_auto_heal", new_callable=AsyncMock, return_value={}),
            patch("core.alert_engine.broadcast", new_callable=AsyncMock),
        ):
            alerts = await ae.check_linux_security_alerts(linux_results)
        assert alerts == []


class TestAlertTopologyCorrelation:
    def test_build_and_correlate(self) -> None:
        corr = ae.AlertTopologyCorrelation()
        alerts = [
            {"source": "server1", "type": "cpu_high"},
            {"source": "server1", "type": "disk_high"},
        ]
        topo = corr.build_topology_from_alerts(alerts)
        assert topo["server1"] == ["processes", "storage"]
        roots = corr.correlate_alerts_with_topology({"source": "server1"})
        assert roots == []

    def test_impact_analysis(self) -> None:
        corr = ae.AlertTopologyCorrelation()
        corr.build_topology_from_alerts([{"source": "server1", "type": "cpu_high"}])
        impact = corr.get_impact_analysis({"source": "processes"})
        assert impact["source"] == "processes"
        assert "server1" in impact["affected_services"]


class TestAutomaticAlertRouter:
    def test_route_alert(self) -> None:
        router = ae.AutomaticAlertRouter()
        router.strategy = ae.AlertRoutingStrategy.RULE_BASED
        router.add_route("crit", {"severity": "critical"}, "email", priority=10)
        router.add_route("warn", {"severity": "warning"}, "webhook", priority=5)
        assert router.route_alert({"severity": "critical"}) == ["email"]
        assert router.route_alert({"severity": "warning"}) == ["webhook"]

    def test_ml_route(self) -> None:
        router = ae.AutomaticAlertRouter()
        router.strategy = ae.AlertRoutingStrategy.ML_BASED
        assert router.route_alert({"severity": "info"}) == ["webhook"]
        assert set(router.route_alert({"severity": "critical"})) == {"email", "sms", "webhook"}

    def test_routing_stats(self) -> None:
        router = ae.AutomaticAlertRouter()
        router.strategy = ae.AlertRoutingStrategy.RULE_BASED
        router.add_route("warn", {"severity": "warning"}, "webhook")
        router.route_alert({"severity": "warning"})
        stats = router.get_routing_stats()
        assert stats["total_routes"] == 1
        assert stats["channel_distribution"]["webhook"] == 1


class TestAlertTrendPredictor:
    def test_predict_moving_average(self) -> None:
        predictor = ae.AlertTrendPredictor()
        for i in range(12):
            predictor.add_historical_data("cpu", float(i))
        pred = predictor.predict_trend("cpu", 3)
        assert pred is not None
        assert len(pred.predicted_values) == 3

    def test_predict_linear_regression(self) -> None:
        predictor = ae.AlertTrendPredictor(model=ae.TrendPredictionModel.LINEAR_REGRESSION)
        for i in range(12):
            predictor.add_historical_data("cpu", float(i))
        pred = predictor.predict_trend("cpu", 3)
        assert pred is not None
        assert pred.trend_direction in ("increasing", "decreasing", "stable")

    def test_predict_insufficient_data(self) -> None:
        predictor = ae.AlertTrendPredictor()
        predictor.add_historical_data("cpu", 1.0)
        assert predictor.predict_trend("cpu") is None

    def test_get_prediction_summary(self) -> None:
        predictor = ae.AlertTrendPredictor()
        for i in range(12):
            predictor.add_historical_data("cpu", float(i))
        predictor.predict_trend("cpu", 3)
        summary = predictor.get_prediction_summary()
        assert summary["metrics_with_predictions"] == 1


class TestGlobalInstances:
    def test_global_instances_exist(self) -> None:
        assert isinstance(ae.alert_engine, ae.AutomaticAlertRouter)
        assert isinstance(ae.alert_topology_correlation, ae.AlertTopologyCorrelation)
        assert isinstance(ae.alert_trend_predictor, ae.AlertTrendPredictor)

    def test_alert_engine_default_routes(self) -> None:
        assert len(ae.alert_engine.routes) >= 2
