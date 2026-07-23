# -*- coding: utf-8 -*-
from pathlib import Path

def show(path: str, n: int = 50) -> None:
    p = Path(path)
    if not p.exists():
        print(f"{path}: not found")
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"--- {path} (last {n} of {len(lines)}) ---")
    for line in lines[-n:]:
        print(line)

show("cov_with_config.log", 50)
show("cov_with_config_err.log", 50)
