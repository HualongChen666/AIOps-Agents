# -*- coding: utf-8 -*-
"""
Start Script for AIOps Agent
AIOps Agent启动脚本

使用uvicorn启动FastAPI应用
"""

# Set UTF-8 encoding for Windows compatibility
import io
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def start_backend():
    """启动后端API"""
    print("[INFO] Starting Backend API...")

    # 检查环境变量
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv()
        print(f"[INFO] Loaded environment from {env_file}")
        # Remove SSL_CERT_FILE if file doesn't exist to prevent startup errors
        ssl_cert_file = os.environ.get("SSL_CERT_FILE")
        if ssl_cert_file and not Path(ssl_cert_file).exists():
            print(
                f"[WARN] SSL_CERT_FILE points to non-existent file: {ssl_cert_file}, "  # noqa: E501
                "removing from environment"
            )
            del os.environ["SSL_CERT_FILE"]
    else:
        print("[WARN] .env file not found, using default configuration")
        print("[HINT] Run 'python setup_production.py' to create configuration file")

    # 启动配置
    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    workers = int(os.getenv("UVICORN_WORKERS", "4"))  # P2优化：默认4个worker
    reload = os.getenv("RELOAD", "false").lower() == "true"

    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Workers: {workers}")
    print(f"Reload: {reload}")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")

    # 启动后端
    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            log_level="info",
            access_log=True,
        )
    except KeyboardInterrupt:
        print("\n[INFO] Backend stopped by user")
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def start_frontend():
    """启动前端UI"""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("[WARN] Frontend directory not found, skipping frontend startup")
        return None

    print("[INFO] Starting Frontend UI...")

    # 检查node_modules
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("[INFO] Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, shell=True)

    # 启动前端
    try:
        process = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir, shell=True)
        print("[INFO] Frontend started on port 3000")
        return process
    except Exception as e:
        print(f"[ERROR] Failed to start frontend: {e}")
        return None


def main():
    """启动应用"""

    print("\n=== Starting AIOps Agent ===\n")

    # 检查启动模式
    mode = os.getenv("START_MODE", "backend").lower()  # 默认只启动后端

    if mode == "backend":
        # 只启动后端
        print("[INFO] Starting Backend only (START_MODE=backend)")
        start_backend()
    elif mode == "frontend":
        # 只启动前端
        print("[INFO] Starting Frontend only (START_MODE=frontend)")
        start_frontend()
    else:
        # 同时启动前后端
        print("[INFO] Starting Backend and Frontend")

        # 启动前端（后台）
        frontend_process = start_frontend()

        # 等待前端启动
        import time

        time.sleep(3)

        # 启动后端（前台）
        print("\n[INFO] Backend starting...")
        try:
            start_backend()
        finally:
            # 清理前端进程
            if frontend_process:
                print("\n[INFO] Stopping frontend...")
                frontend_process.terminate()


if __name__ == "__main__":
    main()
