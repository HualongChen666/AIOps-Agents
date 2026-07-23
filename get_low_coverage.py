# -*- coding: utf-8 -*-
"""List low-coverage core/api files sorted by missing statements."""
import json
from pathlib import Path


def main() -> None:
    data = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
    rows = []
    for name, file_info in data.get("files", {}).items():
        summary = file_info.get("summary", {})
        stmts = summary.get("num_statements", 0)
        missing = summary.get("missing_lines", 0)
        percent = summary.get("percent_covered", 0.0)
        if stmts == 0:
            continue
        if percent < 80 and missing > 0:
            rows.append((name, stmts, missing, percent))
    rows.sort(key=lambda x: x[2], reverse=True)
    out_lines = [f"{r[0]},{r[1]},{r[2]},{r[3]}" for r in rows]
    Path("low_coverage.txt").write_text("\n".join(out_lines), encoding="utf-8")
    for line in out_lines:
        print(line)


if __name__ == "__main__":
    main()
