# -*- coding: utf-8 -*-
"""
Enable AI and RAG Configuration Script
启用AI和RAG配置脚本

用于启用AI功能和RAG知识库功能
"""

from pathlib import Path
from typing import Any, Dict  # noqa: F401


def enable_ai_config():
    """启用AI配置"""

    print("\n=== Enable AI Configuration ===\n")

    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        print("[HINT] Run 'python setup_production.py' first")
        return False

    # 读取.env
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 配置项
    ai_configs = {
        "AI_ENABLED": "true",
        "AI_PROVIDER": "minimax",
        "AI_MODEL": "abab6.5s-chat",
        "AI_API_KEY": "your_minimax_api_key_here",
        "AI_TEMPERATURE": "0.7",
        "AI_MAX_TOKENS": "4096",
        "AI_TIMEOUT": "60",
    }

    # 更新或添加配置
    updated = False
    new_lines = []
    existing_keys = set()

    for line in lines:
        stripped = line.strip()
        if stripped and "=" in stripped:
            key = stripped.split("=")[0].strip()
            existing_keys.add(key)
            if key in ai_configs:
                new_lines.append(f"{key}={ai_configs[key]}\n")
                updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 添加缺失的配置
    for key, value in ai_configs.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}\n")
            updated = True

    if updated:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("[SUCCESS] AI configuration enabled in .env")
        print("\n[INFO] AI Configuration:")
        for key, value in ai_configs.items():
            print(f"  - {key}: {value}")
    else:
        print("[INFO] AI configuration already set")

    return True


def enable_rag_config():
    """启用RAG配置"""

    print("\n=== Enable RAG Configuration ===\n")

    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        return False

    # 读取.env
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 配置项
    rag_configs = {
        "RAG_ENABLED": "true",
        "RAG_VECTOR_DB": "qdrant",
        "RAG_COLLECTION_NAME": "aiops_knowledge",
        "RAG_VECTOR_SIZE": "1536",
        "RAG_TOP_K": "5",
        "RAG_RETRIEVER_TYPE": "hybrid",
        "RAG_RERANKER_ENABLED": "true",
        "RAG_FUSION_ENABLED": "true",
        "RAG_CHUNK_SIZE": "512",
        "RAG_CHUNK_OVERLAP": "50",
    }

    # 更新或添加配置
    updated = False
    new_lines = []
    existing_keys = set()

    for line in lines:
        stripped = line.strip()
        if stripped and "=" in stripped:
            key = stripped.split("=")[0].strip()
            existing_keys.add(key)
            if key in rag_configs:
                new_lines.append(f"{key}={rag_configs[key]}\n")
                updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 添加缺失的配置
    for key, value in rag_configs.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}\n")
            updated = True

    if updated:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("[SUCCESS] RAG configuration enabled in .env")
        print("\n[INFO] RAG Configuration:")
        for key, value in rag_configs.items():
            print(f"  - {key}: {value}")
    else:
        print("[INFO] RAG configuration already set")

    return True


def enable_qdrant_config():
    """启用Qdrant配置"""

    print("\n=== Enable Qdrant Configuration ===\n")

    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] .env file not found")
        return False

    # 读取.env
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 配置项
    qdrant_configs = {
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "QDRANT_API_KEY": "",
        "QDRANT_GRPC_PORT": "6334",
        "QDRANT_PREFER_GRPC": "false",
    }

    # 更新或添加配置
    updated = False
    new_lines = []
    existing_keys = set()

    for line in lines:
        stripped = line.strip()
        if stripped and "=" in stripped:
            key = stripped.split("=")[0].strip()
            existing_keys.add(key)
            if key in qdrant_configs:
                new_lines.append(f"{key}={qdrant_configs[key]}\n")
                updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 添加缺失的配置
    for key, value in qdrant_configs.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}\n")
            updated = True

    if updated:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("[SUCCESS] Qdrant configuration enabled in .env")
        print("\n[INFO] Qdrant Configuration:")
        for key, value in qdrant_configs.items():
            print(f"  - {key}: {value}")
    else:
        print("[INFO] Qdrant configuration already set")

    print("\n[INFO] Please start Qdrant service:")
    print("  - Docker: docker run -p 6333:6333 qdrant/qdrant")
    print("  - Or install locally: https://qdrant.tech/documentation/install/")

    return True


def main():
    """主函数"""

    print("\n=== Enable AI and RAG ===\n")

    # 启用AI配置
    if not enable_ai_config():
        return

    # 启用RAG配置
    if not enable_rag_config():
        return

    # 启用Qdrant配置
    if not enable_qdrant_config():
        return

    print("\n=== Configuration Complete ===\n")
    print("[INFO] Next steps:")
    print("  1. Configure AI_API_KEY in .env")
    print("  2. Start Qdrant service for RAG")
    print("  3. Restart the application: python start.py")
    print("\n[INFO] See RAG_SETUP_GUIDE.md for detailed RAG setup")


if __name__ == "__main__":
    main()
