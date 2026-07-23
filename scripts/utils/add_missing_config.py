# -*- coding: utf-8 -*-
"""
Add Missing Configuration
添加缺失的配置项
"""

from pathlib import Path


def add_missing_config():
    """添加缺失的配置"""

    env_file = Path(".env")

    if not env_file.exists():
        print("[ERROR] .env file does not exist")
        return False

    print("[INFO] Reading .env file...")
    content = env_file.read_text(encoding="utf-8")

    # 添加缺失的配置
    missing_configs = {
        "HOST=0.0.0.0": "HOST",
        "PORT=8000": "PORT",
        "DATABASE_URL=sqlite:///./aiops.db": "DATABASE_URL",
        "HISTORY_MAX_POINTS=60": "HISTORY_MAX_POINTS",
        "WF_NODE_MIN_DELAY_MS=500": "WF_NODE_MIN_DELAY_MS",
        "WF_NODE_MAX_DELAY_MS=1200": "WF_NODE_MAX_DELAY_MS",
    }

    for config_line, config_key in missing_configs.items():
        if config_key not in content:
            content += f"\n{config_line}"
            print(f"[INFO] Added {config_key}")
        else:
            print(f"[OK] {config_key} already exists")

    # 写回文件
    env_file.write_text(content, encoding="utf-8")

    print("\n[SUCCESS] Missing configuration added")
    return True


if __name__ == "__main__":
    success = add_missing_config()
    exit(0 if success else 1)
