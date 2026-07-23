# -*- coding: utf-8 -*-
from pathlib import Path

def main() -> None:
    p = Path("cov_with_config.log")
    if not p.exists():
        print("log not found")
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-10:]:
        print(line)

if __name__ == "__main__":
    main()
