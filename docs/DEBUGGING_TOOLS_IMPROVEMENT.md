# 调试工具改进文档

## 概述

本文档描述了AIOps SRE Agent的调试工具改进方案，包括调试配置、调试工具使用和调试最佳实践。

---

## 调试工具架构

### 调试工具层次

```
┌─────────────────────────────────────────────────────────┐
│              Debugging Tools System                       │
├─────────────────────────────────────────────────────────┤
│  IDE Integration (VS Code, PyCharm)                     │
│  ├── Breakpoints                                         │
│  ├── Variable Inspection                                │
│  ├── Call Stack                                         │
│  └── Expression Evaluation                              │
├─────────────────────────────────────────────────────────┤
│  Python Debugging (pdb, ipdb)                           │
│  ├── Command Line Debugging                              │
│  ├── Remote Debugging                                    │
│  ├── Post-Mortem Debugging                              │
│  └── Conditional Breakpoints                             │
├─────────────────────────────────────────────────────────┤
│  Logging Debugging                                      │
│  ├── Structured Logging                                 │
│  ├── Log Levels                                          │
│  ├── Log Context                                        │
│  └── Log Aggregation                                    │
├─────────────────────────────────────────────────────────┤
│  Performance Debugging                                  │
│  ├── Profiling                                           │
│  ├── Memory Profiling                                   │
│  ├── CPU Profiling                                      │
│  └── I/O Profiling                                      │
└─────────────────────────────────────────────────────────┘
```

---

## IDE调试配置

### VS Code调试配置

#### launch.json配置
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "development"
      }
    },
    {
      "name": "Python: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload"
      ],
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "development"
      }
    },
    {
      "name": "Python: Tests",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v",
        "-n",
        "auto"
      ],
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Python: Remote Attach",
      "type": "debugpy",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

#### settings.json配置
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests/",
    "-v",
    "-n",
    "auto"
  ],
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "none"
  }
}
```

### PyCharm调试配置

#### Run/Debug配置
```python
# PyCharm运行配置
# 1. 创建新的Python运行配置
# 2. 设置Module: uvicorn
# 3. 设置Parameters: main:app --host 0.0.0.0 --port 8000 --reload
# 4. 设置环境变量:
#    PYTHONPATH=/path/to/project
#    LOG_LEVEL=DEBUG
#    ENVIRONMENT=development
```

#### 远程调试配置
```python
# 远程调试配置
# 1. 在服务器上安装pydevd-pycharm
# pip install pydevd-pycharm~=203.0

# 2. 在代码中添加远程调试
import pydevd_pycharm
pydevd_pycharm.settrace('localhost', port=12345, stdoutToServer=True, stderrToServer=True)

# 3. 在PyCharm中配置Python Remote Debug
# 4. 设置Host: localhost, Port: 12345
# 5. 设置Path Mapping
```

---

## Python调试工具

### pdb调试

#### 基础pdb使用
```python
# core/debugging/pdb_debugger.py
import pdb

def debug_function(x, y):
    """调试函数"""
    result = x + y
    
    # 设置断点
    pdb.set_trace()
    
    # 检查变量
    print(f"x: {x}")
    print(f"y: {y}")
    print(f"result: {result}")
    
    return result

# 使用方法
if __name__ == "__main__":
    debug_function(10, 20)
```

#### pdb命令
```python
# 常用pdb命令
# n (next): 执行下一行
# s (step): 进入函数
# c (continue): 继续执行
# b (break): 设置断点
# l (list): 显示代码
# p (print): 打印变量
# pp (pretty print): 美化打印
# w (where): 显示调用栈
# q (quit): 退出调试
```

### ipdb调试

#### ipdb配置
```python
# requirements.txt
# ipdb>=0.13.0

# core/debugging/ipdb_debugger.py
import ipdb

def debug_function(x, y):
    """调试函数"""
    result = x + y
    
    # 设置断点
    ipdb.set_trace()
    
    # 检查变量
    print(f"x: {x}")
    print(f"y: {y}")
    print(f"result: {result}")
    
    return result

# 使用方法
if __name__ == "__main__":
    debug_function(10, 20)
```

#### ipdb增强功能
```python
# ipdb增强功能
# 1. Tab补全
# 2. 语法高亮
# 3. 更好的变量显示
# 4. 颜色输出
```

### 远程调试

#### debugpy远程调试
```python
# requirements.txt
# debugpy>=1.8.0

# core/debugging/remote_debugger.py
import debugpy

def enable_remote_debugging(port=5678):
    """启用远程调试"""
    debugpy.listen(("0.0.0.0", port))
    print(f"Remote debugging enabled on port {port}")
    debugpy.wait_for_client()

def debug_function(x, y):
    """调试函数"""
    result = x + y
    
    # 设置断点
    debugpy.breakpoint()
    
    # 检查变量
    print(f"x: {x}")
    print(f"y: {y}")
    print(f"result: {result}")
    
    return result

# 使用方法
if __name__ == "__main__":
    enable_remote_debugging()
    debug_function(10, 20)
```

#### Docker远程调试
```python
# Docker远程调试配置
# 1. 在Dockerfile中安装debugpy
# RUN pip install debugpy

# 2. 在docker-compose.yml中暴露调试端口
# ports:
#   - "5678:5678"

# 3. 在代码中启用远程调试
# import debugpy
# debugpy.listen(("0.0.0.0", 5678))
# debugpy.wait_for_client()
```

---

## 日志调试

### 结构化日志

#### 日志配置
```python
# core/debugging/logging_config.py
import logging
import json
from typing import Any, Dict
from contextvars import ContextVar

# 上下文变量
trace_id: ContextVar[str] = ContextVar('trace_id', default='')

class StructuredLogHandler(logging.Handler):
    """结构化日志处理器"""
    
    def emit(self, record: logging.LogRecord) -> None:
        """发出日志"""
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id.get(),
            "context": getattr(record, "context", {}),
            "extra": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }
        }
        
        # 输出JSON格式日志
        print(json.dumps(log_entry))
    
    def formatTime(self, record: logging.LogRecord) -> str:
        """格式化时间"""
        return self.formatTime(record)

def configure_logging(level: str = "DEBUG") -> None:
    """配置结构化日志"""
    handler = StructuredLogHandler()
    logging.root.addHandler(handler)
    logging.root.setLevel(getattr(logging, level.upper()))

# 使用示例
if __name__ == "__main__":
    configure_logging("DEBUG")
    
    logger = logging.getLogger(__name__)
    logger.info("Test message", extra={"context": {"key": "value"}})
```

#### 日志上下文
```python
# core/debugging/log_context.py
from contextvars import ContextVar
from typing import Any, Dict

# 上下文变量
request_id: ContextVar[str] = ContextVar('request_id', default='')
user_id: ContextVar[str] = ContextVar('user_id', default='')
operation_id: ContextVar[str] = ContextVar('operation_id', default='')

class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.tokens = []
    
    def __enter__(self):
        """进入上下文"""
        for key, value in self.context.items():
            if key == 'request_id':
                self.tokens.append(request_id.set(value))
            elif key == 'user_id':
                self.tokens.append(user_id.set(value))
            elif key == 'operation_id':
                self.tokens.append(operation_id.set(value))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        for token in self.tokens:
            token.reset()

# 使用示例
if __name__ == "__main__":
    with LogContext(request_id="123", user_id="456"):
        logger.info("Operation started")
        # 执行操作
        logger.info("Operation completed")
```

---

## 性能调试

### 性能分析

#### cProfile性能分析
```python
# core/debugging/profiler.py
import cProfile
import pstats
import io
from typing import Callable, Any

def profile_function(func: Callable) -> Callable:
    """性能分析装饰器"""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        
        # 输出性能分析结果
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        print(s.getvalue())
        
        return result
    return wrapper

# 使用示例
@profile_function
def slow_function():
    """慢函数"""
    total = 0
    for i in range(1000000):
        total += i
    return total

if __name__ == "__main__":
    slow_function()
```

#### memory_profiler内存分析
```python
# requirements.txt
# memory-profiler>=0.61.0

# core/debugging/memory_profiler.py
from memory_profiler import profile

@profile
def memory_intensive_function():
    """内存密集型函数"""
    data = []
    for i in range(100000):
        data.append([j for j in range(100)])
    return data

# 使用方法
if __name__ == "__main__":
    memory_intensive_function()
```

### 线程调试

#### 线程调试
```python
# core/debugging/thread_debugger.py
import threading
import time
from typing import Any

def debug_thread_function(name: str, delay: float) -> None:
    """调试线程函数"""
    print(f"Thread {name} started")
    time.sleep(delay)
    print(f"Thread {name} completed")

def create_debug_threads() -> None:
    """创建调试线程"""
    threads = []
    
    for i in range(5):
        thread = threading.Thread(
            target=debug_thread_function,
            args=(f"Thread-{i}", i * 0.1)
        )
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()

# 使用方法
if __name__ == "__main__":
    create_debug_threads()
```

---

## 异步调试

### 异步调试

#### asyncio调试
```python
# core/debugging/async_debugger.py
import asyncio
import traceback
from typing import Any

async def debug_async_function(x: int, y: int) -> int:
    """调试异步函数"""
    print(f"Starting async function with x={x}, y={y}")
    
    try:
        result = await asyncio.sleep(1, result=x + y)
        print(f"Async function completed with result={result}")
        return result
    except Exception as e:
        print(f"Error in async function: {e}")
        traceback.print_exc()
        raise

async def main() -> None:
    """主函数"""
    try:
        result = await debug_async_function(10, 20)
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error in main: {e}")

# 使用方法
if __name__ == "__main__":
    asyncio.run(main())
```

#### 异步任务调试
```python
# core/debugging/async_task_debugger.py
import asyncio
from typing import Any

async def debug_async_task(task_id: str, delay: float) -> str:
    """调试异步任务"""
    print(f"Task {task_id} started")
    await asyncio.sleep(delay)
    print(f"Task {task_id} completed")
    return task_id

async def create_debug_tasks() -> None:
    """创建调试任务"""
    tasks = []
    
    for i in range(5):
        task = asyncio.create_task(
            debug_async_task(f"Task-{i}", i * 0.1)
        )
        tasks.append(task)
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks)
    print(f"All tasks completed: {results}")

# 使用方法
if __name__ == "__main__":
    asyncio.run(create_debug_tasks())
```

---

## 数据库调试

### 数据库调试

#### SQL调试
```python
# core/debugging/sql_debugger.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Any, Dict
import logging

# 配置SQL日志
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)

def debug_sql_query(engine_url: str, query: str) -> Any:
    """调试SQL查询"""
    engine = create_engine(engine_url, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        result = session.execute(text(query))
        return result.fetchall()
    finally:
        session.close()
        engine.dispose()

# 使用示例
if __name__ == "__main__":
    engine_url = "postgresql://user:password@localhost:5432/aiops"
    query = "SELECT * FROM alerts LIMIT 10"
    results = debug_sql_query(engine_url, query)
    print(f"Results: {results}")
```

#### 连接池调试
```python
# core/debugging/connection_pool_debugger.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from typing import Any

def debug_connection_pool(engine_url: str) -> Dict[str, Any]:
    """调试连接池"""
    engine = create_engine(
        engine_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=True
    )
    
    # 获取连接池状态
    pool = engine.pool
    pool_status = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": pool._max_overflow
    }
    
    print(f"Connection pool status: {pool_status}")
    
    return pool_status

# 使用示例
if __name__ == "__main__":
    engine_url = "postgresql://user:password@localhost:5432/aiops"
    pool_status = debug_connection_pool(engine_url)
    print(f"Pool status: {pool_status}")
```

---

## API调试

### API调试

#### FastAPI调试
```python
# core/debugging/fastapi_debugger.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from typing import Callable

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Any:
    """记录请求日志"""
    start_time = time.time()
    
    # 记录请求信息
    logging.info(f"Request: {request.method} {request.url}")
    logging.info(f"Headers: {dict(request.headers)}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logging.info(f"Response: {response.status_code}")
    logging.info(f"Process time: {process_time:.3f}s")
    
    # 添加处理时间到响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# 调试端点
@app.get("/debug/health")
async def debug_health():
    """调试健康检查"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@app.get("/debug/config")
async def debug_config():
    """调试配置"""
    return {
        "environment": "development",
        "log_level": "DEBUG",
        "debug_mode": True
    }

# 使用方法
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

---

## 调试最佳实践

### 1. 调试策略
- 使用IDE调试器进行交互式调试
- 使用日志进行远程调试
- 使用性能分析工具定位性能问题
- 使用断点进行条件调试

### 2. 调试技巧
- 设置条件断点
- 使用日志记录关键变量
- 使用异常处理捕获错误
- 使用单元测试隔离问题

### 3. 调试工具
- 使用VS Code或PyCharm进行IDE调试
- 使用pdb或ipdb进行命令行调试
- 使用debugpy进行远程调试
- 使用cProfile进行性能分析

### 4. 调试安全
- 不要在生产环境启用调试模式
- 不要在日志中记录敏感信息
- 使用环境变量控制调试开关
- 定期清理调试代码

---

## 调试工具验证

### 调试工具测试

#### 调试功能测试
```python
# tests/test_debugging.py
import pytest
from core.debugging.pdb_debugger import debug_function
from core.debugging.profiler import profile_function

class TestDebuggingTools:
    """测试调试工具"""
    
    def test_debug_function(self):
        """测试调试函数"""
        result = debug_function(10, 20)
        assert result == 30
    
    def test_profile_function(self):
        """测试性能分析函数"""
        @profile_function
        def test_func():
            return sum(range(1000))
        
        result = test_func()
        assert result == 499500
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队