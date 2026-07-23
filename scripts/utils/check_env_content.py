# -*- coding: utf-8 -*-
"""Check .env content"""

from pathlib import Path

env_file = Path(".env")
if env_file.exists():
    content = env_file.read_text(encoding="utf-8")
    output_file = Path("env_check_output.txt")
    output_file.write_text(content, encoding="utf-8")
    print(f"Content written to {output_file}")
else:
    print(".env not found")
