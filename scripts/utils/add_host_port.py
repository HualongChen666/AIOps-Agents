# -*- coding: utf-8 -*-
"""Add HOST and PORT to .env"""

from pathlib import Path

env_file = Path(".env")
if env_file.exists():
    content = env_file.read_text(encoding="utf-8")

    # 添加HOST和PORT
    if "HOST=0.0.0.0" not in content:
        content += "\n\n# Server Configuration\nHOST=0.0.0.0\nPORT=8000"
        print("Added HOST and PORT")
    else:
        print("HOST and PORT already exist")

    # 写回文件
    env_file.write_text(content, encoding="utf-8")
    print("Updated .env file")
else:
    print(".env not found")
