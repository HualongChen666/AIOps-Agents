# -*- coding: utf-8 -*-
from pathlib import Path

def main() -> None:
    log = Path("cov_with_config.log")
    if not log.exists():
        print("log not found")
        return
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if "===" in line:
            print(f"{i+1}: {line}")

if __name__ == "__main__":
    main()
