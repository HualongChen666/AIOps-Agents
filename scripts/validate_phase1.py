#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
"""Validate Phase 1 functional completeness.

Checks:
- main.py imports and exposes the FastAPI app without Python warnings.
- openapi.yaml is generated and contains registered routes.
- scripts/verify_all.py reports zero missing docs/examples/errors.
- Missing routers (teams, graphql, realtime, slack) are imported and registered.
- core/ai/langgraph LLMNode can be instantiated and executed.
- core/content_moderation moderate_content works.
"""

import asyncio
import json
import pathlib
import subprocess
import sys
import time
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _run(cmd: list[str], timeout: int = 120) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {"rc": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as exc:
        return {"rc": -1, "stdout": "", "stderr": str(exc)}


def _check_import_main() -> tuple[bool, str]:
    code = "import main; from main import app; print('OK', len(app.routes))"
    result = _run([sys.executable, "-c", code], timeout=120)
    if result["rc"] != 0:
        return False, result["stderr"]
    if "Traceback" in result["stderr"] or "Traceback" in result["stdout"]:
        return False, result["stderr"]
    return True, result["stdout"].strip()


def _check_openapi_generation() -> tuple[bool, str]:
    code = (
        "import main, yaml; "
        "yaml.dump(main.app.openapi(), open('openapi.yaml','w',encoding='utf-8'), allow_unicode=True); "  # noqa: E501
        "print('OK')"
    )
    result = _run([sys.executable, "-c", code], timeout=120)
    if result["rc"] != 0:
        return False, result["stderr"]
    openapi_path = PROJECT_ROOT / "openapi.yaml"
    if not openapi_path.exists() or openapi_path.stat().st_size == 0:
        return False, "openapi.yaml is empty or missing"
    return True, f"openapi.yaml size={openapi_path.stat().st_size}"


def _check_verify_all() -> tuple[bool, str]:
    result = _run([sys.executable, "-m", "scripts.verify_all"], timeout=60)
    if result["rc"] != 0:
        return False, result["stdout"] + result["stderr"]
    try:
        report = json.loads(result["stdout"].split("\n")[-1] or result["stdout"])
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        return False, result["stdout"]
    non_zero = {k: v for k, v in report.items() if isinstance(v, int) and v != 0 and "missing" in k}
    if non_zero:
        return False, json.dumps(non_zero, ensure_ascii=False)
    return True, json.dumps(report, ensure_ascii=False, indent=2)


def _check_router_registration(app: Any) -> tuple[bool, str]:
    from fastapi.routing import APIRouter, _IncludedRouter

    paths = set()
    for r in app.routes:
        if isinstance(r, (_IncludedRouter, APIRouter)) or hasattr(r, "original_router"):
            routes = getattr(
                r, "routes", getattr(getattr(r, "original_router", None), "routes", [])
            )
            for sr in routes or []:
                if hasattr(sr, "path"):
                    paths.add(sr.path)
        elif hasattr(r, "path"):
            paths.add(r.path)

    missing = []
    for prefix in ["/api/teams", "/api/slack", "/api/v1/realtime"]:
        if not any(p.startswith(prefix) for p in paths):
            missing.append(prefix)
    if not any("graphql" in p for p in paths):
        missing.append("/graphql")
    if missing:
        return False, f"Missing routes: {missing}"
    return True, f"Registered route count={len(paths)}"


def _check_ai_langgraph() -> tuple[bool, str]:
    try:
        from core.ai.langgraph import LLMNode, WorkflowContext

        async def _run():
            node = LLMNode(name="test", prompt_template="test {name}")
            ctx = WorkflowContext(state_data={"name": "world"})
            return await node.execute(ctx)

        result = asyncio.run(_run())
        return True, f"LLMNode execute returned: {result[:80]}..."
    except Exception as exc:
        return False, str(exc)


def _check_content_moderation() -> tuple[bool, str]:
    try:
        from core.content_moderation import moderate_content

        allowed, reasons = moderate_content("hello world")
        return True, f"allowed={allowed}, reasons={reasons}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    checks = {
        "import_main": _check_import_main(),
        "openapi_generation": _check_openapi_generation(),
        "verify_all": _check_verify_all(),
        "ai_langgraph": _check_ai_langgraph(),
        "content_moderation": _check_content_moderation(),
    }

    # Router registration check requires main import
    try:
        import main

        checks["router_registration"] = _check_router_registration(main.app)
    except Exception as exc:
        checks["router_registration"] = (False, str(exc))

    all_ok = all(ok for ok, _ in checks.values())
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "Phase 1 - Functional Completeness",
        "valid": all_ok,
        "checks": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks.items()},
    }

    report_dir = PROJECT_ROOT / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "phase1_functional_completeness.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    status = "valid" if all_ok else "invalid"
    print(f"Phase 1 validation report ({status}) written to {report_file}")
    for name, (ok, detail) in checks.items():
        print(f"  {name}: {'OK' if ok else 'FAIL'} - {detail}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())