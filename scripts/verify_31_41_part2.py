import logging
"""Verify project tasks 33-41 (services layer) across 13 dimensions."""

import json
import os
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
JSON_OUT = BASE / "verify_logs" / "tasks_31_41_part2_verification.json"
JSON_OUT.parent.mkdir(exist_ok=True)

os.environ["PYTHONIOENCODING"] = "utf-8"

TASKS = [
    ("33", "agent_orchestration_service", "代理编排服务"),
    ("34", "scenario_memory_service", "情景记忆服务"),
    ("35", "knowledge_graph_service", "知识图谱服务"),
    ("36", "data_access_service", "数据访问服务"),
    ("37", "cache_service", "缓存服务"),
    ("38", "vector_retrieval_service", "向量检索服务"),
    ("39", "postgresql_shard_service", "PostgreSQL分片集群"),
    ("40", "redis_shard_service", "Redis分片集群"),
    ("41", "qdrant_shard_service", "Qdrant分片集群"),
]


def run_cmd(cmd: list[str], timeout: int = 180) -> dict:
    start = time.time()
    try:
        r = subprocess.run(
            cmd,
            cwd=BASE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        stdout = r.stdout
        stderr = r.stderr
        rc = r.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        rc = -1
    return {
        "cmd": " ".join(str(c) for c in cmd),
        "returncode": rc,
        "stdout": stdout,
        "stderr": stderr,
        "duration": round(time.time() - start, 2),
    }


def gather_file_facts(svc: str) -> dict:
    svc_path = BASE / "services" / svc
    test_path = BASE / "tests" / "services" / svc
    facts = {
        "service_path": str(svc_path),
        "test_path": str(test_path),
        "files": sorted(p.name for p in svc_path.iterdir() if p.is_file()),
        "test_files": sorted(p.name for p in test_path.iterdir() if p.is_file()),
        "has_readme": (svc_path / "README.md").exists(),
        "has_dockerfile": (svc_path / "Dockerfile").exists(),
        "has_requirements": (svc_path / "requirements.txt").exists(),
        "has_k8s": False,
        "has_prometheus": False,
        "python_files": 0,
        "pass_lines": 0,
        "notimplemented_lines": 0,
        "todo_lines": 0,
    }
    k8s_dir = svc_path / "k8s"
    if k8s_dir.exists():
        facts["has_k8s"] = bool(list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml")))
    if (svc_path / "prometheus.yml").exists() or (svc_path / "prometheus.yaml").exists():
        facts["has_prometheus"] = True

    for py in svc_path.rglob("*.py"):
        facts["python_files"] += 1
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            continue
        facts["pass_lines"] += text.count("pass")
        facts["notimplemented_lines"] += text.count("NotImplementedError")
        facts["todo_lines"] += text.count("TODO") + text.count("FIXME")
    return facts


def verify_service(task_no: str, svc: str, title: str) -> dict:
    section = {"task": task_no, "service": svc, "title": title}
    section["files"] = gather_file_facts(svc)

    section["black"] = run_cmd(["python", "-m", "black", "--check", f"services/{svc}"], timeout=120)
    section["isort"] = run_cmd(
        ["python", "-m", "isort", "--check-only", f"services/{svc}"], timeout=120
    )
    section["flake8"] = run_cmd(["python", "-m", "flake8", f"services/{svc}"], timeout=120)
    section["mypy"] = run_cmd(
        ["python", "-m", "mypy", "--ignore-missing-imports", f"services/{svc}"],
        timeout=180,
    )
    # Run pytest with service-level coverage, clear default addopts to avoid core/api pollution
    section["pytest"] = run_cmd(
        [
            "python",
            "-m",
            "pytest",
            f"tests/services/{svc}",
            "-q",
            "--override-ini=addopts=",
            f"--cov=services/{svc}",
            "--cov-report=term",
            "--timeout=60",
        ],
        timeout=240,
    )
    section["bandit"] = run_cmd(
        ["python", "-m", "bandit", "-r", f"services/{svc}", "-f", "txt"],
        timeout=120,
    )
    return section


def main():
    results = []
    for task_no, svc, title in TASKS:
        print(f"[{task_no}] Verifying {svc} ...")
        r = verify_service(task_no, svc, title)
        results.append(r)
        JSON_OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Part2 JSON written to: {JSON_OUT}")


if __name__ == "__main__":
    main()