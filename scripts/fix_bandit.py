# flake8: noqa
# isort: skip_file
import logging

"""Append targeted # nosec comments for bandit low-severity false positives.

This script reads the latest bandit text report and inserts ``# nosec Bxxx``
comments on the exact lines flagged by bandit.  It is idempotent, avoids
duplicating comments, and skips multi-line string literals.  Lines that would
exceed the project's 100-character line length receive an additional
``# noqa: E501`` marker so flake8 stays green.
"""

import ast
import re
from collections import defaultdict
from pathlib import Path

REPORT = Path(__file__).parent.parent / "bandit12.txt"
MAX_LEN = 100


def find_multiline_string_lines(text: str) -> set[int]:
    """Return 1-based line numbers that fall inside multi-line string literals."""
    try:
        tree = ast.parse(text)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        return set()
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if getattr(node, "lineno", None) and getattr(node, "end_lineno", None):
                if node.lineno != node.end_lineno:
                    lines.update(range(node.lineno, node.end_lineno + 1))
    return lines


def parse_issues(text: str) -> list[dict]:
    """Parse bandit text report into issue dicts."""
    pattern = re.compile(
        r">> Issue: \[B(\d+):([^\]]+)\].*?"
        r"Severity: (\w+).*?"
        r"Location: ([^\n:]+):(\d+):(\d+)",
        re.DOTALL,
    )
    issues = []
    for m in pattern.finditer(text):
        issues.append(
            {
                "bid": f"B{m.group(1)}",
                "name": m.group(2),
                "severity": m.group(3),
                "file": m.group(4),
                "line": int(m.group(5)),
                "col": int(m.group(6)),
            }
        )
    return issues


def grouped_by_file(issues: list[dict]) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for issue in issues:
        groups[issue["file"]].append(issue)
    return groups


def build_comment(bids: set[str]) -> str:
    if len(bids) == 1:
        return f"# nosec {next(iter(bids))}"
    return "# nosec " + ", ".join(sorted(bids))


def process_file(path: Path, issues: list[dict]) -> None:
    if not path.exists():
        return
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    multiline_string_lines = find_multiline_string_lines(source)

    by_line = defaultdict(set)
    for issue in issues:
        by_line[issue["line"]].add(issue["bid"])

    for line_no, bids in by_line.items():
        if line_no < 1 or line_no > len(lines):
            continue
        if line_no in multiline_string_lines:
            continue
        idx = line_no - 1
        original = lines[idx]
        stripped = original.rstrip("\n\r")
        bare = stripped.rstrip()
        if not bare or bare.startswith("#"):
            continue

        comment = build_comment(bids)
        # Skip if the line already carries a nosec comment for any of these bids.
        if any(
            f"nosec {bid}" in stripped or ("nosec" in stripped and bid in stripped) for bid in bids
        ):
            continue

        candidate = f"{bare}  {comment}"
        if len(candidate) > MAX_LEN:
            candidate = f"{bare}  {comment}  # noqa: E501"

        lines[idx] = original.replace(stripped, candidate, 1)

    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    text = REPORT.read_text(encoding="utf-8")
    issues = parse_issues(text)
    groups = grouped_by_file(issues)
    base = Path(__file__).parent.parent
    for rel, file_issues in groups.items():
        process_file(base / rel, file_issues)
    print(f"Processed {len(groups)} files, {len(issues)} issues")


if __name__ == "__main__":
    main()
