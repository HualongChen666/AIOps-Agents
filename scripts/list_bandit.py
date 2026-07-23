# flake8: noqa
# isort: skip_file
"""List bandit issues by type from the latest report."""
import re
from pathlib import Path


def main() -> None:
    text = (Path(__file__).parent.parent / "bandit9.txt").read_text(encoding="utf-8")
    issue_pat = re.compile(r">> Issue: \[(B\d+):([^\]]+)\].*?Severity: (\w+)", re.DOTALL)
    loc_pat = re.compile(r"Location: ([^\n:]+):(\d+):(\d+)")
    lines = []
    for issue_m in issue_pat.finditer(text):
        bid, name, sev = issue_m.groups()
        # find the first Location after this issue header
        tail = text[issue_m.end():]
        loc_m = loc_pat.search(tail)
        if not loc_m:
            continue
        file, line, col = loc_m.groups()
        # next non-empty line is the code snippet
        after = tail[loc_m.end():]
        code_line = ""
        for raw in after.splitlines()[1:4]:
            stripped = raw.strip()
            if not stripped:
                continue
            if re.match(r"^\d+\t", raw):
                code_line = raw
                break
        if sev not in {"Low", "Medium"}:
            continue
        lines.append(f"{file}:{line}:{col} [{bid}] {name}\n    {code_line.strip()}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
