# -*- coding: utf-8 -*-
"""
Check Configuration Script
检查配置脚本

用于检查.env文件的配置完整性和有效性
"""

import sys
from pathlib import Path
from typing import Dict, List

# 必需的配置项
REQUIRED_CONFIGS = [
    "ENVIRONMENT",
    "HOST",
    "PORT",
    "DATABASE_URL",
    "JWT_SECRET_KEY",
    "INTERNAL_API_KEY",
]

# AI配置项
AI_CONFIGS = [
    "AI_ENABLED",
    "AI_PROVIDER",
    "AI_API_KEY",
]

# RAG配置项
RAG_CONFIGS = [
    "RAG_ENABLED",
    "RAG_VECTOR_DB",
    "RAG_COLLECTION_NAME",
]

# 可选配置项
OPTIONAL_CONFIGS = [
    "WORKERS",
    "RELOAD",
    "DEBUG",
    "LOG_LEVEL",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DB",
    "REDIS_PASSWORD",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_HOST",
]


def load_env_file(env_file: Path) -> Dict[str, str]:
    """加载.env文件"""

    if not env_file.exists():
        print(f"[ERROR] {env_file} not found")
        return {}

    configs = {}
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    configs[key] = value

    return configs


def check_required_configs(configs: Dict[str, str]) -> List[str]:
    """检查必需的配置项"""

    missing = []
    for config in REQUIRED_CONFIGS:
        if config not in configs or not configs[config]:
            missing.append(config)

    return missing


def check_ai_configs(configs: Dict[str, str]) -> List[str]:
    """检查AI配置项"""

    if configs.get("AI_ENABLED", "false").lower() != "true":
        return []

    missing = []
    for config in AI_CONFIGS:
        if config not in configs or not configs[config]:
            missing.append(config)

    return missing


def check_rag_configs(configs: Dict[str, str]) -> List[str]:
    """检查RAG配置项"""

    if configs.get("RAG_ENABLED", "false").lower() != "true":
        return []

    missing = []
    for config in RAG_CONFIGS:
        if config not in configs or not configs[config]:
            missing.append(config)

    return missing


def check_config_values(configs: Dict[str, str]) -> List[str]:
    """检查配置值的有效性"""

    invalid = []

    # 检查端口
    if "PORT" in configs:
        try:
            port = int(configs["PORT"])
            if port < 1 or port > 65535:
                invalid.append(f"PORT: invalid port number {port}")
        except ValueError:
            invalid.append("PORT: not a valid number")

    # 检查JWT密钥长度
    if "JWT_SECRET_KEY" in configs:
        jwt_key = configs["JWT_SECRET_KEY"]
        if len(jwt_key) < 32:
            invalid.append(f"JWT_SECRET_KEY: too short (minimum 32 characters)")  # noqa: F541

    # 检查数据库URL
    if "DATABASE_URL" in configs:
        db_url = configs["DATABASE_URL"]
        if not db_url.startswith(("sqlite:///", "postgresql://", "mysql://", "mongodb://")):
            invalid.append(f"DATABASE_URL: invalid database URL format")  # noqa: F541

    return invalid


def check_env_file(env_file: Path) -> bool:
    """检查.env文件"""

    print(f"\n=== Checking {env_file} ===\n")

    if not env_file.exists():
        print(f"[ERROR] {env_file} not found")
        return False

    # 加载配置
    configs = load_env_file(env_file)

    if not configs:
        print(f"[ERROR] No configurations found in {env_file}")
        return False

    print(f"[INFO] Loaded {len(configs)} configuration(s)")  # noqa: F541

    # 检查必需配置
    missing_required = check_required_configs(configs)
    if missing_required:
        print(f"\n[ERROR] Missing required configuration(s):")  # noqa: F541
        for config in missing_required:
            print(f"  - {config}")  # noqa: F541
    else:
        print(f"\n[SUCCESS] All required configurations present")  # noqa: F541

    # 检查AI配置
    missing_ai = check_ai_configs(configs)
    if missing_ai:
        print(f"\n[WARN] Missing AI configuration(s) (AI_ENABLED=true):")  # noqa: F541
        for config in missing_ai:
            print(f"  - {config}")  # noqa: F541

    # 检查RAG配置
    missing_rag = check_rag_configs(configs)
    if missing_rag:
        print(f"\n[WARN] Missing RAG configuration(s) (RAG_ENABLED=true):")  # noqa: F541
        for config in missing_rag:
            print(f"  - {config}")  # noqa: F541

    # 检查配置值
    invalid_values = check_config_values(configs)
    if invalid_values:
        print(f"\n[ERROR] Invalid configuration value(s):")  # noqa: F541
        for config in invalid_values:
            print(f"  - {config}")  # noqa: F541

    # 显示所有配置
    print(f"\n[INFO] All configurations:")  # noqa: F541
    for key, value in sorted(configs.items()):
        # 隐藏敏感信息
        if "SECRET" in key.upper() or "KEY" in key.upper() or "PASSWORD" in key.upper():
            value = value[:8] + "..." if len(value) > 8 else "***"
        print(f"  - {key}: {value}")

    # 返回检查结果
    has_errors = bool(missing_required or invalid_values)
    return not has_errors


def main():
    """主函数"""

    print("\n=== Configuration Check ===\n")

    # 检查.env
    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        print("[HINT] Run 'python setup_production.py' first")
        sys.exit(1)

    # 检查配置
    success = check_env_file(env_file)

    if success:
        print("\n[SUCCESS] Configuration check passed")
        print("[INFO] You can now run: python start.py")
        sys.exit(0)
    else:
        print("\n[ERROR] Configuration check failed")
        print("[INFO] Please fix the issues above and run again")
        sys.exit(1)


if __name__ == "__main__":
    main()
