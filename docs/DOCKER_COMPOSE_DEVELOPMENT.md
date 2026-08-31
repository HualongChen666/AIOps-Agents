# 开发环境Docker Compose配置文档

## 概述

本文档描述了AIOps SRE Agent的开发环境Docker Compose配置方案，包括配置说明、使用方法和最佳实践。

---

## 开发环境架构

### 开发环境层次

```
┌─────────────────────────────────────────────────────────┐
│         Development Environment Architecture               │
├─────────────────────────────────────────────────────────┤
│  Application Services                                    │
│  ├── AIOps Agent (FastAPI)                              │
│  ├── Frontend (Next.js)                                 │
│  └── Worker Services                                    │
├─────────────────────────────────────────────────────────┤
│  Data Services                                          │
│  ├── PostgreSQL (Database)                              │
│  ├── Redis (Cache)                                      │
│  └── Qdrant (Vector DB)                                 │
├─────────────────────────────────────────────────────────┤
│  Monitoring Services                                    │
│  ├── Prometheus (Metrics)                               │
│  ├── Grafana (Dashboards)                               │
│  └── Jaeger (Tracing)                                   │
├─────────────────────────────────────────────────────────┤
│  Development Tools                                      │
│  ├── pgAdmin (Database UI)                              │
│  ├── Redis Commander (Redis UI)                         │
│  └── Mailhog (Email Testing)                            │
└─────────────────────────────────────────────────────────┘
```

---

## Docker Compose配置

### 主配置文件

#### docker-compose.dev.yml
```yaml
version: "3.8"

services:
  # AIOps Agent Backend
  aiops-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: aiops-agent-dev
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://aiops:aiops_password@postgres:5432/aiops
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - UVICORN_RELOAD=true
      - UVICORN_RELOAD_DIRS=./core,./api
    volumes:
      - ./core:/app/core
      - ./api:/app/api
      - ./config.py:/app/config.py
      - ./main.py:/app/main.py
      - ./tests:/app/tests
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - redis
      - postgres
      - qdrant
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # Frontend Development Server
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: aiops-frontend-dev
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    command: npm run dev
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: aiops-postgres-dev
    environment:
      - POSTGRES_USER=aiops
      - POSTGRES_PASSWORD=aiops_password
      - POSTGRES_DB=aiops
    ports:
      - "5432:5432"
    volumes:
      - postgres-dev-data:/var/lib/postgresql/data
      - ./deploy/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - aiops-dev-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aiops"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: aiops-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis-dev-data:/data
    networks:
      - aiops-dev-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: aiops-qdrant-dev
    ports:
      - "6333:6333"
    volumes:
      - qdrant-dev-data:/qdrant/storage
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # pgAdmin (Database UI)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: aiops-pgadmin-dev
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@aiops.local
      - PGADMIN_DEFAULT_PASSWORD=admin
      - PGADMIN_CONFIG_SERVER_MODE=False
    ports:
      - "5050:80"
    volumes:
      - pgadmin-dev-data:/var/lib/pgadmin
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # Redis Commander (Redis UI)
  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: aiops-redis-commander-dev
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # Mailhog (Email Testing)
  mailhog:
    image: mailhog/mailhog:latest
    container_name: aiops-mailhog-dev
    ports:
      - "1025:1025"
      - "8025:8025"
    networks:
      - aiops-dev-network
    restart: unless-stopped

networks:
  aiops-dev-network:
    driver: bridge

volumes:
  postgres-dev-data:
  redis-dev-data:
  qdrant-dev-data:
  pgadmin-dev-data:
```

### 监控配置

#### docker-compose.monitoring.yml
```yaml
version: "3.8"

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: aiops-prometheus-dev
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-dev-data:/prometheus
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: aiops-grafana-dev
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3001:3000"
    volumes:
      - grafana-dev-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/etc/grafana/dashboards
    networks:
      - aiops-dev-network
    restart: unless-stopped

  # Jaeger
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: aiops-jaeger-dev
    ports:
      - "5775:5775"
      - "6831:6831"
      - "6832:6832"
      - "16686:16686"
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - aiops-dev-network
    restart: unless-stopped

networks:
  aiops-dev-network:
    external: true

volumes:
  prometheus-dev-data:
  grafana-dev-data:
```

---

## 配置说明

### 环境变量

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
POSTGRES_USER=aiops
POSTGRES_PASSWORD=aiops_password
POSTGRES_DB=aiops

# Redis配置
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# Qdrant配置
QDRANT_URL=http://localhost:6333
QDRANT_HOST=localhost
QDRANT_PORT=6333

# 热重载配置
UVICORN_RELOAD=true
UVICORN_RELOAD_DIRS=./core,./api
NEXT_PUBLIC_ENABLE_HMR=true

# 监控配置
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3001
JAEGER_URL=http://localhost:16686

# 开发工具配置
PGADMIN_URL=http://localhost:5050
REDIS_COMMANDER_URL=http://localhost:8081
MAILHOG_URL=http://localhost:8025
```

### Dockerfile配置

#### Dockerfile.dev
```dockerfile
# Dockerfile.dev
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
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

#### frontend/Dockerfile.dev
```dockerfile
# frontend/Dockerfile.dev
FROM node:18-alpine

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制代码
COPY . .

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["npm", "run", "dev"]
```

---

## 使用方法

### 启动开发环境

#### 一键启动
```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 启动监控服务
docker-compose -f docker-compose.monitoring.yml up -d

# 验证服务状态
docker-compose -f docker-compose.dev.yml ps
```

#### 分步启动
```bash
# 1. 启动数据服务
docker-compose -f docker-compose.dev.yml up -d postgres redis qdrant

# 2. 等待数据服务就绪
docker-compose -f docker-compose.dev.yml logs postgres

# 3. 启动应用服务
docker-compose -f docker-compose.dev.yml up -d aiops-agent frontend

# 4. 启动开发工具
docker-compose -f docker-compose.dev.yml up -d pgadmin redis-commander mailhog

# 5. 启动监控服务
docker-compose -f docker-compose.monitoring.yml up -d
```

### 停止开发环境

#### 停止所有服务
```bash
# 停止所有服务
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.monitoring.yml down

# 停止并删除数据卷
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.monitoring.yml down -v
```

### 查看日志

#### 查看服务日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.dev.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.dev.yml logs -f aiops-agent
docker-compose -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.dev.yml logs -f postgres
```

### 进入容器

#### 进入容器调试
```bash
# 进入AIOps Agent容器
docker-compose -f docker-compose.dev.yml exec aiops-agent bash

# 进入PostgreSQL容器
docker-compose -f docker-compose.dev.yml exec postgres psql -U aiops -d aiops

# 进入Redis容器
docker-compose -f docker-compose.dev.yml exec redis redis-cli
```

---

## 开发工具访问

### 服务访问地址

#### 主要服务
- **AIOps Agent API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API文档**: http://localhost:8000/docs

#### 数据服务
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Qdrant**: http://localhost:6333

#### 开发工具
- **pgAdmin**: http://localhost:5050
  - 用户名: admin@aiops.local
  - 密码: admin
- **Redis Commander**: http://localhost:8081
- **Mailhog**: http://localhost:8025

#### 监控服务
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001
  - 用户名: admin
  - 密码: admin
- **Jaeger**: http://localhost:16686

---

## 开发脚本

### 启动脚本

#### scripts/dev-start.sh
```bash
#!/bin/bash
# scripts/dev-start.sh

echo "Starting AIOps Agent development environment..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# 启动数据服务
echo "Starting data services..."
docker-compose -f docker-compose.dev.yml up -d postgres redis qdrant

# 等待数据服务就绪
echo "Waiting for data services to be ready..."
sleep 10

# 启动应用服务
echo "Starting application services..."
docker-compose -f docker-compose.dev.yml up -d aiops-agent frontend

# 启动开发工具
echo "Starting development tools..."
docker-compose -f docker-compose.dev.yml up -d pgadmin redis-commander mailhog

# 启动监控服务
echo "Starting monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d

echo "Development environment started successfully!"
echo ""
echo "Services:"
echo "  - AIOps Agent API: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - pgAdmin: http://localhost:5050"
echo "  - Redis Commander: http://localhost:8081"
echo "  - Mailhog: http://localhost:8025"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3001"
echo "  - Jaeger: http://localhost:16686"
```

#### scripts/dev-stop.sh
```bash
#!/bin/bash
# scripts/dev-stop.sh

echo "Stopping AIOps Agent development environment..."

# 停止所有服务
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.monitoring.yml down

echo "Development environment stopped successfully!"
```

#### scripts/dev-restart.sh
```bash
#!/bin/bash
# scripts/dev-restart.sh

echo "Restarting AIOps Agent development environment..."

# 停止服务
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.monitoring.yml down

# 启动服务
./scripts/dev-start.sh
```

### 数据库脚本

#### scripts/db-migrate.sh
```bash
#!/bin/bash
# scripts/db-migrate.sh

echo "Running database migrations..."

docker-compose -f docker-compose.dev.yml exec aiops-agent alembic upgrade head

echo "Database migrations completed!"
```

#### scripts/db-reset.sh
```bash
#!/bin/bash
# scripts/db-reset.sh

echo "Resetting database..."

# 停止服务
docker-compose -f docker-compose.dev.yml stop postgres

# 删除数据卷
docker volume rm aiops-sre-agent_postgres-dev-data

# 重新启动服务
docker-compose -f docker-compose.dev.yml up -d postgres

# 等待数据库就绪
sleep 10

# 运行迁移
./scripts/db-migrate.sh

echo "Database reset completed!"
```

---

## 最佳实践

### 1. 资源管理
- 合理设置容器资源限制
- 使用数据卷持久化数据
- 定期清理未使用的镜像和容器
- 监控容器资源使用情况

### 2. 网络配置
- 使用自定义网络隔离服务
- 配置服务发现
- 设置合理的端口映射
- 使用健康检查确保服务可用性

### 3. 安全配置
- 不要在生产环境使用开发配置
- 使用环境变量管理敏感信息
- 定期更新基础镜像
- 限制容器权限

### 4. 开发效率
- 使用热重载提高开发效率
- 配置合理的日志级别
- 使用开发工具提高调试效率
- 自动化常用操作

---

## 故障排除

### 常见问题

#### 容器启动失败
```bash
# 解决方案：检查日志
docker-compose -f docker-compose.dev.yml logs aiops-agent

# 检查端口占用
netstat -tuln | grep 8000

# 重新构建镜像
docker-compose -f docker-compose.dev.yml build --no-cache aiops-agent
```

#### 数据库连接失败
```bash
# 解决方案：检查数据库状态
docker-compose -f docker-compose.dev.yml ps postgres

# 检查数据库日志
docker-compose -f docker-compose.dev.yml logs postgres

# 测试数据库连接
docker-compose -f docker-compose.dev.yml exec postgres psql -U aiops -d aiops
```

#### 热重载不工作
```bash
# 解决方案：检查卷挂载
docker-compose -f docker-compose.dev.yml config

# 检查文件权限
ls -la ./core

# 重新启动服务
docker-compose -f docker-compose.dev.yml restart aiops-agent
```

---

## 性能优化

### 资源限制

#### 容器资源限制
```yaml
# docker-compose.dev.yml
services:
  aiops-agent:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 构建优化

#### Dockerfile优化
```dockerfile
# Dockerfile.dev
FROM python:3.12-slim

WORKDIR /app

# 使用多阶段构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 只复制必要的文件
COPY core ./core
COPY api ./api
COPY config.py .
COPY main.py .

# 设置环境变量
ENV PYTHONPATH=/app
ENV LOG_LEVEL=DEBUG

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队