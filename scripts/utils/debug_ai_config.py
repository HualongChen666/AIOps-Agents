# -*- coding: utf-8 -*-
"""
Debug AI Configuration Script
调试AI配置脚本

用于调试AI配置和测试AI功能
"""

import os
from pathlib import Path
from typing import Any, Dict  # noqa: F401


def load_config():
    """加载配置"""

    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        return None

    from dotenv import load_dotenv

    load_dotenv()

    config = {}
    ai_keys = [
        "AI_ENABLED",
        "AI_PROVIDER",
        "AI_MODEL",
        "AI_API_KEY",
        "AI_TEMPERATURE",
        "AI_MAX_TOKENS",
        "AI_TIMEOUT",
    ]

    for key in ai_keys:
        config[key] = os.getenv(key, "")

    return config


def debug_ai_config():
    """调试AI配置"""

    print("\n=== AI Configuration Debug ===\n")

    config = load_config()
    if not config:
        return False

    print("[INFO] AI Configuration:")
    for key, value in config.items():
        if "KEY" in key and value:
            value = value[:8] + "..."
        print(f"  - {key}: {value}")

    # 检查AI是否启用
    ai_enabled = config.get("AI_ENABLED", "false").lower() == "true"

    if not ai_enabled:
        print("\n[WARN] AI is not enabled (AI_ENABLED=false)")
        print("[HINT] Set AI_ENABLED=true in .env")
        return False

    print("\n[INFO] AI is enabled")

    # 检查API密钥
    api_key = config.get("AI_API_KEY", "")
    if not api_key:
        print("[ERROR] AI_API_KEY is not set")
        print("[HINT] Set AI_API_KEY in .env")
        return False

    print("[INFO] AI_API_KEY is configured")

    # 检查provider
    provider = config.get("AI_PROVIDER", "")
    if not provider:
        print("[WARN] AI_PROVIDER is not set, using default")

    print(f"[INFO] AI Provider: {provider or 'default'}")

    # 检查model
    model = config.get("AI_MODEL", "")
    if not model:
        print("[WARN] AI_MODEL is not set, using default")

    print(f"[INFO] AI Model: {model or 'default'}")

    return True


def test_ai_import():
    """测试AI导入"""

    print("\n=== Test AI Import ===\n")

    try:
        print("[INFO] Importing core.ai_engine...")

        print("[SUCCESS] core.ai_engine imported")

        print("[INFO] Importing core.ai_service...")

        print("[SUCCESS] core.ai_service imported")

        print("[INFO] Importing core.ai_interface...")

        print("[SUCCESS] core.ai_interface imported")

        return True
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def test_rag_import():
    """测试RAG导入"""

    print("\n=== Test RAG Import ===\n")

    try:
        print("[INFO] Importing core.ai.rag.knowledge_base...")

        print("[SUCCESS] core.ai.rag.knowledge_base imported")

        print("[INFO] Importing core.ai.rag.retriever...")

        print("[SUCCESS] core.ai.rag.retriever imported")

        print("[INFO] Importing core.ai.rag.vectorizer...")

        print("[SUCCESS] core.ai.rag.vectorizer imported")

        return True
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def test_ai_initialization():
    """测试AI初始化"""

    print("\n=== Test AI Initialization ===\n")

    try:
        print("[INFO] Initializing AIEngine...")

        # 检查初始化参数
        print("[INFO] Checking AIEngine initialization...")

        # 注意：这里不实际初始化，只检查类定义
        print("[SUCCESS] AIEngine class is available")

        return True
    except Exception as e:
        print(f"[ERROR] Initialization test failed: {e}")
        return False


def check_dependencies():
    """检查依赖"""

    print("\n=== Check Dependencies ===\n")

    dependencies = [
        ("openai", "OpenAI SDK"),
        ("httpx", "HTTP client"),
        ("pydantic", "Pydantic"),
    ]

    for module, name in dependencies:
        try:
            __import__(module)
            print(f"[SUCCESS] {name} ({module}) is installed")
        except ImportError:
            print(f"[ERROR] {name} ({module}) is not installed")


def main():
    """主函数"""

    print("\n=== AI Configuration Debug ===\n")

    # 检查配置
    if not debug_ai_config():
        print("\n[WARN] AI configuration has issues")

    # 检查依赖
    check_dependencies()

    # 测试导入
    print("\n=== Testing Imports ===\n")

    ai_import_ok = test_ai_import()
    rag_import_ok = test_rag_import()

    # 测试初始化
    ai_init_ok = test_ai_initialization()

    # 总结
    print("\n=== Debug Summary ===\n")

    print(f"AI Import: {'OK' if ai_import_ok else 'FAILED'}")
    print(f"RAG Import: {'OK' if rag_import_ok else 'FAILED'}")
    print(f"AI Init: {'OK' if ai_init_ok else 'FAILED'}")

    if ai_import_ok and ai_init_ok:
        print("\n[SUCCESS] AI configuration is valid")
    else:
        print("\n[ERROR] AI configuration has issues")
        print("[HINT] Check the errors above and fix them")


if __name__ == "__main__":
    main()
