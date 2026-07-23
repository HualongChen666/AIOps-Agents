import json
from pathlib import Path


def main() -> None:
    cov_path = Path("coverage.json")
    if not cov_path.exists():
        print("coverage.json not found")
        return
    data = json.loads(cov_path.read_text(encoding="utf-8"))
    totals = data["totals"]
    print(f"TOTAL: {totals['percent_cured']:.2f}%" if False else f"TOTAL: {totals['percent_covered']:.2f}%")
    print(f"FILES: {len(data['files'])}")
    print(f"STMTS: {totals['num_statements']} COVERED: {totals['covered_lines']}")

    rows = []
    for name, file_info in data.get("files", {}).items():
        summary = file_info.get("summary")
        if not summary:
            continue
        rows.append(
            (
                name,
                summary["num_statements"],
                summary.get("missing_lines", 0),
                summary.get("percent_covered", 0),
            )
        )

    rows.sort(key=lambda x: x[2], reverse=True)
    top_missing = rows[:20]
    print("\nTOP20_MISSING:")
    for r in top_missing:
        print(f"{r[0]},{r[1]},{r[2]},{r[3]}")

    low = [r for r in rows if r[3] < 80 and r[1] > 0]
    low.sort(key=lambda x: x[2], reverse=True)
    print(f"\nLOW_COVERAGE_COUNT: {len(low)}")
    print("\nTOP20_LOW:")
    for r in low[:20]:
        print(f"{r[0]},{r[1]},{r[2]},{r[3]}")

    out = {
        "total_percent": totals["percent_covered"],
        "files": len(data["files"]),
        "num_statements": totals["num_statements"],
        "covered_lines": totals["covered_lines"],
        "missing_lines": totals.get("missing_lines", 0),
        "top_missing": [
            {"file": r[0], "statements": r[1], "missing": r[2], "percent": r[3]} for r in top_missing
        ],
        "top_low": [
            {"file": r[0], "statements": r[1], "missing": r[2], "percent": r[3]} for r in low[:20]
        ],
    }
    Path("coverage_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nWROTE coverage_summary.json")


if __name__ == "__main__":
    main()
