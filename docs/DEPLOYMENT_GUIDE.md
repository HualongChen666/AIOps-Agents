# Deployment Guide
部署指南

## 概述

本文档描述了AIOps SRE Agent的部署流程，包括开发环境、测试环境和生产环境的部署配置。

## 环境要求

### 硬件要求

- **CPU**: 4核心以上
- **内存**: 8GB以上
- **磁盘**: 50GB以上SSD
- **网络**: 稳定的网络连接

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+) / Windows Server 2019+
- **Python**: 3.12+
- **数据库**: PostgreSQL 13+ / SQLite 3+
- **缓存**: Redis 6+
- **容器**: Docker 20.10+ (可选)

## 部署架构

### 生产环境架构

```
┌─────────────────┐
│   Load Balancer  │
│   (Nginx/HAProxy)│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼───┐
│ App 1 │ │ App 2 │
└───┬───┘ └───┬───┘
    │         │
    └────┬────┘
         │
    ┌────▼────┐
    │ Redis   │
    └────┬────┘
         │
    ┌────▼────┐
    │PostgreSQL│
    └─────────┘
```

## 部署方式

### 1. Docker部署

#### 1.1 构建Docker镜像

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 运行迁移
RUN python -m alembic upgrade head

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.2 构建镜像

```bash
docker build -t aiops-sre-agent:latest .
```

#### 1.3 运行容器

```bash
docker run -d \
  --name aiops-sre-agent \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@postgres:5432/aiops \
  -e REDIS_URL=redis://redis:6379 \
  -e AI_API_KEY=your_api_key \
  aiops-sre-agent:latest
```

#### 1.4 Docker Compose部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://aiops:aiops_password@postgres:5432/aiops
      - REDIS_URL=redis://redis:6379
      - AI_API_KEY=${AI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_USER=aiops
      - POSTGRES_PASSWORD=aiops_password
      - POSTGRES_DB=aiops
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6
    command: redis-server --requirepass redis_password
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

启动服务：

```bash
docker-compose up -d
```

### 2. Kubernetes部署

#### 2.1 创建ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aiops-config
data:
  DATABASE_URL: "postgresql://aiops:aiops_password@postgres:5432/aiops"
  REDIS_URL: "redis://redis:6379"
  AI_ENABLED: "true"
```

#### 2.2 创建Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiops-secrets
type: Opaque
stringData:
  AI_API_KEY: "your_api_key"
  JWT_SECRET_KEY: "your_jwt_secret_key"
  SNAPSHOT_ENCRYPTION_KEY: "your_encryption_key"
```

#### 2.3 创建Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-sre-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiops-sre-agent
  template:
    metadata:
      labels:
        app: aiops-sre-agent
    spec:
      containers:
      - name: aiops-sre-agent
        image: aiops-sre-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: aiops-config
              key: DATABASE_URL
        - name: AI_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: AI_API_KEY
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 2.4 创建Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: aiops-sre-agent
spec:
  selector:
    app: aiops-sre-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### 2.5 部署到Kubernetes

```bash
# 应用配置
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# 查看状态
kubectl get pods
kubectl get services
```

### 3. 传统部署

#### 3.1 系统准备

```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装Python 3.12
sudo apt-get install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update -y
sudo apt-get install python3.12 -y

# 安装PostgreSQL
sudo apt-get install postgresql postgresql-contrib -y

# 安装Redis
sudo apt-get install redis-server -y

# 安装Nginx
sudo apt-get install nginx -y
```

#### 3.2 应用部署

```bash
# 创建用户
sudo useradd -m -s /bin/bash aiops
sudo su - aiops

# 克隆代码
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents

# 创建虚拟环境
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 初始化数据库
python -m alembic upgrade head

# 启动应用
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

#### 3.3 Nginx配置

```nginx
# /etc/nginx/sites-available/aiops-sre-agent
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/AIOps-Agents/static;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/aiops-sre-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 数据库配置

### PostgreSQL配置

#### 1. 创建数据库

```sql
CREATE DATABASE aiops;
CREATE USER aiops WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE aiops TO aiops;
```

#### 2. 优化配置

```ini
# postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 16MB
min_wal_size = 1GB
max_wal_size = 4GB
```

#### 3. 备份配置

```bash
# 每日备份
0 2 * * * pg_dump -U aiops aiops > /backup/aiops_$(date +\%Y\%m\%d).sql

# 每周备份
0 3 * * 0 pg_dump -U aiops aiops > /backup/aiops_weekly_$(date +\%Y\%W).sql
```

### Redis配置

#### 1. 安全配置

```ini
# redis.conf
requirepass your_redis_password
bind 127.0.0.1
maxmemory 2gb
maxmemory-policy allkeys-lru
```

#### 2. 持久化配置

```ini
# redis.conf
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfilename "appendonly.aof"
```

## 监控配置

### 应用监控

#### 1. 健康检查端点

```python
# main.py
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

#### 2. 指标端点

```python
# main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### 系统监控

#### 1. Prometheus配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'aiops-sre-agent'
    static_configs:
      - targets: ['localhost:8000']
```

#### 2. Grafana仪表板

导入预配置的仪表板或创建自定义仪表板监控：
- API响应时间
- 数据库连接数
- Redis缓存命中率
- 系统资源使用

## 日志管理

### 日志配置

```python
# config.py
import logging
from loguru import logger

logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)
```

### 日志轮转

```bash
# logrotate配置
/var/log/aiops/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 aiops aiops
}
```

## 安全配置

### 1. 防火墙配置

```bash
# UFW配置
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. SSL/TLS配置

```bash
# 使用Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 3. 安全头配置

```nginx
# Nginx安全头
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

## 备份与恢复

### 数据库备份

```bash
# 备份
pg_dump -U aiops aiops > backup_$(date +%Y%m%d).sql

# 恢复
psql -U aiops aiops < backup_20240827.sql
```

### 文件备份

```bash
# 备份应用数据
tar -czf backup_data_$(date +%Y%m%d).tar.gz /path/to/AIOps-Agents/data

# 恢复
tar -xzf backup_data_20240827.tar.gz -C /
```

## 性能优化

### 1. 应用优化

- 启用Gunicorn多worker模式
- 配置适当的worker数量
- 启用异步处理

### 2. 数据库优化

- 配置连接池
- 优化查询
- 添加适当的索引

### 3. 缓存优化

- 配置Redis缓存
- 实现查询结果缓存
- 使用CDN加速静态资源

## 故障恢复

### 1. 应用故障

```bash
# 重启应用
sudo systemctl restart aiops-sre-agent

# 查看日志
sudo journalctl -u aiops-sre-agent -f
```

### 2. 数据库故障

```bash
# 重启PostgreSQL
sudo systemctl restart postgresql

# 检查数据库状态
sudo -u postgres psql -c "SELECT version();"
```

### 3. 网络故障

```bash
# 检查网络连接
ping google.com

# 检查端口监听
netstat -tlnp | grep 8000
```

## 扩展策略

### 水平扩展

- 增加应用实例数量
- 使用负载均衡分发流量
- 配置自动伸缩策略

### 垂直扩展

- 升级服务器硬件
- 优化数据库配置
- 增加缓存容量

## 更新部署

### 滚动更新

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 运行迁移
python -m alembic upgrade head

# 重启应用
sudo systemctl restart aiops-sre-agent
```

### 蓝绿部署

1. 部署新版本到蓝环境
2. 验证新版本功能
3. 切换流量到蓝环境
4. 部署新版本到绿环境
5. 切换流量到绿环境

## 故障排除

### 常见问题

1. **应用无法启动**
   ```bash
   # 检查日志
   tail -f logs/app.log
   
   # 检查端口占用
   netstat -tlnp | grep 8000
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   sudo systemctl status postgresql
   
   # 测试连接
   psql -U aiops -d aiops
   ```

3. **内存不足**
   ```bash
   # 检查内存使用
   free -h
   
   # 检查进程内存
   ps aux --sort=-%mem | head
   ```

## 支持

如有部署问题，请：
1. 查看部署文档
2. 检查日志文件
3. 联系技术支持团队