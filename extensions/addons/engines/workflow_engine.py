# -*- coding: utf-8 -*-
"""Workflow engine for Group 6 workflow & operations addons."""

from __future__ import annotations

import importlib
import os
import runpy
import subprocess
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    import httpx as requests


class WorkflowEngine:
    """Execute workflow definitions sequentially with dry-run safety."""

    def __init__(self, dry_run: Optional[bool] = None) -> None:
        if dry_run is None:
            dry_run = os.environ.get("INFRA_EXECUTE_ENABLED") != "true"
        self.dry_run = bool(dry_run)

    @property
    def _real_execution(self) -> bool:
        return (not self.dry_run) and (os.environ.get("INFRA_EXECUTE_ENABLED") == "true")

    def _execute_http(self, step: Dict[str, Any]) -> Dict[str, Any]:
        if not self._real_execution:
            return {"dry_run": True, "status_code": 200, "text": "simulated"}

        method = step.get("method", "GET")
        url = step["url"]
        kwargs: Dict[str, Any] = {}

        headers = step.get("headers")
        if headers is not None:
            kwargs["headers"] = headers

        payload = step.get("body") if "body" in step else step.get("data")
        if payload is not None:
            if isinstance(payload, dict):
                kwargs["json"] = payload
            else:
                kwargs["data"] = payload

        params = step.get("params")
        if params is not None:
            kwargs["params"] = params

        timeout = step.get("timeout", 30)
        resp = requests.request(method, url, timeout=timeout, **kwargs)
        return {
            "status_code": resp.status_code,
            "text": resp.text,
            "headers": dict(resp.headers),
        }

    def _execute_cli(self, step: Dict[str, Any]) -> Dict[str, Any]:
        if not self._real_execution:
            return {"dry_run": True, "returncode": 0, "stdout": "simulated", "stderr": ""}

        command = step["command"]
        shell = step.get("shell", False)
        if isinstance(command, str) and not shell:
            command = command.split()
        cp = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=shell,
        )
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
        }

    def _execute_python(self, step: Dict[str, Any], context: Dict[str, Any]) -> Any:
        if not self._real_execution:
            return {"dry_run": True, "mode": step.get("mode", "module")}

        mode = step.get("mode", "module")
        if mode == "module":
            mod = importlib.import_module(step["module"])
            func_name = step.get("function", "main")
            if hasattr(mod, func_name):
                func = getattr(mod, func_name)
                args = step.get("args", {})
                result = func(**args)
            else:
                result = mod
        elif mode == "script":
            namespace = runpy.run_path(step["script"], run_name="__workflow__")
            result = namespace.get(step.get("return"), None)
        elif mode == "code":
            local_vars = {"context": context, "inputs": context}
            exec(step["code"], {"__builtins__": {}}, local_vars)
            result = local_vars.get(step.get("output"), local_vars)
        else:
            result = None
        return result

    def _execute_decision(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        condition = step.get("condition", "False")
        try:
            value = bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            value = False
        branch = step.get("true" if value else "false", None)
        return {"decision": value, "branch": branch}

    def _execute_memory(self, step: Dict[str, Any]) -> Any:
        return self.get_scenario_memory(step.get("query", ""))

    def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Any:
        step_type = step.get("type", "python")
        if step_type == "http":
            return self._execute_http(step)
        if step_type == "cli":
            return self._execute_cli(step)
        if step_type == "python":
            return self._execute_python(step, context)
        if step_type == "decision":
            return self._execute_decision(step, context)
        if step_type == "memory":
            return self._execute_memory(step)
        return {"error": f"Unknown step type: {step_type}"}

    def run_workflow(
        self,
        workflow_def: Any,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a workflow definition sequentially and return per-step results."""
        inputs = inputs or {}
        steps = workflow_def if isinstance(workflow_def, list) else workflow_def.get("steps", [])
        context = inputs.copy()
        results: List[Dict[str, Any]] = []

        for step in steps:
            try:
                result = self._execute_step(step, context)
            except Exception as exc:
                result = {"error": str(exc)}
            results.append({"step": step.get("name", step.get("type")), "result": result})
            output_key = step.get("output")
            if output_key:
                context[output_key] = result

        return {"success": True, "results": results, "context": context}

    def get_scenario_memory(self, query: str) -> Dict[str, Any]:
        """Call the RAG/memory engine, falling back to a synthetic placeholder."""
        try:
            from extensions.addons.engines.memory_engine import retrieve_scenario
            return retrieve_scenario(query)
        except Exception:  # pragma: no cover - Group 7 placeholder
            return {
                "query": query,
                "matches": [
                    {
                        "id": "synthetic",
                        "text": f"Scenario memory for {query}",
                        "score": 0.95,
                    }
                ],
            }

    def capacity_analysis(
        self,
        metrics: Dict[str, Any],
        forecasts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Combine metrics and forecasts into actionable capacity recommendations."""
        recommendations: List[Dict[str, Any]] = []
        for key, value in metrics.items():
            forecast = forecasts.get(key)
            if isinstance(value, (int, float)) and isinstance(forecast, (int, float)):
                if forecast > value * 1.2:
                    action = "scale_up"
                elif forecast < value * 0.8:
                    action = "scale_down"
                else:
                    action = "monitor"
                recommendations.append(
                    {"resource": key, "current": value, "forecast": forecast, "action": action}
                )
        return {
            "success": True,
            "metrics": metrics,
            "forecasts": forecasts,
            "recommendations": recommendations,
        }


class RunbookRunner:
    """Thin wrapper around WorkflowEngine for incident runbooks."""

    def __init__(self, engine: Optional[WorkflowEngine] = None, dry_run: Optional[bool] = None) -> None:
        self.engine = engine or WorkflowEngine(dry_run=dry_run)

    def run_runbook(
        self,
        runbook: Any,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Alias for running an incident runbook through the workflow engine."""
        results = self.engine.run_workflow(runbook, inputs)
        return {"success": True, "runbook": runbook, "results": results}
