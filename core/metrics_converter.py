# -*- coding: utf-8 -*-
"""
Metrics Data Converter
Converts between SQLite metrics format and VictoriaMetrics Prometheus format
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


class MetricsConverter:
    """
    Converts metrics between different storage formats
    """

    @staticmethod
    def sqlite_to_prometheus(
        metric_name: str, value: float, labels: Dict[str, str], timestamp: Optional[int] = None
    ) -> str:
        """
        Convert SQLite metric to Prometheus exposition format

        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Metric labels
            timestamp: Optional timestamp (Unix epoch in seconds)

        Returns:
            Prometheus format string
        """
        # Sanitize metric name (replace invalid characters)
        safe_name = MetricsConverter.sanitize_metric_name(metric_name)

        # Format labels
        label_str = MetricsConverter.format_labels(labels)

        # Format timestamp (milliseconds for Prometheus)
        if timestamp:
            timestamp_ms = int(timestamp * 1000)
            return f"{safe_name}{label_str} {value} {timestamp_ms}\n"
        else:
            return f"{safe_name}{label_str} {value}\n"

    @staticmethod
    def batch_sqlite_to_prometheus(metrics: List[Dict[str, Any]]) -> str:
        """
        Convert batch of SQLite metrics to Prometheus exposition format

        Args:
            metrics: List of metric dictionaries

        Returns:
            Prometheus format string for all metrics
        """
        lines = []
        for metric in metrics:
            line = MetricsConverter.sqlite_to_prometheus(
                metric["name"], metric["value"], metric.get("labels", {}), metric.get("timestamp")
            )
            lines.append(line)
        return "".join(lines)

    @staticmethod
    def sanitize_metric_name(name: str) -> str:
        """
        Sanitize metric name for Prometheus compatibility

        Args:
            name: Original metric name

        Returns:
            Sanitized metric name
        """
        # Prometheus metric names must match: [a-zA-Z_:][a-zA-Z0-9_:]*
        # Replace invalid characters with underscore using regex for better performance
        sanitized = re.sub(r"[^a-zA-Z0-9_:]", "_", name)

        # Ensure first character is valid (letter or underscore)
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == "_"):
            sanitized = "_" + sanitized

        return sanitized

    @staticmethod
    def format_labels(labels: Dict[str, str]) -> str:
        """
        Format labels for Prometheus

        Args:
            labels: Dictionary of label key-value pairs

        Returns:
            Formatted label string
        """
        if not labels:
            return ""

        label_pairs = []
        for key, value in labels.items():
            # Sanitize label name
            safe_key = MetricsConverter.sanitize_label_name(key)
            # Escape label value
            safe_value = MetricsConverter.escape_label_value(str(value))
            label_pairs.append(f'{safe_key}="{safe_value}"')

        return "{" + ",".join(label_pairs) + "}"

    @staticmethod
    def sanitize_label_name(name: str) -> str:
        """
        Sanitize label name for Prometheus compatibility

        Args:
            name: Original label name

        Returns:
            Sanitized label name
        """
        # Prometheus label names must match: [a-zA-Z_][a-zA-Z0-9_]*
        sanitized = ""
        for i, char in enumerate(name):
            if i == 0:
                if char.isalpha() or char == "_":
                    sanitized += char
                else:
                    sanitized += "_"
            else:
                if char.isalnum() or char == "_":
                    sanitized += char
                else:
                    sanitized += "_"

        return sanitized

    @staticmethod
    def escape_label_value(value: str) -> str:
        """
        Escape label value for Prometheus

        Args:
            value: Original label value

        Returns:
            Escaped label value
        """
        # Escape backslashes, double quotes, and newlines
        value = value.replace("\\", "\\\\")
        value = value.replace('"', '\\"')
        value = value.replace("\n", "\\n")
        return value

    @staticmethod
    def system_snapshot_to_prometheus(snapshot: Dict[str, Any]) -> str:
        """
        Convert system snapshot to Prometheus format

        Args:
            snapshot: System snapshot dictionary from collect_all()

        Returns:
            Prometheus format string
        """
        lines = []
        timestamp = int(datetime.now().timestamp())

        # CPU metrics
        cpu = snapshot.get("cpu", {})
        if cpu:
            cpu_usage = cpu.get("usage_percent", 0)
            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_cpu_usage_percent", cpu_usage, {"host": "localhost"}, timestamp
                )
            )

            per_core = cpu.get("per_core", [])
            for i, core_usage in enumerate(per_core):
                lines.append(
                    MetricsConverter.sqlite_to_prometheus(
                        "aiops_cpu_core_usage_percent",
                        core_usage,
                        {"host": "localhost", "core": str(i)},
                        timestamp,
                    )
                )

        # Memory metrics
        memory = snapshot.get("memory", {})
        if memory:
            mem_usage = memory.get("usage_percent", 0)
            mem_total = memory.get("total_gb", 0)
            mem_used = memory.get("used_gb", 0)

            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_memory_usage_percent", mem_usage, {"host": "localhost"}, timestamp
                )
            )
            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_memory_total_gb", mem_total, {"host": "localhost"}, timestamp
                )
            )
            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_memory_used_gb", mem_used, {"host": "localhost"}, timestamp
                )
            )

        # Disk metrics
        disk = snapshot.get("disk", {})
        if disk:
            disk_usage = disk.get("usage_percent", 0)
            disk_total = disk.get("total_gb", 0)
            disk_used = disk.get("used_gb", 0)

            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_disk_usage_percent", disk_usage, {"host": "localhost"}, timestamp
                )
            )
            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_disk_total_gb", disk_total, {"host": "localhost"}, timestamp
                )
            )
            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_disk_used_gb", disk_used, {"host": "localhost"}, timestamp
                )
            )

        # Network metrics
        network = snapshot.get("network", {})
        if network:
            rx_bytes = network.get("rx_bytes", 0)
            tx_bytes = network.get("tx_bytes", 0)

            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_network_rx_bytes", rx_bytes, {"host": "localhost"}, timestamp
                )
            )
            lines.append(
                MetricsConverter.sqlite_to_prometheus(
                    "aiops_network_tx_bytes", tx_bytes, {"host": "localhost"}, timestamp
                )
            )

        return "".join(lines)

    @staticmethod
    def prometheus_to_sqlite(prometheus_line: str) -> Optional[Dict[str, Any]]:
        """
        Convert Prometheus format line to SQLite metric

        Args:
            prometheus_line: Prometheus format line

        Returns:
            Metric dictionary
        """
        # Parse Prometheus line: metric_name{labels} value timestamp
        try:
            # Split into metric and value
            parts = prometheus_line.split()
            if len(parts) < 2:
                return None

            metric_part = parts[0]
            value = float(parts[1])
            timestamp = int(parts[2]) / 1000 if len(parts) > 2 else None

            # Extract metric name and labels
            if "{" in metric_part:
                name_part, label_part = metric_part.split("{", 1)
                label_part = label_part.rstrip("}")

                # Parse labels
                labels = {}
                for label_pair in label_part.split(","):
                    if "=" in label_pair:
                        key, val = label_pair.split("=", 1)
                        labels[key.strip()] = val.strip('"')

                return {"name": name_part, "value": value, "labels": labels, "timestamp": timestamp}
            else:
                return {"name": metric_part, "value": value, "labels": {}, "timestamp": timestamp}

        except Exception as e:
            logger.error(f"Failed to parse Prometheus line: {e}")
            return None
