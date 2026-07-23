# -*- coding: utf-8 -*-
from pathlib import Path

def show(path: str, start: int, end: int) -> None:
    p = Path(path)
    if not p.exists():
        print(f"{path}: not found")
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"--- {path} lines {start}-{end} (of {len(lines)}) ---")
    for i, line in enumerate(lines[start-1:end], start=start):
        print(f"{i}: {line}")

show("cov_with_config_err.log", 9200, 9284)
