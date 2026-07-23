"""Compile per-service verification JSONs into a final markdown report."""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "verify_logs" / "tasks_31_41_final_report.md"

JSONS = [
    BASE / "verify_logs" / "tasks_31_41_verification.json",
    BASE / "verify_logs" / "tasks_31_41_part2_verification.json",
    BASE / "verify_logs" / "tasks_37_41_verification.json",
]

# Earlier runs did not include coverage for 31/32; fill in from direct pytest --cov runs.
KNOWN_COVERAGE = {
    "31": 93.62,
    "32": 83.01,
}


def parse_pytest_summary(stdout: str) -> dict:
    out = {}
    m = re.search(
        r"(\d+)\s+passed"
        r"(?:,\s+(\d+)\s+failed)?"
        r"(?:,\s+(\d+)\s+skipped)?"
        r"(?:,\s+(\d+)\s+xfailed)?"
        r"\s+in\s+([\d.]+)s",
        stdout,
        re.IGNORECASE,
    )
    if m:
        out["passed"] = int(m.group(1))
        out["failed"] = int(m.group(2) or 0)
        out["skipped"] = int(m.group(3) or 0)
        out["xfailed"] = int(m.group(4) or 0)
        out["duration"] = m.group(5)
    else:
        out["passed"] = out["failed"] = out["skipped"] = out["xfailed"] = None
        out["duration"] = None
    # coverage total (format has multiple numeric columns before Cover)
    cm = re.search(
        r"""TOTAL \s+ \d+ \s+ \d+ \s+ \d+ \s+ \d+ \s+ (\d+\.?\d*) %""",
        stdout,
        re.VERBOSE,
    )
    out["coverage"] = int(float(cm.group(1))) if cm else None
    return out


def parse_bandit(stdout: str) -> dict:
    result = {"low": 0, "medium": 0, "high": 0}
    block = re.search(
        r"Total issues \(by severity\):\s*\n"
        r"(?:.*\n)*?"
        r"\s*Low:\s+(\d+)\s*\n"
        r"\s*Medium:\s+(\d+)\s*\n"
        r"\s*High:\s+(\d+)",
        stdout,
        re.MULTILINE,
    )
    if block:
        result = {
            "low": int(block.group(1)),
            "medium": int(block.group(2)),
            "high": int(block.group(3)),
        }
    return result


def count_mypy_errors(stdout: str) -> int:
    m = re.search(r"Found\s+(\d+)\s+error", stdout)
    if m:
        return int(m.group(1))
    return 0


def verdict(r: dict) -> str:
    black = r["black"]["returncode"] == 0
    isort = r["isort"]["returncode"] == 0
    flake8 = r["flake8"]["returncode"] == 0
    pytest = r["pytest"]["returncode"] == 0
    mypy_rc = r["mypy"]["returncode"]
    bandit = parse_bandit(r["bandit"]["stdout"])
    files = r["files"]

    if not pytest:
        return "未通过（pytest 失败）"
    if not (black and isort and flake8):
        return "未通过（代码规范检查失败）"
    issues = []
    if mypy_rc != 0:
        issues.append(f"mypy 错误 {count_mypy_errors(r['mypy']['stdout'])} 处")
    if bandit["medium"] or bandit["high"]:
        issues.append(f"bandit 中/高危 {bandit['medium'] + bandit['high']} 处")
    if bandit["low"]:
        issues.append(f"bandit 低危 {bandit['low']} 处")
    if issues:
        return "部分通过（" + "；".join(issues) + "）"
    if files["notimplemented_lines"] or files["todo_lines"]:
        return "部分通过（含 TODO / NotImplementedError）"
    return "通过"


def main():
    results_by_task = {}
    for path in JSONS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for r in data:
            # Prefer later data; it should contain coverage and more accurate tooling
            results_by_task[int(r["task"])] = r

    results = [results_by_task[k] for k in sorted(results_by_task)]

    lines = ["# 任务31-41 13维度核验汇总报告\n"]
    summary = []
    for r in results:
        task = r["task"]
        svc = r["service"]
        title = r["title"]
        files = r["files"]
        pt = parse_pytest_summary(r["pytest"]["stdout"])
        if pt.get("coverage") is None and task in KNOWN_COVERAGE:
            pt["coverage"] = KNOWN_COVERAGE[task]
        bnd = parse_bandit(r["bandit"]["stdout"])
        mypy_errs = count_mypy_errors(r["mypy"]["stdout"])
        v = verdict(r)
        summary.append(
            (
                task,
                title,
                svc,
                v,
                pt.get("passed"),
                pt.get("coverage"),
                bnd["low"],
                bnd["medium"],
                bnd["high"],
                mypy_errs,
            )
        )

        lines.append(f"\n## 任务{task}: {title} (`{svc}`)\n")
        lines.append("### 13 维度核验结果\n")
        lines.append(
            f"- **真实性**: 服务目录存在，"
            f"Python 文件数 {files['python_files']}，"
            f"未实现桩 {files['notimplemented_lines']}，"
            f"TODO {files['todo_lines']}\n"
        )
        lines.append(
            f"- **交付物**: README={files['has_readme']}, "
            f"Dockerfile={files['has_dockerfile']}, "
            f"k8s={files['has_k8s']}, "
            f"Prometheus={files['has_prometheus']}\n"
        )
        lines.append(f"- **black**: {'通过' if r['black']['returncode'] == 0 else '失败'}\n")
        lines.append(f"- **isort**: {'通过' if r['isort']['returncode'] == 0 else '失败'}\n")
        lines.append(f"- **flake8**: {'通过' if r['flake8']['returncode'] == 0 else '失败'}\n")
        lines.append(
            f"- **mypy**: "
            f"{'通过' if r['mypy']['returncode'] == 0 else f'失败（{mypy_errs} 处错误）'}\n"
        )
        lines.append(
            f"- **pytest**: 通过 {pt['passed'] or '?'}, "
            f"失败 {pt['failed'] or 0}, 跳过 {pt['skipped'] or 0}, "
            f"xfailed {pt['xfailed'] or 0}, 耗时 {pt['duration'] or '?'}s, "
            f"覆盖率 {pt['coverage'] or '未统计'}%\n"
        )
        lines.append(f"- **bandit**: 低危 {bnd['low']}, 中危 {bnd['medium']}, 高危 {bnd['high']}\n")
        lines.append(f"- **综合判定**: **{v}**\n")

    lines.append("\n## 总体判定表\n")
    lines.append("| 任务 | 服务 | pytest | 覆盖率 | mypy错误 | bandit低/中/高 | 判定 |\n")
    lines.append("|------|------|--------|--------|----------|----------------|------|\n")
    for s in summary:
        task, title, svc, v, passed, cov, low, med, high, mypy_e = s
        lines.append(
            f"| {task} | {svc} | {passed} | "
            f"{cov if cov is not None else '-'} | {mypy_e} | "
            f"{low}/{med}/{high} | {v} |\n"
        )

    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Report written to: {OUT}")
    print("\n判定汇总：")
    for s in summary:
        print(
            f"  任务{s[0]} ({s[2]}): {s[3]} "
            f"(pytest={s[4]}, cov={s[5]}, "
            f"bandit={s[6]}/{s[7]}/{s[8]}, mypy={s[9]})"
        )


if __name__ == "__main__":
    main()
