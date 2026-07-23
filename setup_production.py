# -*- coding: utf-8 -*-
"""
Production Environment Setup Script
生产环境配置脚本

用于配置生产环境变量和生成安全密钥
"""

import os
import secrets
from pathlib import Path
from typing import Any, Dict  # noqa: F401


def generate_secret_key(length: int = 64) -> str:
    """生成安全的随机密钥"""
    return secrets.token_hex(length)


def setup_production_env():
    """配置生产环境"""

    print("\n=== Production Environment Setup ===\n")

    # 检查.env.production
    env_prod = Path(".env.production")
    if env_prod.exists():
        print(f"[INFO] {env_prod} already exists")  # noqa: F541
        print("[HINT] Backing up to .env.production.backup")
        os.rename(env_prod, ".env.production.backup")

    # 读取模板
    template = Path("env.production.template")
    if not template.exists():
        print(f"[ERROR] {template} not found")  # noqa: F541
        print("[HINT] Please create env.production.template first")
        return False

    print(f"[INFO] Reading template from {template}")  # noqa: F541
    with open(template, "r", encoding="utf-8") as f:
        content = f.read()

    # 生成密钥
    print("\n[INFO] Generating security keys...")
    jwt_secret = generate_secret_key(64)
    internal_api_key = generate_secret_key(32)

    # 替换占位符
    replacements = {
        "JWT_SECRET_KEY=your_jwt_secret_key_here": f"JWT_SECRET_KEY={jwt_secret}",  # noqa: F541
        "INTERNAL_API_KEY=your_internal_api_key_here": (  # noqa: F541, E501
            f"INTERNAL_API_KEY={internal_api_key}"
        ),
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    # 写入.env.production
    with open(env_prod, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[SUCCESS] {env_prod} created")  # noqa: F541
    print(f"\n[INFO] Generated keys:")  # noqa: F541
    print(f"  - JWT_SECRET_KEY: {jwt_secret[:8]}...")  # noqa: F541
    print(f"  - INTERNAL_API_KEY: {internal_api_key[:8]}...")  # noqa: F541

    # 提示API密钥配置
    print("\n[INFO] Please configure API keys in .env.production:")
    print("  - LANGFUSE_SECRET_KEY")
    print("  - LANGFUSE_PUBLIC_KEY")
    print("  - MINIMAX_API_KEY")
    print("  - AI_API_KEY")

    return True


def setup_security_additions():
    """配置安全附加项"""

    print("\n=== Security Configuration ===\n")

    # 检查.env.security.additions
    security_file = Path(".env.security.additions")
    if security_file.exists():
        print(f"[INFO] {security_file} already exists")  # noqa: F541
        return

    # 生成安全配置
    session_secret = generate_secret_key(64)
    encryption_key = generate_secret_key(32)

    content = f"""  # noqa: F541
# Security Configuration
# 安全配置

# Session Secret
SESSION_SECRET={session_secret}

# Encryption Key
ENCRYPTION_KEY={encryption_key}

# Password Hashing
PASSWORD_HASH_ALGORITHM=bcrypt
PASSWORD_HASH_ROUNDS=12

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
"""

    with open(security_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[SUCCESS] {security_file} created")  # noqa: F541
    print(f"\n[INFO] Generated security keys:")  # noqa: F541
    print(f"  - SESSION_SECRET: {session_secret[:8]}...")  # noqa: F541
    print(f"  - ENCRYPTION_KEY: {encryption_key[:8]}...")  # noqa: F541


def setup_database_config():
    """配置数据库"""

    print("\n=== Database Configuration ===\n")

    # 检查.env
    env_file = Path(".env")
    if not env_file.exists():
        print("[WARN] .env not found, creating from .env.production")

        env_prod = Path(".env.production")
        if env_prod.exists():
            import shutil

            shutil.copy(env_prod, env_file)
            print(f"[SUCCESS] {env_file} created from .env.production")  # noqa: F541
        else:
            print("[ERROR] .env.production not found")
            print("[HINT] Run 'python setup_production.py' first")
            return

    print(f"[INFO] Database configuration in {env_file}")  # noqa: F541
    print("\n[INFO] Please configure database settings in .env:")
    print("  - DATABASE_URL (default: sqlite:///./aiops.db)")
    print("  - POSTGRES_HOST (for PostgreSQL)")
    print("  - POSTGRES_PORT (default: 5432)")
    print("  - POSTGRES_DB")
    print("  - POSTGRES_USER")
    print("  - POSTGRES_PASSWORD")


def main():
    """主函数"""

    print("\n=== AIOps Agent Production Setup ===\n")

    # 配置生产环境
    if not setup_production_env():
        return

    # 配置安全附加项
    setup_security_additions()

    # 配置数据库
    setup_database_config()

    print("\n=== Setup Complete ===\n")
    print("[INFO] Next steps:")
    print("  1. Configure API keys in .env.production")
    print("  2. Copy .env.production to .env: copy .env.production .env")
    print("  3. Run 'python start.py' to start the application")
    print("\n[INFO] For Redis setup, see REDIS_START_GUIDE.md")
    print("[INFO] For OpenTelemetry setup, see OPENTELEMETRY_INSTALL_GUIDE.md")


if __name__ == "__main__":
    main()
