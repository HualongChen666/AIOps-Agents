# -*- coding: utf-8 -*-
"""cloud_collector.py

实现对三大公有云平台（AWS CloudWatch、Azure Monitor、阿里云 CloudMonitor）的统一采集入口。

每个云平台的采集细节封装在私有函数中，统一返回结构:
    {
        "provider": "aws|azure|alibaba",
        "timestamp": "ISO8601 UTC",
        "metrics": [{"name": str, "value": float, "unit": str, "dimensions": dict}],
        "raw": dict   # 原始 SDK 返回的完整数据（便于审计）
    }

该模块遵循项目已有的采集模式：
- 通过 `push_to_loki` 将结果写入 Loki
- 通过 `record_collect` 将 JSON 存入 SQLite（stats_engine）
- 使用 `register_self_pid` 防止误杀（基于 `CLOUD_HOST_MAX_FAILURES`/`CLOUD_HOST_COOLDOWN_SEC`）
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, List

from config import CLOUD_PROVIDERS  # type: ignore
from core.command_guard import register_self_pid  # type: ignore
from core.loki_sink import push_to_loki  # type: ignore
from core.stats_engine import record_collect  # type: ignore

_logger = logging.getLogger(__name__)

# ---------- 内部帮助函数 ----------


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=timezone.utc).isoformat()


# ---- AWS CloudWatch ----


def _collect_aws(cfg: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import boto3

        session = boto3.Session(
            aws_access_key_id=cfg["access_key"],
            aws_secret_access_key=cfg["secret_key"],
            region_name=cfg["region"],
        )
        cw = session.client("cloudwatch")
        metric_data = []
        for metric_name in cfg.get("metrics", []):
            resp = cw.get_metric_statistics(
                Namespace=cfg.get("namespace", "AWS/EC2"),
                MetricName=metric_name,
                Dimensions=cfg.get("dimensions", []),
                StartTime=datetime.now(timezone.utc) - timedelta(minutes=5),
                EndTime=datetime.now(timezone.utc),
                Period=300,
                Statistics=["Average"],
            )
            datapoints = resp.get("Datapoints", [])
            if datapoints:
                latest = max(datapoints, key=lambda d: d["Timestamp"])
                metric_data.append(
                    {
                        "name": metric_name,
                        "value": latest.get("Average", 0.0),
                        "unit": latest.get("Unit", ""),
                        "dimensions": {d["Name"]: d["Value"] for d in cfg.get("dimensions", [])},
                    }
                )
        return {
            "provider": "aws",
            "timestamp": _iso_timestamp(),
            "metrics": metric_data,
            "raw": cfg,
        }
    except Exception as e:
        _logger.error("AWS CloudWatch collection failed: %s", e, exc_info=True)
        raise


# ---- Azure Monitor ----


def _collect_azure(cfg: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from azure.identity import ClientSecretCredential
        from azure.monitor.query import MetricsQueryClient

        credential = ClientSecretCredential(
            tenant_id=cfg["tenant_id"],
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
        )
        client = MetricsQueryClient(credential)
        metric_data = []
        for metric_name in cfg.get("metrics", []):
            resp = client.query_resource(
                cfg["resource_id"],
                metric_names=[metric_name],
                timespan="PT5M",
                interval="PT5M",
            )
            for metric in resp.metrics:
                if metric.timeseries:
                    ts = metric.timeseries[0]
                    if ts.data:
                        latest = ts.data[-1]
                        metric_data.append(
                            {
                                "name": metric_name,
                                "value": latest.average or 0.0,
                                "unit": metric.unit,
                                "dimensions": {},
                            }
                        )
        return {
            "provider": "azure",
            "timestamp": _iso_timestamp(),
            "metrics": metric_data,
            "raw": cfg,
        }
    except Exception as e:
        _logger.error("Azure Monitor collection failed: %s", e, exc_info=True)
        raise


# ---- Alibaba Cloud Monitor ----


def _collect_alibaba(cfg: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from aliyunsdkcms.request.v20180308 import DescribeMetricListRequest
        from aliyunsdkcore.client import AcsClient

        client = AcsClient(cfg["access_key_id"], cfg["access_key_secret"], cfg["region"])
        metric_data = []
        for metric_name in cfg.get("metrics", []):
            request = DescribeMetricListRequest.DescribeMetricListRequest()
            request.set_accept_format("json")
            request.set_Namespace("acs_ecs_dashboard")
            request.set_MetricName(metric_name)
            request.set_Dimensions(f"instanceId:{cfg['instance_id']}")
            request.set_Period("300")
            request.set_StartTime(
                (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            request.set_EndTime(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            resp = json.loads(client.do_action_with_exception(request))
            datapoints = resp.get("Datapoints", [])
            if datapoints:
                latest = max(datapoints, key=lambda d: d["Timestamp"])  # type: ignore
                metric_data.append(
                    {
                        "name": metric_name,
                        "value": latest.get("Average", 0.0),
                        "unit": latest.get("Unit", ""),
                        "dimensions": {"instanceId": cfg["instance_id"]},
                    }
                )
        return {
            "provider": "alibaba",
            "timestamp": _iso_timestamp(),
            "metrics": metric_data,
            "raw": cfg,
        }
    except Exception as e:
        _logger.error("Alibaba CloudMonitor collection failed: %s", e, exc_info=True)
        raise


# ---------- 公共采集入口 ----------


def collect_cloud_provider(provider_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """根据单条配置采集对应云平台指标并返回统一结构"""
    provider = provider_cfg.get("provider", "").lower()
    if provider == "aws":
        return _collect_aws(provider_cfg)
    if provider == "azure":
        return _collect_azure(provider_cfg)
    if provider == "alibaba" or provider == "alicloud":
        return _collect_alibaba(provider_cfg)
    raise ValueError(f"Unsupported cloud provider: {provider}")


# ---------- 业务函数 ----------

_collect_history: deque[Dict[str, Any]] = deque(maxlen=50)
_collect_lock = Lock()


def collect_cloud(host_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """采集单个云平台（host_cfg 为 CLOUD_PROVIDERS 中的单条 dict）"""
    try:
        snapshot = collect_cloud_provider(host_cfg)
        # Loki & Stats 写入
        try:
            push_to_loki(snapshot)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            _logger.debug("Failed to push cloud snapshot to Loki", exc_info=True)
        try:
            collect_data = {
                "host": host_cfg.get("provider", "unknown"),
                "metric": json.dumps(snapshot),
                "count": len(snapshot.get("metrics", [])),
                "key": "cloud",
            }
            record_collect(collect_data)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            _logger.debug("Failed to record cloud collect", exc_info=True)
        # PID 防护登记（统一使用 CLOUD_* 配置）
        try:
            register_self_pid()
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            _logger.debug("register_self_pid failed for cloud", exc_info=True)
        # 记录历史
        with _collect_lock:
            _collect_history.append(snapshot)
        return snapshot
    except Exception as e:
        _logger.error("Collect cloud failed: %s", e, exc_info=True)
        return {}


def collect_all_cloud() -> List[Dict[str, Any]]:
    """遍历 CONFIG 中的 CLOUD_PROVIDERS，批量采集"""
    results: List[Dict[str, Any]] = []
    for cfg in CLOUD_PROVIDERS:
        results.append(collect_cloud(cfg))
    return results


def get_cloud_collect_history(limit: int = 20) -> List[Dict[str, Any]]:
    with _collect_lock:
        return list(_collect_history)[-limit:]