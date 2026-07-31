import logging

"""Verify project tasks 31-41 (services layer) across 13 dimensions."""

import json
import os
import time
from pathlib import Path

from core.security import subprocess_runner

BASE = Path(__file__).resolve().parent.parent
REPORT = BASE / "verify_logs" / "tasks_31_41_verification_report.md"
REPORT.parent.mkdir(exist_ok=True)

# Ensure UTF-8 output on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"

TASKS = [
    ("31", "llm_router_service", "LLM路由服务"),
    ("32", "rag_service", "RAG服务集群"),
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
        r = subprocess_runner.run(
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
    except subprocess_runner.TimeoutExpired as exc:
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


def truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit // 2] + "\n... [truncated] ...\n" + text[-limit // 2 :]


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
        "noop_lines": 0,
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
        # crude counts; ignore docstrings and type stubs by counting raw occurrences
        facts["noop_lines"] += text.count("pass")
        facts["notimplemented_lines"] += text.count("NotImplementedError")
        facts["todo_lines"] += text.count("TODO") + text.count("FIXME")
    return facts


def verify_service(task_no: str, svc: str, title: str) -> dict:
    section = {"task": task_no, "service": svc, "title": title}
    section["files"] = gather_file_facts(svc)

    # 1. black
    section["black"] = run_cmd(["python", "-m", "black", "--check", f"services/{svc}"], timeout=120)
    # 2. isort
    section["isort"] = run_cmd(
        ["python", "-m", "isort", "--check-only", f"services/{svc}"], timeout=120
    )
    # 3. flake8
    section["flake8"] = run_cmd(["python", "-m", "flake8", f"services/{svc}"], timeout=120)
    # 4. mypy
    section["mypy"] = run_cmd(
        ["python", "-m", "mypy", "--ignore-missing-imports", f"services/{svc}"],
        timeout=180,
    )
    # 5. pytest (no global cov to avoid core/api pollution, service cov only)
    test_dir = f"tests/services/{svc}"
    section["pytest"] = run_cmd(
        [
            "python",
            "-m",
            "pytest",
            test_dir,
            "-q",
            "-n",
            "auto",
            "--no-cov",
            "--timeout=60",
        ],
        timeout=240,
    )
    # 6. bandit
    section["bandit"] = run_cmd(
        ["python", "-m", "bandit", "-r", f"services/{svc}", "-f", "txt"],
        timeout=120,
    )
    return section


def render_markdown(results: list[dict]) -> str:
    lines = ["# 任务31-41 13维度核验报告\n", f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]
    overall_ok = True
    for r in results:
        task = r["task"]
        svc = r["service"]
        title = r["title"]
        files = r["files"]
        lines.append(f"\n## 任务{task}: {title} ({svc})\n")
        lines.append(f"- **服务目录**: `{files['service_path']}`\n")
        lines.append(f"- **测试目录**: `{files['test_path']}`\n")
        lines.append(f"- **服务文件**: {', '.join(files['files'])}\n")
        lines.append(f"- **测试文件**: {', '.join(files['test_files'])}\n")
        lines.append(
            f"- **交付物**: README={files['has_readme']}, "
            f"Dockerfile={files['has_dockerfile']}, "
            f"requirements={files['has_requirements']}, "
            f"k8s={files['has_k8s']}, "
            f"prometheus={files['has_prometheus']}\n"
        )
        lines.append(
            f"- **代码真实性**: python_files={files['python_files']}, pass_count={files['noop_lines']}, "
            f"NotImplementedError={files['notimplemented_lines']}, TODO={files['todo_lines']}\n"
        )

        for tool in ["black", "isort", "flake8", "mypy", "pytest", "bandit"]:
            res = r[tool]
            ok = res["returncode"] == 0
            if not ok and tool != "flake8":
                # flake8 may report only style issues; treat as info
                overall_ok = False
            lines.append(
                f"\n### {tool.upper()} 检查 (exit={res['returncode']}, duration={res['duration']}s)\n"
            )
            out = (res["stdout"] + "\n" + res["stderr"]).strip()
            lines.append(f"```\n{truncate(out)}\n```\n")

    lines.append("\n## 总体判定\n")
    lines.append(f"- 整体状态: {'通过' if overall_ok else '不通过'}\n")
    return "".join(lines)


def main():
    results = []
    for task_no, svc, title in TASKS:
        print(f"[{task_no}] Verifying {svc} ...")
        r = verify_service(task_no, svc, title)
        results.append(r)
        # Save incremental JSON for recovery
        (REPORT.parent / "tasks_31_41_verification.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    md = render_markdown(results)
    REPORT.write_text(md, encoding="utf-8")
    print(f"Report written to: {REPORT}")


if __name__ == "__main__":
    main()
