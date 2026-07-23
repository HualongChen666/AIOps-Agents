import os
from pathlib import Path

base = Path("temp")
for f in base.iterdir():
    if f.is_file() and f.suffix in (".py", ".ps1"):
        try:
            f.unlink()
        except Exception:
            pass
print("temp cleanup done")
