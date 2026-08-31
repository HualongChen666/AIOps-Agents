# AIOps SRE Agent 部署指南

## 目录

1. [系统要求](#系统要求)
2. [环境准备](#环境准备)
3. [数据库配置](#数据库配置)
4. [Redis配置](#redis配置)
5. [Qdrant配置](#qdrant配置)
6. [应用配置](#应用配置)
7. [本地部署](#本地部署)
8. [Docker部署](#docker部署)
9. [Kubernetes部署](#kubernetes部署)
10. [生产环境配置](#生产环境配置)
11. [监控和日志](#监控和日志)
12. [故障排除](#故障排除)
13. [备份和恢复](#备份和恢复)
14. [升级指南](#升级指南)
15. [安全配置](#安全配置)

---

## 系统要求

### 硬件要求

#### 最低配置

- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB 可用空间
- **网络**: 100Mbps

#### 推荐配置

- **CPU**: 8核心
- **内存**: 16GB RAM
- **存储**: 200GB SSD
- **网络**: 1Gbps

#### 生产环境配置

- **CPU**: 16核心
- **内存**: 32GB RAM
- **存储**: 500GB SSD
- **网络**: 10Gbps

### 软件要求

#### 操作系统

- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **Windows**: Windows Server 2019+ (开发环境)
- **macOS**: macOS 11+ (开发环境)

#### 依赖软件

- **Python**: 3.8+ (推荐3.10+)
- **PostgreSQL**: 13+
- **Redis**: 6+
- **Qdrant**: 1.6+
- **Docker**: 20.10+ (可选)
- **Kubernetes**: 1.20+ (可选)

---

## 环境准备

### 1. Python环境设置

#### 安装Python 3.10+

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# CentOS/RHEL
sudo yum install python310 python310-pip

# macOS (使用Homebrew)
brew install python@3.10
```

#### 创建虚拟环境

```bash
# 创建项目目录
cd /opt/aiops-agent
mkdir -p aiops-agent
cd aiops-agent

# 创建虚拟环境
python3.10 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 2. 系统依赖安装

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    curl \
    wget
```

#### CentOS/RHEL

```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    postgresql-devel \
    openssl-devel \
    libffi-devel \
    python3-devel \
    git \
    curl \
    wget
```

---

## 数据库配置

### 1. PostgreSQL安装

#### Ubuntu/Debian

```bash
# 添加PostgreSQL仓库
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# 安装PostgreSQL 14
sudo apt install -y postgresql-14 postgresql-contrib-14

# 启动PostgreSQL服务
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### CentOS/RHEL

```bash
# 安装PostgreSQL仓库
sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-$(rpm -E %{rhel})-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 安装PostgreSQL 14
sudo yum install -y postgresql14-server postgresql14-contrib

# 初始化数据库
sudo /usr/pgsql-14/bin/postgresql-14-setup initdb

# 启动PostgreSQL服务
sudo systemctl start postgresql-14
sudo systemctl enable postgresql-14
```

### 2. 数据库配置

#### 创建数据库和用户

```bash
# 切换到postgres用户
sudo -u postgres psql

# 在PostgreSQL命令行中执行以下命令
CREATE DATABASE aiops_agent;
CREATE USER aiops_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE aiops_agent TO aiops_user;
ALTER USER aiops_user CREATEDB;

# 退出PostgreSQL
\q
```

#### 配置PostgreSQL

编辑 `/etc/postgresql/14/main/postgresql.conf`:

```ini
# 连接设置
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB

# 日志设置
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'all'
log_duration = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

编辑 `/etc/postgresql/14/main/pg_hba.conf`:

```ini
# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             10.0.0.0/8              scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
host    all             all             192.168.0.0/16          scram-sha-256
```

重启PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## Redis配置

### 1. Redis安装

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y redis-server
```

#### CentOS/RHEL

```bash
sudo yum install -y redis
```

### 2. Redis配置

编辑 `/etc/redis/redis.conf`:

```ini
# 绑定地址
bind 0.0.0.0

# 端口
port 6379

# 内存设置
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化设置
save 900 1
save 300 10
save 60 10000

# 日志设置
loglevel notice
logfile /var/log/redis/redis-server.log

# 安全设置
requirepass your_redis_password
```

启动Redis服务:

```bash
sudo systemctl start redis
sudo systemctl enable redis
```

---

## Qdrant配置

### 1. Qdrant安装

#### 使用Docker

```bash
docker pull qdrant/qdrant:v1.6.0

# 启动Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.6.0
```

#### 使用Docker Compose

创建 `docker-compose.qdrant.yml`:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:v1.6.0
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
    restart: unless-stopped
```

启动:

```bash
docker-compose -f docker-compose.qdrant.yml up -d
```

### 2. Qdrant配置

创建Qdrant集合:

```bash
curl -X PUT 'http://localhost:6333/collections/aiops_vectors' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "indexing_threshold": 20000
    },
    "replication_factor": 2
  }'
```

---

## 应用配置

### 1. 环境变量配置

创建 `.env` 文件:

```bash
# 应用配置
APP_NAME=aiops-agent
APP_ENV=production
APP_DEBUG=false
APP_URL=http://localhost:8000
APP_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://aiops_user:your_secure_password@localhost:5432/aiops_agent
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_RECYCLE=3600

# Redis配置
REDIS_URL=redis://:your_redis_password@localhost:6379/0
REDIS_CACHE_TTL=3600
REDIS_MAX_CONNECTIONS=50

# Qdrant配置
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=aiops_vectors

# JWT配置
JWT_SECRET_KEY=your_jwt_secret_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 安全配置
SECRET_KEY=your_secret_key_change_this_in_production
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=/var/log/aiops-agent/app.log

# 监控配置
SENTRY_DSN=
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# 插件配置
PLUGIN_DIRECTORY=/opt/aiops-agent/plugins
PLUGIN_ENABLED=true

# 多租户配置
MULTI_TENANT_ENABLED=true
TENANT_ISOLATION_ENABLED=true

# 合规配置
COMPLIANCE_ENABLED=true
AUDIT_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=365
```

### 2. 配置文件验证

创建配置验证脚本 `scripts/validate_config.py`:

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def validate_config():
    """验证配置文件"""
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL',
        'QDRANT_URL',
        'JWT_SECRET_KEY',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"缺少必需的环境变量: {', '.join(missing_vars)}")
        return False
    
    print("配置验证通过")
    return True

if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)
```

---

## 本地部署

### 1. 安装依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库迁移

```bash
# 运行数据库迁移
alembic upgrade head

# 验证迁移
alembic current
```

### 3. 初始化数据

```bash
# 初始化基础数据
python scripts/init_data.py

# 初始化ABAC策略
python scripts/init_abac_policies.py
```

### 4. 启动应用

```bash
# 开发模式启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式启动
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# API文档访问
curl http://localhost:8000/docs
```

---

## Docker部署

### 1. Dockerfile

创建 `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /var/log/aiops-agent

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: aiops-postgres
    environment:
      POSTGRES_DB: aiops_agent
      POSTGRES_USER: aiops_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aiops_user -d aiops_agent"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: aiops-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.6.0
    container_name: aiops-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  app:
    build: .
    container_name: aiops-app
    environment:
      - DATABASE_URL=postgresql://aiops_user:${POSTGRES_PASSWORD}@postgres:5432/aiops_agent
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    volumes:
      - ./logs:/var/log/aiops-agent
      - ./plugins:/opt/aiops-agent/plugins
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

### 3. 构建和启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down

# 停止服务并删除数据
docker-compose down -v
```

---

## Kubernetes部署

### 1. Kubernetes配置文件

#### Namespace

创建 `k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aiops-agent
```

#### ConfigMap

创建 `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aiops-config
  namespace: aiops-agent
data:
  APP_NAME: "aiops-agent"
  APP_ENV: "production"
  APP_DEBUG: "false"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
```

#### Secret

创建 `k8s/secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiops-secrets
  namespace: aiops-agent
type: Opaque
stringData:
  DATABASE_PASSWORD: "your_database_password"
  REDIS_PASSWORD: "your_redis_password"
  JWT_SECRET_KEY: "your_jwt_secret_key"
  SECRET_KEY: "your_secret_key"
```

#### PostgreSQL Deployment

创建 `k8s/postgres-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: aiops-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: aiops_agent
        - name: POSTGRES_USER
          value: aiops_user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: DATABASE_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: aiops-agent
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: aiops-agent
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

#### Redis Deployment

创建 `k8s/redis-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: aiops-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: REDIS_PASSWORD
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: aiops-agent
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: aiops-agent
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

#### Qdrant Deployment

创建 `k8s/qdrant-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
  namespace: aiops-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:v1.6.0
        ports:
        - containerPort: 6333
        - containerPort: 6334
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      volumes:
      - name: qdrant-storage
        persistentVolumeClaim:
          claimName: qdrant-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: aiops-agent
spec:
  selector:
    app: qdrant
  ports:
  - port: 6333
    targetPort: 6333
    name: http
  - port: 6334
    targetPort: 6334
    name: grpc
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: qdrant-pvc
  namespace: aiops-agent
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

#### Application Deployment

创建 `k8s/app-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-app
  namespace: aiops-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiops-app
  template:
    metadata:
      labels:
        app: aiops-app
    spec:
      containers:
      - name: aiops-app
        image: aiops-agent:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: aiops-config
        env:
        - name: DATABASE_URL
          value: "postgresql://aiops_user:$(DATABASE_PASSWORD)@postgres:5432/aiops_agent"
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@redis:6379/0"
        - name: QDRANT_URL
          value: "http://qdrant:6333"
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: DATABASE_PASSWORD
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: REDIS_PASSWORD
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: JWT_SECRET_KEY
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: SECRET_KEY
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
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: aiops-app
  namespace: aiops-agent
spec:
  selector:
    app: aiops-app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiops-app-hpa
  namespace: aiops-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiops-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. 部署到Kubernetes

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 创建配置
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 部署数据库
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/qdrant-deployment.yaml

# 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres -n aiops-agent --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n aiops-agent --timeout=300s
kubectl wait --for=condition=ready pod -l app=qdrant -n aiops-agent --timeout=300s

# 运行数据库迁移
kubectl run -it --rm migration --image=aiops-agent:latest --restart=Never --namespace=aiops-agent -- alembic upgrade head

# 部署应用
kubectl apply -f k8s/app-deployment.yaml

# 查看部署状态
kubectl get pods -n aiops-agent
kubectl get services -n aiops-agent
```

### 3. 查看日志

```bash
# 查看应用日志
kubectl logs -f deployment/aiops-app -n aiops-agent

# 查看特定Pod日志
kubectl logs -f <pod-name> -n aiops-agent
```

---

## 生产环境配置

### 1. 负载均衡器配置

#### Nginx配置

创建 `nginx.conf`:

```nginx
upstream aiops_backend {
    least_conn;
    server app1:8000 weight=5;
    server app2:8000 weight=5;
    server app3:8000 weight=5;
    keepalive 32;
}

server {
    listen 80;
    server_name aiops.example.com;
    
    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name aiops.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # 请求大小限制
    client_max_body_size 10M;
    
    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    location / {
        proxy_pass http://aiops_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /health {
        proxy_pass http://aiops_backend/health;
        access_log off;
    }
    
    location /docs {
        proxy_pass http://aiops_backend/docs;
    }
}
```

### 2. 监控配置

#### Prometheus配置

创建 `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aiops-agent'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

#### Grafana Dashboard

创建Grafana仪表板配置，监控以下指标：

- API响应时间
- 错误率
- 数据库连接池
- Redis缓存命中率
- Qdrant查询性能
- 系统资源使用

### 3. 日志聚合

#### ELK Stack配置

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/aiops-agent/*.log
  fields:
    app: aiops-agent
    environment: production

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "aiops-agent-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"
```

---

## 监控和日志

### 1. 应用监控

#### 健康检查端点

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed
```

#### 性能监控

```bash
# 查看Prometheus指标
curl http://localhost:9090/metrics

# 查看应用状态
curl http://localhost:8000/metrics
```

### 2. 日志管理

#### 日志级别

- **DEBUG**: 详细调试信息
- **INFO**: 一般信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

#### 日志轮转

配置 `/etc/logrotate.d/aiops-agent`:

```
/var/log/aiops-agent/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 aiops aiops
    postrotate
        systemctl reload aiops-agent > /dev/null 2>&1 || true
    endscript
}
```

---

## 故障排除

### 1. 常见问题

#### 数据库连接失败

**症状**: 应用无法连接到数据库

**解决方案**:

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 检查连接
psql -U aiops_user -d aiops_agent -h localhost

# 检查防火墙
sudo ufw status
sudo ufw allow 5432/tcp
```

#### Redis连接失败

**症状**: 应用无法连接到Redis

**解决方案**:

```bash
# 检查Redis状态
sudo systemctl status redis

# 测试连接
redis-cli -a your_password ping

# 检查配置
redis-cli CONFIG GET bind
```

#### 内存不足

**症状**: 应用OOM killed

**解决方案**:

```bash
# 检查内存使用
free -h

# 增加swap空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 调整应用内存限制
# 在Kubernetes中更新resources.limits.memory
```

### 2. 调试模式

启用调试模式:

```bash
# 设置环境变量
export APP_DEBUG=true

# 启动应用
uvicorn main:app --reload --log-level debug
```

---

## 备份和恢复

### 1. 数据库备份

#### 手动备份

```bash
# 备份数据库
pg_dump -U aiops_user -d aiops_agent > backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份
gzip backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 自动备份脚本

创建 `scripts/backup_db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aiops_agent_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

pg_dump -U aiops_user -d aiops_agent | gzip > $BACKUP_FILE

# 保留最近7天的备份
find $BACKUP_DIR -name "aiops_agent_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

添加到crontab:

```bash
# 每天凌晨2点备份
0 2 * * * /path/to/scripts/backup_db.sh
```

### 2. 数据恢复

```bash
# 解压备份
gunzip backup_20240101_020000.sql.gz

# 恢复数据库
psql -U aiops_user -d aiops_agent < backup_20240101_020000.sql
```

### 3. Redis备份

```bash
# 手动备份
redis-cli --rdb /backups/redis/dump_$(date +%Y%m%d_%H%M%S).rdb

# 自动备份脚本
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backups/redis/dump_$(date +%Y%m%d_%H%M%S).rdb
```

---

## 升级指南

### 1. 升级前准备

```bash
# 1. 备份数据库
./scripts/backup_db.sh

# 2. 备份配置文件
cp .env .env.backup

# 3. 记录当前版本
git log -1 > version_backup.txt
```

### 2. 升级步骤

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 更新依赖
pip install -r requirements.txt --upgrade

# 3. 运行数据库迁移
alembic upgrade head

# 4. 重启应用
sudo systemctl restart aiops-agent

# 5. 验证升级
curl http://localhost:8000/health
```

### 3. 回滚步骤

```bash
# 1. 停止应用
sudo systemctl stop aiops-agent

# 2. 恢复代码
git checkout <previous_commit>

# 3. 恢复依赖
pip install -r requirements.txt

# 4. 回滚数据库
alembic downgrade <target_version>

# 5. 重启应用
sudo systemctl start aiops-agent
```

---

## 安全配置

### 1. 防火墙配置

```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # Application
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 2. SSL/TLS配置

生成自签名证书（开发环境）:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

使用Let's Encrypt（生产环境）:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d aiops.example.com
```

### 3. 访问控制

配置IP白名单:

```python
# 在应用配置中添加
ALLOWED_IPS = ["192.168.1.0/24", "10.0.0.0/8"]
```

---

## 附录

### A. 环境变量参考

完整的环境变量列表和说明。

### B. 配置文件模板

各种配置文件的完整模板。

### C. 故障排除清单

常见问题和解决方案的快速参考。

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31
