# -*- coding: utf-8 -*-
from pathlib import Path

def main() -> None:
    p = Path("cov_with_config_err.log")
    if not p.exists():
        print("err log not found")
        return
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    keywords = ["INTERNALERROR", "Traceback", "worker", "FAILED", "ERROR", "error", "coverage", "KeyboardInterrupt"]
    # print lines near errors (last 30 occurrences)
    hits = []
    for i, line in enumerate(lines):
        low = line.lower()
        if any(k in low for k in ["traceback", "internalerror", "worker", "failed", "keyboardinterrupt"]):
            hits.append((i, line))
    if not hits:
        print("No error keywords found")
        return
    for i, line in hits[-50:]:
        print(f"{i+1}: {line}")

if __name__ == "__main__":
    main()
