# 热重载配置文档

## 概述

本文档描述了AIOps SRE Agent的热重载配置方案，包括前端热重载、后端热重载和开发环境热重载配置。

---

## 热重载架构

### 热重载层次

```
┌─────────────────────────────────────────────────────────┐
│              Hot Reload System                            │
├─────────────────────────────────────────────────────────┤
│  Frontend Hot Reload (Next.js)                          │
│  ├── Fast Refresh                                        │
│  ├── HMR (Hot Module Replacement)                       │
│  ├── CSS Hot Reload                                     │
│  └── Component Hot Reload                                │
├─────────────────────────────────────────────────────────┤
│  Backend Hot Reload (FastAPI)                           │
│  ├── Uvicorn Reload                                      │
│  ├── Watchdog Monitoring                                │
│  ├── Dependency Reload                                  │
│  └── Configuration Reload                               │
├─────────────────────────────────────────────────────────┤
│  Development Server                                     │
│  ├── File Watching                                       │
│  ├── Change Detection                                    │
│  ├── Process Restart                                     │
│  └── State Preservation                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 前端热重载

### Next.js热重载

#### 基础配置
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用快速刷新
  reactStrictMode: true,
  
  // 启用热重载
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: /node_modules/
      }
    }
    return config
  },
  
  // 开发服务器配置
  devIndicators: {
    buildActivity: true,
    buildActivityPosition: 'bottom-right'
  }
}

module.exports = nextConfig
```

#### 环境变量配置
```bash
# .env.development
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_ENABLE_HMR=true
```

### React热重载

#### React Fast Refresh
```typescript
// frontend/app/layout.tsx
'use client'

import { ReactNode } from 'react'

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        {children}
      </body>
    </html>
  )
}
```

#### 组件热重载
```typescript
// frontend/components/example.tsx
'use client'

import { useState } from 'react'

export function ExampleComponent() {
  const [count, setCount] = useState(0)
  
  return (
    <div>
      <h1>Count: {count}</h1>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  )
}
```

### CSS热重载

#### CSS模块热重载
```css
/* frontend/styles/example.module.css */
.container {
  padding: 20px;
  background-color: #f0f0f0;
}

.button {
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
}
```

#### Tailwind CSS热重载
```javascript
// tailwind.config.js
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

---

## 后端热重载

### FastAPI热重载

#### Uvicorn热重载
```python
# main.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 启用热重载
        reload_dirs=["./core", "./api"],  # 监控目录
        log_level="debug"
    )
```

#### 环境变量配置
```bash
# .env.development
UVICORN_RELOAD=true
UVICORN_RELOAD_DIRS=./core,./api
UVICORN_LOG_LEVEL=debug
```

### Watchdog监控

#### Watchdog配置
```python
# core/debugging/watchdog_monitor.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import time
import os
from typing import List

class ReloadHandler(FileSystemEventHandler):
    """文件变化处理器"""
    
    def __init__(self, command: List[str]):
        self.command = command
        self.process = None
        self.start_process()
    
    def start_process(self):
        """启动进程"""
        if self.process:
            self.process.terminate()
        self.process = subprocess.Popen(self.command)
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.src_path.endswith('.py'):
            print(f"File modified: {event.src_path}")
            self.start_process()

def start_watchdog_monitor(watch_path: str, command: List[str]):
    """启动Watchdog监控"""
    event_handler = ReloadHandler(command)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

# 使用示例
if __name__ == "__main__":
    command = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    start_watchdog_monitor("./core", command)
```

### 配置热重载

#### 配置文件监控
```python
# core/debugging/config_monitor.py
import os
import time
from typing import Dict, Any
import yaml
import json

class ConfigMonitor:
    """配置文件监控器"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.last_modified = 0
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        elif self.config_path.endswith('.json'):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            return {}
    
    def check_for_changes(self) -> bool:
        """检查配置变化"""
        current_modified = os.path.getmtime(self.config_path)
        if current_modified > self.last_modified:
            self.last_modified = current_modified
            self.config = self.load_config()
            return True
        return False
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self.check_for_changes():
            print("Configuration reloaded")
        return self.config

# 使用示例
if __name__ == "__main__":
    monitor = ConfigMonitor("config.yaml")
    
    while True:
        config = monitor.get_config()
        print(f"Current config: {config}")
        time.sleep(5)
```

---

## 开发环境热重载

### Docker热重载

#### Docker Compose热重载
```yaml
# docker-compose.dev.yml
version: "3.8"

services:
  aiops-agent:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
      - UVICORN_RELOAD=true
    volumes:
      - ./core:/app/core
      - ./api:/app/api
      - ./config.py:/app/config.py
      - ./main.py:/app/main.py
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - redis
      - postgres
    networks:
      - aiops-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - aiops-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=aiops
      - POSTGRES_PASSWORD=aiops_password
      - POSTGRES_DB=aiops
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - aiops-network

networks:
  aiops-network:
    driver: bridge

volumes:
  postgres-data:
```

#### Dockerfile优化
```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV LOG_LEVEL=DEBUG
ENV ENVIRONMENT=development

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 开发脚本

#### 启动脚本
```bash
#!/bin/bash
# scripts/dev-start.sh

echo "Starting AIOps Agent development environment..."

# 启动后端服务
echo "Starting backend services..."
docker-compose -f docker-compose.dev.yml up -d

# 等待服务启动
echo "Waiting for services to start..."
sleep 10

# 启动前端开发服务器
echo "Starting frontend development server..."
cd frontend
npm run dev

echo "Development environment started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
```

#### 停止脚本
```bash
#!/bin/bash
# scripts/dev-stop.sh

echo "Stopping AIOps Agent development environment..."

# 停止后端服务
docker-compose -f docker-compose.dev.yml down

echo "Development environment stopped!"
```

---

## 热重载最佳实践

### 1. 文件监控
- 监控必要的文件和目录
- 排除不必要的文件（node_modules, __pycache__）
- 设置合理的监控间隔
- 使用高效的文件监控工具

### 2. 状态管理
- 保持应用状态在热重载时的一致性
- 使用状态管理工具（Redux, Zustand）
- 避免在全局作用域中存储状态
- 使用localStorage持久化重要状态

### 3. 性能优化
- 减少热重载的文件数量
- 使用增量编译
- 优化构建配置
- 使用缓存提高热重载速度

### 4. 错误处理
- 捕获热重载错误
- 提供错误恢复机制
- 记录热重载日志
- 显示友好的错误信息

---

## 热重载故障排除

### 常见问题

#### 热重载不工作
```bash
# 解决方案：检查文件监控配置
# 1. 验证监控目录是否正确
# 2. 检查文件权限
# 3. 验证文件监控工具是否正常运行
# 4. 检查防火墙设置
```

#### 热重载导致状态丢失
```typescript
// 解决方案：使用状态持久化
import { useEffect } from 'react'

function usePersistState<T>(key: string, initialValue: T) {
  const [state, setState] = useState<T>(() => {
    const saved = localStorage.getItem(key)
    return saved ? JSON.parse(saved) : initialValue
  })
  
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(state))
  }, [key, state])
  
  return [state, setState]
}
```

#### 热重载性能问题
```javascript
// 解决方案：优化构建配置
// next.config.js
module.exports = {
  webpack: (config) => {
    config.cache = {
      type: 'filesystem',
      cacheDirectory: '.next/cache'
    }
    return config
  }
}
```

---

## 热重载验证

### 热重载测试

#### 前端热重载测试
```typescript
// tests/hot-reload.test.ts
import { render, screen } from '@testing-library/react'
import { ExampleComponent } from '../components/example'

describe('Hot Reload', () => {
  it('should preserve state on hot reload', () => {
    const { rerender } = render(<ExampleComponent />)
    
    const button = screen.getByText('Increment')
    button.click()
    
    expect(screen.getByText('Count: 1')).toBeInTheDocument()
    
    // 模拟热重载
    rerender(<ExampleComponent />)
    
    // 验证状态是否保留
    expect(screen.getByText('Count: 1')).toBeInTheDocument()
  })
})
```

#### 后端热重载测试
```python
# tests/test_hot_reload.py
import pytest
import time
import requests

class TestHotReload:
    """测试热重载"""
    
    def test_backend_hot_reload(self):
        """测试后端热重载"""
        # 获取初始响应
        response = requests.get("http://localhost:8000/")
        initial_data = response.json()
        
        # 修改代码
        # 等待热重载
        time.sleep(5)
        
        # 获取新响应
        response = requests.get("http://localhost:8000/")
        new_data = response.json()
        
        # 验证热重载是否生效
        assert new_data != initial_data
```

---

## 热重载配置文件

### 开发环境配置

#### .env.development
```bash
# 开发环境配置
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true

# API配置
API_HOST=localhost
API_PORT=8000
API_URL=http://localhost:8000

# 数据库配置
DATABASE_URL=postgresql://aiops:aiops_password@localhost:5432/aiops
REDIS_URL=redis://localhost:6379

# 热重载配置
UVICORN_RELOAD=true
UVICORN_RELOAD_DIRS=./core,./api
NEXT_PUBLIC_ENABLE_HMR=true
```

#### package.json脚本
```json
{
  "scripts": {
    "dev": "next dev",
    "dev:backend": "uvicorn main:app --host 0.0.0.0 --port 8000 --reload",
    "dev:docker": "docker-compose -f docker-compose.dev.yml up",
    "dev:stop": "docker-compose -f docker-compose.dev.yml down"
  }
}
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队