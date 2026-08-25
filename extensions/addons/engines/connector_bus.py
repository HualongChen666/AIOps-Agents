# -*- coding: utf-8 -*-
"""Generic connector bus for integration and messaging addons.

Supports Kafka, RabbitMQ, SQS and HTTP webhooks/GitHub requests.  Real I/O is
only performed when ``INFRA_EXECUTE_ENABLED`` is set to ``"true"``; otherwise
every method returns a dry-run placeholder.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _should_execute(dry_run: bool) -> bool:
    return (not dry_run) and os.environ.get("INFRA_EXECUTE_ENABLED") == "true"


def _http_request(method: str, url: str, **kwargs: Any) -> Any:
    """Make an HTTP request using ``requests`` if available, otherwise ``httpx``."""
    # Use environment variable to control SSL verification (default: True for security)
    ssl_verify = os.environ.get("CONNECTOR_BUS_SSL_VERIFY", "true").lower() == "true"

    if requests is not None:
        kwargs.setdefault("verify", ssl_verify)
        if not ssl_verify:
            import logging
            logging.warning("SSL verification is disabled in connector_bus - this is a security risk!")
        return requests.request(method, url, **kwargs)
    if httpx is not None:
        kwargs.setdefault("verify", ssl_verify)
        if not ssl_verify:
            import logging
            logging.warning("SSL verification is disabled in connector_bus - this is a security risk!")
        return httpx.request(method, url, **kwargs)
    raise RuntimeError("No HTTP client available (requests or httpx)")  # pragma: no cover


def _sqs_url(queue: str) -> bool:
    """Heuristic for identifying an SQS queue URL."""
    return queue.startswith("https://sqs.") or queue.startswith("arn:aws:sqs")


def _serialize_message(message: Any) -> str:
    if isinstance(message, str):
        return message
    return json.dumps(message)


class ConnectorBus:
    """Thin integration engine backed by CLI tools and HTTP clients."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def produce(self, topic: str, message: Any, bus: str = "kafka") -> Dict[str, Any]:
        """Produce a message to ``topic`` on the requested ``bus``."""
        if not _should_execute(self.dry_run):
            return {
                "success": True,
                "status": "dry_run",
                "dry_run": True,
                "action": "produce",
                "topic": topic,
                "bus": bus,
                "message": message,
            }

        payload = _serialize_message(message)
        broker = os.environ.get("KAFKA_BROKER", "localhost:9092")

        if bus == "kafka":
            cmd = [
                "kafka-console-producer.sh",
                "--broker-list",
                broker,
                "--topic",
                topic,
            ]
            result = subprocess.run(cmd, input=payload, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "produced" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        if bus == "rabbitmq":
            cmd = [
                "rabbitmqadmin",
                "publish",
                "exchange=amq.default",
                f"routing_key={topic}",
                f"payload={payload}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "published" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        if bus == "sqs":
            cmd = [
                "aws",
                "sqs",
                "send-message",
                "--queue-url",
                topic,
                "--message-body",
                payload,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "sent" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        if bus == "http":
            return self.webhook_send(topic, message, "POST")

        return {"success": False, "status": "unsupported_bus", "bus": bus}

    def consume(self, topic: str, bus: str = "kafka", limit: int = 1) -> Dict[str, Any]:
        """Consume up to ``limit`` messages from ``topic`` on the requested ``bus``."""
        if not _should_execute(self.dry_run):
            return {
                "success": True,
                "status": "dry_run",
                "dry_run": True,
                "action": "consume",
                "topic": topic,
                "bus": bus,
                "limit": limit,
            }

        broker = os.environ.get("KAFKA_BROKER", "localhost:9092")

        if bus == "kafka":
            cmd = [
                "kafka-console-consumer.sh",
                "--bootstrap-server",
                broker,
                "--topic",
                topic,
                "--from-beginning",
                "--max-messages",
                str(limit),
                "--timeout-ms",
                "5000",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "consumed" if result.returncode == 0 else "error",
                "messages": result.stdout.splitlines() if result.stdout else [],
                "returncode": result.returncode,
                "stderr": result.stderr,
            }

        if bus == "rabbitmq":
            cmd = ["rabbitmqadmin", "get", f"queue={topic}", f"count={limit}"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "consumed" if result.returncode == 0 else "error",
                "messages": result.stdout.splitlines() if result.stdout else [],
                "returncode": result.returncode,
                "stderr": result.stderr,
            }

        if bus == "sqs":
            cmd = [
                "aws",
                "sqs",
                "receive-message",
                "--queue-url",
                topic,
                "--max-number-of-messages",
                str(limit),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "received" if result.returncode == 0 else "error",
                "messages": result.stdout.splitlines() if result.stdout else [],
                "returncode": result.returncode,
                "stderr": result.stderr,
            }

        return {"success": False, "status": "unsupported_bus", "bus": bus}

    def publish_queue(self, queue: str, message: Any) -> Dict[str, Any]:
        """Publish ``message`` to a RabbitMQ or SQS queue."""
        if not _should_execute(self.dry_run):
            return {
                "success": True,
                "status": "dry_run",
                "dry_run": True,
                "action": "publish_queue",
                "queue": queue,
                "message": message,
            }

        payload = _serialize_message(message)

        if _sqs_url(queue):
            cmd = [
                "aws",
                "sqs",
                "send-message",
                "--queue-url",
                queue,
                "--message-body",
                payload,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "sent" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        cmd = [
            "rabbitmqadmin",
            "publish",
            "exchange=amq.default",
            f"routing_key={queue}",
            f"payload={payload}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
        return {
            "success": result.returncode == 0,
            "status": "published" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def subscribe_queue(self, queue: str, limit: int = 1) -> Dict[str, Any]:
        """Receive up to ``limit`` messages from a RabbitMQ or SQS queue."""
        if not _should_execute(self.dry_run):
            return {
                "success": True,
                "status": "dry_run",
                "dry_run": True,
                "action": "subscribe_queue",
                "queue": queue,
                "limit": limit,
            }

        if _sqs_url(queue):
            cmd = [
                "aws",
                "sqs",
                "receive-message",
                "--queue-url",
                queue,
                "--max-number-of-messages",
                str(limit),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
            return {
                "success": result.returncode == 0,
                "status": "received" if result.returncode == 0 else "error",
                "messages": result.stdout.splitlines() if result.stdout else [],
                "returncode": result.returncode,
                "stderr": result.stderr,
            }

        cmd = ["rabbitmqadmin", "get", f"queue={queue}", f"count={limit}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=False)
        return {
            "success": result.returncode == 0,
            "status": "consumed" if result.returncode == 0 else "error",
            "messages": result.stdout.splitlines() if result.stdout else [],
            "returncode": result.returncode,
            "stderr": result.stderr,
        }

    def webhook_send(self, url: str, payload: Any, method: str = "POST") -> Dict[str, Any]:
        """Send an HTTP webhook request."""
        if not _should_execute(self.dry_run):
            return {
                "success": True,
                "status": "dry_run",
                "dry_run": True,
                "action": "webhook_send",
                "url": url,
                "method": method,
                "payload": payload,
            }

        try:
            response = _http_request(
                method.upper(),
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            try:
                data = response.json()
            except Exception:
                data = response.text
            return {
                "success": 200 <= response.status_code < 300,
                "status": response.status_code,
                "result": data,
            }
        except Exception as exc:  # pragma: no cover
            return {"success": False, "status": "error", "result": str(exc)}

    def github_request(self, owner: str, repo: str, endpoint: str) -> Dict[str, Any]:
        """Perform a GET request against the GitHub API."""
        if not _should_execute(self.dry_run):
            return {
                "success": True,
                "status": "dry_run",
                "dry_run": True,
                "action": "github_request",
                "owner": owner,
                "repo": repo,
                "endpoint": endpoint,
            }

        url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint.lstrip('/')}"
        try:
            response = _http_request(
                "GET",
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "connector-bus/1.0",
                },
                timeout=10,
            )
            try:
                data = response.json()
            except Exception:
                data = response.text
            return {
                "success": 200 <= response.status_code < 300,
                "status": response.status_code,
                "result": data,
            }
        except Exception as exc:  # pragma: no cover
            return {"success": False, "status": "error", "result": str(exc)}
