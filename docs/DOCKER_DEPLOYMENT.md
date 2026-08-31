# Docker部署指南

## 目录

1. [Docker基础](#docker基础)
2. [Dockerfile详解](#dockerfile详解)
3. [Docker Compose配置](#docker-compose配置)
4. [镜像构建](#镜像构建)
5. [容器管理](#容器管理)
6. [网络配置](#网络配置)
7. [存储管理](#存储管理)
8. [性能优化](#性能优化)
9. [安全配置](#安全配置)
10. [故障排除](#故障排除)

---

## Docker基础

### 1. Docker安装

#### Ubuntu/Debian

```bash
# 更新包索引
sudo apt update

# 安装依赖
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加Docker官方GPG密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 设置Docker仓库
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
sudo docker run hello-world
```

#### CentOS/RHEL

```bash
# 卸载旧版本
sudo yum remove docker \
                  docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-engine

# 安装依赖
sudo yum install -y yum-utils

# 添加Docker仓库
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

# 安装Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
sudo docker run hello-world
```

#### macOS

```bash
# 使用Homebrew安装
brew install --cask docker

# 启动Docker Desktop
open /Applications/Docker.app
```

### 2. Docker用户配置

```bash
# 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录或运行
newgrp docker

# 验证用户权限
docker ps
```

---

## Dockerfile详解

### 1. 多阶段构建

创建 `Dockerfile`:

```dockerfile
# 构建阶段
FROM python:3.10-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.10-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    libssl1.1 \
    libffi6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制依赖
COPY --from=builder /root/.local /root/.local

# 确保PATH包含用户安装的包
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 aiops && \
    chown -R aiops:aiops /app

USER aiops

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 优化Dockerfile

#### 使用.dockerignore

创建 `.dockerignore`:

```
# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build

# 环境变量
.env
.env.local
.env.*.local

# IDE
.vscode
.idea
*.swp
*.swo
*~

# Git
.git
.gitignore
.gitattributes

# 文档
docs
*.md

# 测试
tests
.pytest_cache
.coverage
htmlcov

# 日志
logs
*.log

# 临时文件
tmp
temp
*.tmp

# 操作系统
.DS_Store
Thumbs.db
```

#### 层缓存优化

```dockerfile
# 不好的做法 - 每次都重新安装依赖
COPY . .
RUN pip install -r requirements.txt

# 好的做法 - 只在依赖变化时重新安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

---

## Docker Compose配置

### 1. 完整的docker-compose.yml

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL数据库
  postgres:
    image: postgres:14-alpine
    container_name: aiops-postgres
    environment:
      POSTGRES_DB: aiops_agent
      POSTGRES_USER: aiops_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-default_password}
      POSTGRES_INITDB_ARGS: "-E UTF8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql:ro
    ports:
      - "5432:5432"
    networks:
      - aiops-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aiops_user -d aiops_agent"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: aiops-redis
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD:-default_password}
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - aiops-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-default_password}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  # Qdrant向量数据库
  qdrant:
    image: qdrant/qdrant:v1.6.0
    container_name: aiops-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
      - QDRANT__STORAGE__OPTIMIZERS__INDEXING_THRESHOLD=20000
    networks:
      - aiops-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  # AIOps应用
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        BUILD_ENV: production
    container_name: aiops-app
    environment:
      - DATABASE_URL=postgresql://aiops_user:${POSTGRES_PASSWORD:-default_password}@postgres:5432/aiops_agent
      - REDIS_URL=redis://:${REDIS_PASSWORD:-default_password}@redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-change_this_in_production}
      - SECRET_KEY=${SECRET_KEY:-change_this_in_production}
      - APP_ENV=production
      - APP_DEBUG=false
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/var/log/aiops-agent
      - ./plugins:/opt/aiops-agent/plugins
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    networks:
      - aiops-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: aiops-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - app
    networks:
      - aiops-network
    restart: unless-stopped

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    container_name: aiops-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - aiops-network
    restart: unless-stopped

  # Grafana仪表板
  grafana:
    image: grafana/grafana:latest
    container_name: aiops-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    depends_on:
      - prometheus
    networks:
      - aiops-network
    restart: unless-stopped

networks:
  aiops-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  nginx_logs:
  prometheus_data:
  grafana_data:
```

### 2. 环境变量文件

创建 `.env`:

```bash
# 数据库配置
POSTGRES_PASSWORD=your_secure_postgres_password

# Redis配置
REDIS_PASSWORD=your_secure_redis_password

# 应用密钥
JWT_SECRET_KEY=your_jwt_secret_key_change_this_in_production
SECRET_KEY=your_secret_key_change_this_in_production

# Grafana配置
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

---

## 镜像构建

### 1. 构建镜像

```bash
# 构建镜像
docker build -t aiops-agent:latest .

# 构建带标签的镜像
docker build -t aiops-agent:v1.0.0 .

# 构建多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 -t aiops-agent:latest .
```

### 2. 镜像优化

```bash
# 查看镜像大小
docker images aiops-agent

# 清理未使用的镜像
docker image prune -a

# 使用多阶段构建减小镜像大小
# 见上面的Dockerfile示例
```

### 3. 镜像推送到仓库

```bash
# 登录Docker Hub
docker login

# 标记镜像
docker tag aiops-agent:latest yourusername/aiops-agent:latest

# 推送镜像
docker push yourusername/aiops-agent:latest

# 推送到私有仓库
docker tag aiops-agent:latest registry.example.com/aiops-agent:latest
docker push registry.example.com/aiops-agent:latest
```

---

## 容器管理

### 1. 容器生命周期

```bash
# 启动容器
docker-compose up -d

# 停止容器
docker-compose stop

# 重启容器
docker-compose restart

# 删除容器
docker-compose down

# 删除容器和数据卷
docker-compose down -v
```

### 2. 查看容器状态

```bash
# 查看所有容器
docker ps -a

# 查看容器日志
docker-compose logs -f app

# 查看容器资源使用
docker stats

# 进入容器
docker-compose exec app bash

# 查看容器详细信息
docker inspect aiops-app
```

### 3. 容器资源限制

在 `docker-compose.yml` 中添加资源限制:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

---

## 网络配置

### 1. 网络模式

```yaml
services:
  app:
    networks:
      - aiops-network
      - external-network

networks:
  aiops-network:
    driver: bridge
  external-network:
    external: true
```

### 2. 网络隔离

```yaml
# 创建隔离网络
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 只能内部访问

services:
  nginx:
    networks:
      - frontend
  app:
    networks:
      - frontend
      - backend
  postgres:
    networks:
      - backend
```

---

## 存储管理

### 1. 数据卷

```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      device: /mnt/data/postgres
      o: bind
```

### 2. 备份卷

```bash
# 备份数据卷
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data

# 恢复数据卷
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

---

## 性能优化

### 1. 容器优化

```dockerfile
# 使用alpine基础镜像减小镜像大小
FROM python:3.10-alpine

# 合并RUN命令减少层数
RUN apt-get update && \
    apt-get install -y libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 使用.dockerignore排除不必要的文件
# 见上面的.dockerignore示例
```

### 2. 资源限制

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

## 安全配置

### 1. 容器安全

```dockerfile
# 使用非root用户
RUN useradd -m -u 1000 aiops
USER aiops

# 只读文件系统
# 在docker-compose.yml中配置
```

```yaml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### 2. 网络安全

```yaml
# 使用私有网络
networks:
  aiops-network:
    driver: bridge
    internal: true
```

---

## 故障排除

### 1. 常见问题

#### 容器无法启动

```bash
# 查看容器日志
docker-compose logs app

# 检查容器状态
docker-compose ps

# 重新构建镜像
docker-compose build --no-cache app
```

#### 网络连接问题

```bash
# 检查网络
docker network ls
docker network inspect aiops_aiops-network

# 测试连接
docker-compose exec app ping postgres
```

#### 存储问题

```bash
# 检查卷
docker volume ls
docker volume inspect aiops-agent_postgres_data

# 清理未使用的卷
docker volume prune
```

### 2. 调试技巧

```bash
# 交互式调试
docker-compose run --rm app bash

# 查看环境变量
docker-compose exec app env

# 查看进程
docker-compose exec app ps aux
```

---

## 附录

### A. Docker命令速查

```bash
# 镜像相关
docker build -t name:tag .
docker images
docker rmi image_id
docker push name:tag
docker pull name:tag

# 容器相关
docker run -d name
docker ps
docker ps -a
docker stop container_id
docker start container_id
docker rm container_id
docker logs container_id
docker exec -it container_id bash

# Compose相关
docker-compose up
docker-compose up -d
docker-compose down
docker-compose logs
docker-compose ps
docker-compose build
```

### B. 最佳实践

1. 使用多阶段构建减小镜像大小
2. 使用.dockerignore排除不必要的文件
3. 使用非root用户运行容器
4. 设置资源限制防止资源耗尽
5. 使用健康检查确保容器健康
6. 使用网络隔离提高安全性
7. 定期清理未使用的镜像和容器
8. 使用版本标签管理镜像
9. 配置日志轮转防止磁盘满
10. 使用监控工具监控容器性能

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31