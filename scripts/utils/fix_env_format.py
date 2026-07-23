# -*- coding: utf-8 -*-
"""Fix .env file"""

from pathlib import Path

env_file = Path(".env")
if env_file.exists():
    content = env_file.read_text(encoding="utf-8")

    # 修复格式错误
    content = content.replace(
        "WF_NODE_MAX_DELAY_MS=1200AI_PROVIDER=minimax",
        "WF_NODE_MAX_DELAY_MS=1200\nAI_PROVIDER=minimax",
    )

    # 添加缺失的配置
    if "HOST=" not in content:
        content += "\nHOST=0.0.0.0"
        print("Added HOST")

    if "PORT=" not in content:
        content += "\nPORT=8000"
        print("Added PORT")

    # 写回文件
    env_file.write_text(content, encoding="utf-8")
    print("Fixed .env file")
else:
    print(".env not found")
