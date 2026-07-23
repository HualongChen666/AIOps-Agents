# -*- coding: utf-8 -*-
from pathlib import Path

def main() -> None:
    src = Path("cov_full.log")
    dst = Path("cov_full_tail.txt")
    if not src.exists():
        dst.write_text("log not found", encoding="utf-8")
        return
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    dst.write_text("\n".join(lines[-20:]), encoding="utf-8")

if __name__ == "__main__":
    main()
