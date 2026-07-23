# -*- coding: utf-8 -*-
"""
Verify Configuration Script
验证配置脚本

用于验证配置文件和环境的完整性
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple  # noqa: F401


def verify_file_exists(file_path: Path, description: str = "") -> bool:
    """验证文件是否存在"""

    desc = f" ({description})" if description else ""  # noqa: F541

    if file_path.exists():
        print(f"[SUCCESS] {file_path}{desc}")  # noqa: F541
        return True
    else:
        print(f"[ERROR] {file_path} not found{desc}")  # noqa: F541
        return False


def verify_directory_exists(dir_path: Path, description: str = "") -> bool:
    """验证目录是否存在"""

    desc = f" ({description})" if description else ""  # noqa: F541

    if dir_path.exists() and dir_path.is_dir():
        print(f"[SUCCESS] {dir_path}{desc}")  # noqa: F541
        return True
    else:
        print(f"[ERROR] {dir_path} not found{desc}")  # noqa: F541
        return False


def verify_python_version():
    """验证Python版本"""

    print("\n=== Python Version ===\n")

    version = sys.version_info
    print(f"[INFO] Python version: {version.major}.{version.minor}.{version.micro}")  # noqa: F541

    # 检查Python版本
    if version.major != 3:
        print(f"[ERROR] Python 3 is required (found {version.major})")  # noqa: F541
        return False

    # 检查Python 3.14兼容性
    if version.minor >= 14:
        print("[WARN] Python 3.14 may have compatibility issues with SQLAlchemy")
        print("[HINT] Consider using Python 3.10 or 3.11")
        # 不返回False，只是警告

    return True


def verify_project_structure():
    """验证项目结构"""

    print("\n=== Project Structure ===\n")

    results = []

    # 核心目录
    results.append(verify_directory_exists(Path("api"), "API routes"))
    results.append(verify_directory_exists(Path("core"), "Core modules"))
    results.append(verify_file_exists(Path("core/models.py"), "Database models"))

    # 可选目录
    results.append(verify_directory_exists(Path("frontend"), "Frontend UI"))
    results.append(verify_directory_exists(Path("alembic"), "Database migrations"))

    return all(results)


def verify_configuration_files():
    """验证配置文件"""

    print("\n=== Configuration Files ===\n")

    results = []

    # 必需文件
    results.append(verify_file_exists(Path("config.py"), "Configuration loader"))
    results.append(verify_file_exists(Path("main.py"), "FastAPI application"))

    # 环境配置
    results.append(verify_file_exists(Path(".env"), "Environment variables"))
    results.append(verify_file_exists(Path("env.production.template"), "Production template"))

    # 可选文件
    results.append(verify_file_exists(Path(".env.production"), "Production config"))
    results.append(verify_file_exists(Path(".env.security.additions"), "Security config"))

    return all(results[:4])  # 只检查必需文件


def verify_env_config():
    """验证环境配置"""

    print("\n=== Environment Configuration ===\n")

    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        return False

    # 尝试加载.env
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        print("[WARN] python-dotenv not installed, reading .env directly")
        # 直接读取.env文件
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    # 检查必需配置
    required_configs = [
        ("ENVIRONMENT", "Environment name"),
        ("HOST", "Server host"),
        ("PORT", "Server port"),
        ("DATABASE_URL", "Database connection"),
        ("JWT_SECRET_KEY", "JWT secret key"),
        ("INTERNAL_API_KEY", "Internal API key"),
    ]

    results = []
    for config, description in required_configs:
        value = os.getenv(config)
        if value:
            # 隐藏敏感信息
            if "SECRET" in config or "KEY" in config:
                value = value[:8] + "..." if len(value) > 8 else "***"
            print(f"[SUCCESS] {config}: {value} ({description})")  # noqa: F541
            results.append(True)
        else:
            print(f"[ERROR] {config} not set ({description})")  # noqa: F541
            results.append(False)

    return all(results)


def verify_dependencies():
    """验证依赖"""

    print("\n=== Dependencies ===\n")

    dependencies = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("sqlalchemy", "SQL ORM"),
        ("httpx", "HTTP client"),
    ]

    results = []
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"[SUCCESS] {module} ({description})")  # noqa: F541
            results.append(True)
        except ImportError:
            print(f"[ERROR] {module} not installed ({description})")  # noqa: F541
            results.append(False)

    # python-dotenv是可选的（脚本可以直接读取.env）
    try:
        __import__("dotenv")
        print("[SUCCESS] python-dotenv (Environment variables)")
    except ImportError:
        print("[WARN] python-dotenv not installed (optional, script can read .env directly)")

    return all(results)


def verify_optional_dependencies():
    """验证可选依赖"""

    print("\n=== Optional Dependencies ===\n")

    dependencies = [
        ("redis", "Redis client"),
        ("langchain", "LangChain framework"),
        ("openai", "OpenAI SDK"),
        ("jwt", "PyJWT"),
    ]

    for module, description in dependencies:
        try:
            __import__(module)
            print(f"[SUCCESS] {module} ({description})")  # noqa: F541
        except ImportError:
            print(f"[WARN] {module} not installed ({description})")  # noqa: F541

    # 可选依赖不返回结果，只是警告


def main():
    """主函数"""

    print("\n=== Configuration Verification ===\n")

    # 验证Python版本
    python_ok = verify_python_version()

    # 验证项目结构
    structure_ok = verify_project_structure()

    # 验证配置文件
    config_files_ok = verify_configuration_files()

    # 验证环境配置
    env_ok = verify_env_config()

    # 验证依赖
    deps_ok = verify_dependencies()

    # 验证可选依赖
    verify_optional_dependencies()

    # 总结
    print("\n=== Verification Summary ===\n")

    print(f"Python Version: {'OK' if python_ok else 'FAILED'}")  # noqa: F541
    print(f"Project Structure: {'OK' if structure_ok else 'FAILED'}")  # noqa: F541
    print(f"Configuration Files: {'OK' if config_files_ok else 'FAILED'}")  # noqa: F541
    print(f"Environment Config: {'OK' if env_ok else 'FAILED'}")  # noqa: F541
    print(f"Dependencies: {'OK' if deps_ok else 'FAILED'}")  # noqa: F541

    all_ok = all([python_ok, structure_ok, config_files_ok, env_ok, deps_ok])

    if all_ok:
        print("\n[SUCCESS] Configuration verification passed")
        print("[INFO] You can now run: python start.py")
        sys.exit(0)
    else:
        print("\n[ERROR] Configuration verification failed")
        print("[HINT] Fix the issues above and run again")
        sys.exit(1)


if __name__ == "__main__":
    main()
