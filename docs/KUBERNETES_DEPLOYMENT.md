# Kubernetes部署指南

## 目录

1. [Kubernetes基础](#kubernetes基础)
2. [集群准备](#集群准备)
3. [应用容器化](#应用容器化)
4. [Kubernetes配置](#kubernetes配置)
5. [部署流程](#部署流程)
6. [服务暴露](#服务暴露)
7. [配置管理](#配置管理)
8. [存储管理](#存储管理)
9. [自动扩缩容](#自动扩缩容)
10. [监控和日志](#监控和日志)
11. [故障排除](#故障排除)
12. [备份和恢复](#备份和恢复)
13. [安全配置](#安全配置)

---

## Kubernetes基础

### 1. Kubernetes架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Master     │  │   Master     │  │   Master     │      │
│  │  (Control)   │  │  (Control)   │  │  (Control)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                 │                 │
│         └─────────────────┴─────────────────┘                 │
│                           │                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    Worker Nodes                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │  │
│  │  │  Node 1  │  │  Node 2  │  │  Node 3  │          │  │
│  │  │          │  │          │  │          │          │  │
│  │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │          │  │
│  │  │ │Pod 1 │ │  │ │Pod 2 │ │  │ │Pod 3 │ │          │  │
│  │  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │          │  │
│  │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │          │  │
│  │  │ │Pod 4 │ │  │ │Pod 5 │ │  │ ┌──────┐ │          │  │
│  │  │ └──────┘ │  │ └──────┘ │  │ │Pod 6 │ │          │  │
│  │  └──────────┘  └──────────┘  │ └──────┘ │          │  │
│  │                               └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2. 核心概念

- **Pod**: Kubernetes中最小的部署单元
- **Deployment**: 管理Pod的副本和更新
- **Service**: 为Pod提供稳定的网络访问
- **ConfigMap**: 存储配置数据
- **Secret**: 存储敏感信息
- **PersistentVolume**: 持久化存储
- **Namespace**: 资源隔离

---

## 集群准备

### 1. 安装kubectl

```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# macOS
brew install kubectl

# 验证安装
kubectl version --client
```

### 2. 配置kubeconfig

```bash
# 复制kubeconfig文件
mkdir -p ~/.kube
cp /path/to/kubeconfig ~/.kube/config

# 验证连接
kubectl cluster-info
kubectl get nodes
```

### 3. 创建命名空间

```bash
# 创建命名空间
kubectl create namespace aiops-agent

# 设置默认命名空间
kubectl config set-context --current --namespace=aiops-agent
```

---

## 应用容器化

### 1. 构建镜像

```bash
# 构建Docker镜像
docker build -t aiops-agent:v1.0.0 .

# 标记镜像用于推送到仓库
docker tag aiops-agent:v1.0.0 registry.example.com/aiops-agent:v1.0.0

# 推送镜像
docker push registry.example.com/aiops-agent:v1.0.0
```

### 2. 镜像拉取凭证

```bash
# 创建Docker registry secret
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=username \
  --docker-password=password \
  --docker-email=email@example.com \
  -n aiops-agent
```

---

## Kubernetes配置

### 1. Namespace配置

创建 `k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aiops-agent
  labels:
    name: aiops-agent
    environment: production
```

### 2. ConfigMap配置

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
  APP_PORT: "8000"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  DATABASE_POOL_SIZE: "20"
  DATABASE_MAX_OVERFLOW: "10"
  REDIS_CACHE_TTL: "3600"
  QDRANT_COLLECTION_NAME: "aiops_vectors"
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: "30"
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: "7"
  MULTI_TENANT_ENABLED: "true"
  TENANT_ISOLATION_ENABLED: "true"
  COMPLIANCE_ENABLED: "true"
  AUDIT_LOG_ENABLED: "true"
  AUDIT_LOG_RETENTION_DAYS: "365"
  PROMETHEUS_ENABLED: "true"
  PROMETHEUS_PORT: "9090"
  PLUGIN_ENABLED: "true"
```

### 3. Secret配置

创建 `k8s/secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiops-secrets
  namespace: aiops-agent
type: Opaque
stringData:
  DATABASE_PASSWORD: "your_secure_database_password"
  REDIS_PASSWORD: "your_secure_redis_password"
  JWT_SECRET_KEY: "your_jwt_secret_key_change_this_in_production"
  SECRET_KEY: "your_secret_key_change_this_in_production"
  QDRANT_API_KEY: "your_qdrant_api_key_if_required"
  SENTRY_DSN: "your_sentry_dsn_if_required"
```

### 4. PostgreSQL配置

创建 `k8s/postgres-statefulset.yaml`:

```yaml
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
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: aiops-agent
spec:
  serviceName: postgres
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
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
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
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - aiops_user
            - -d
            - aiops_agent
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - aiops_user
            - -d
            - aiops_agent
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### 5. Redis配置

创建 `k8s/redis-statefulset.yaml`:

```yaml
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
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: aiops-agent
spec:
  serviceName: redis
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
        - --maxmemory
        - 2gb
        - --maxmemory-policy
        - allkeys-lru
        - --appendonly
        - yes
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
        livenessProbe:
          exec:
            command:
            - redis-cli
            - -a
            - $(REDIS_PASSWORD)
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          exec:
            command:
            - redis-cli
            - -a
            - $(REDIS_PASSWORD)
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
  volumeClaimTemplates:
  - metadata:
      name: redis-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
```

### 6. Qdrant配置

创建 `k8s/qdrant-statefulset.yaml`:

```yaml
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
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: aiops-agent
spec:
  serviceName: qdrant
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
          name: http
        - containerPort: 6334
          name: grpc
        env:
        - name: QDRANT__SERVICE__GRPC_PORT
          value: "6334"
        - name: QDRANT__LOG_LEVEL
          value: "INFO"
        - name: QDRANT__STORAGE__OPTIMIZERS__INDEXING_THRESHOLD
          value: "20000"
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
        livenessProbe:
          httpGet:
            path: /health
            port: 6333
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 6333
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
  volumeClaimTemplates:
  - metadata:
      name: qdrant-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
```

### 7. 应用配置

创建 `k8s/app-deployment.yaml`:

```yaml
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
    name: http
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-app
  namespace: aiops-agent
  labels:
    app: aiops-app
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiops-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: aiops-app
        version: v1.0.0
    spec:
      imagePullSecrets:
      - name: regcred
      containers:
      - name: aiops-app
        image: registry.example.com/aiops-agent:v1.0.0
        ports:
        - containerPort: 8000
          name: http
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
        - name: QDRANT_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: QDRANT_API_KEY
          optional: true
        - name: SENTRY_DSN
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: SENTRY_DSN
          optional: true
        volumeMounts:
        - name: logs
          mountPath: /var/log/aiops-agent
        - name: plugins
          mountPath: /opt/aiops-agent/plugins
        - name: data
          mountPath: /app/data
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
      volumes:
      - name: logs
        emptyDir: {}
      - name: plugins
        persistentVolumeClaim:
          claimName: plugins-pvc
      - name: data
        persistentVolumeClaim:
          claimName: data-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: plugins-pvc
  namespace: aiops-agent
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
  namespace: aiops-agent
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
```

### 8. Ingress配置

创建 `k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aiops-ingress
  namespace: aiops-agent
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - aiops.example.com
    secretName: aiops-tls
  rules:
  - host: aiops.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: aiops-app
            port:
              number: 80
      - path: /health
        pathType: Prefix
        backend:
          service:
            name: aiops-app
            port:
              number: 80
```

### 9. HPA配置

创建 `k8s/hpa.yaml`:

```yaml
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
```

---

## 部署流程

### 1. 部署顺序

```bash
# 1. 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 2. 创建配置
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 3. 部署数据库
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml
kubectl apply -f k8s/qdrant-statefulset.yaml

# 4. 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres -n aiops-agent --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n aiops-agent --timeout=300s
kubectl wait --for=condition=ready pod -l app=qdrant -n aiops-agent --timeout=300s

# 5. 运行数据库迁移
kubectl run -it --rm migration \
  --image=registry.example.com/aiops-agent:v1.0.0 \
  --restart=Never \
  --namespace=aiops-agent \
  --env="DATABASE_URL=postgresql://aiops_user:$(kubectl get secret aiops-secrets -n aiops-agent -o jsonpath='{.data.DATABASE_PASSWORD}' | base64 -d)@postgres:5432/aiops_agent" \
  -- alembic upgrade head

# 6. 部署应用
kubectl apply -f k8s/app-deployment.yaml

# 7. 部署Ingress
kubectl apply -f k8s/ingress.yaml

# 8. 配置自动扩缩容
kubectl apply -f k8s/hpa.yaml

# 9. 验证部署
kubectl get pods -n aiops-agent
kubectl get services -n aiops-agent
kubectl get ingress -n aiops-agent
```

### 2. 部署脚本

创建 `scripts/deploy-k8s.sh`:

```bash
#!/bin/bash
set -e

NAMESPACE="aiops-agent"
REGISTRY="registry.example.com"
IMAGE_TAG="v1.0.0"

echo "开始部署到Kubernetes..."

# 创建命名空间
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 应用配置
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 部署数据库
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml
kubectl apply -f k8s/qdrant-statefulset.yaml

# 等待数据库就绪
echo "等待数据库就绪..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=qdrant -n $NAMESPACE --timeout=300s

# 运行数据库迁移
echo "运行数据库迁移..."
kubectl run -it --rm migration \
  --image=$REGISTRY/aiops-agent:$IMAGE_TAG \
  --restart=Never \
  --namespace=$NAMESPACE \
  --env="DATABASE_URL=postgresql://aiops_user:$(kubectl get secret aiops-secrets -n $NAMESPACE -o jsonpath='{.data.DATABASE_PASSWORD}' | base64 -d)@postgres:5432/aiops_agent" \
  -- alembic upgrade head

# 部署应用
echo "部署应用..."
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# 等待应用就绪
echo "等待应用就绪..."
kubectl wait --for=condition=ready pod -l app=aiops-app -n $NAMESPACE --timeout=300s

# 验证部署
echo "验证部署..."
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get ingress -n $NAMESPACE

echo "部署完成！"
```

---

## 服务暴露

### 1. Service类型

#### ClusterIP (集群内部访问)

```yaml
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
  type: ClusterIP
```

#### NodePort (节点端口访问)

```yaml
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
    nodePort: 30080
  type: NodePort
```

#### LoadBalancer (外部负载均衡器)

```yaml
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
```

### 2. Ingress配置

见上面的 `k8s/ingress.yaml` 配置。

---

## 配置管理

### 1. ConfigMap使用

```yaml
envFrom:
- configMapRef:
    name: aiops-config
```

### 2. Secret使用

```yaml
env:
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: aiops-secrets
      key: DATABASE_PASSWORD
```

### 3. 配置热更新

```bash
# 更新ConfigMap
kubectl edit configmap aiops-config -n aiops-agent

# 重启Pod以应用新配置
kubectl rollout restart deployment aiops-app -n aiops-agent
```

---

## 存储管理

### 1. PersistentVolume

创建 `k8s/pv.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgres-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: manual
  hostPath:
    path: /mnt/data/postgres
```

### 2. StorageClass

创建 `k8s/storageclass.yaml`:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  iopsPerGB: "10"
allowVolumeExpansion: true
```

---

## 自动扩缩容

### 1. HPA配置

见上面的 `k8s/hpa.yaml` 配置。

### 2. VPA配置

创建 `k8s/vpa.yaml`:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: aiops-app-vpa
  namespace: aiops-agent
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiops-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: aiops-app
      minAllowed:
        cpu: 100m
        memory: 256Mi
      maxAllowed:
        cpu: 2000m
        memory: 2Gi
      controlledResources: ["cpu", "memory"]
```

---

## 监控和日志

### 1. Prometheus配置

创建 `k8s/prometheus-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: aiops-agent
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
    - job_name: 'aiops-agent'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - aiops-agent
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_node_name]
        action: replace
        target_label: node
```

### 2. Grafana配置

创建 `k8s/grafana-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: aiops-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_USER
          value: admin
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: GRAFANA_ADMIN_PASSWORD
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
      volumes:
      - name: grafana-storage
        persistentVolumeClaim:
          claimName: grafana-pvc
```

### 3. 日志聚合

创建 `k8s/fluentd-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: aiops-agent
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/aiops-agent/*.log
      pos_file /var/log/fluentd-aiops.log.pos
      tag aiops.*
      read_from_head true
    </source>

    <match aiops.**>
      @type elasticsearch
      host elasticsearch
      port 9200
      logstash_format true
      logstash_prefix aiops
    </match>
```

---

## 故障排除

### 1. Pod状态检查

```bash
# 查看Pod状态
kubectl get pods -n aiops-agent

# 查看Pod详细信息
kubectl describe pod <pod-name> -n aiops-agent

# 查看Pod日志
kubectl logs <pod-name> -n aiops-agent

# 查看Pod事件
kubectl get events -n aiops-agent --sort-by='.lastTimestamp'
```

### 2. 常见问题

#### CrashLoopBackOff

```bash
# 查看Pod日志
kubectl logs <pod-name> -n aiops-agent --previous

# 检查资源限制
kubectl describe pod <pod-name> -n aiops-agent

# 检查镜像拉取
kubectl describe pod <pod-name> -n aiops-agent | grep Image
```

#### ImagePullBackOff

```bash
# 检查镜像拉取凭证
kubectl get secret regcred -n aiops-agent -o yaml

# 手动拉取镜像测试
docker pull registry.example.com/aiops-agent:v1.0.0
```

#### Pending状态

```bash
# 检查调度问题
kubectl describe pod <pod-name> -n aiops-agent

# 检查资源配额
kubectl describe quota -n aiops-agent

# 检查节点资源
kubectl describe nodes
```

---

## 备份和恢复

### 1. 数据库备份

```bash
# 从Pod中备份数据库
kubectl exec -it postgres-0 -n aiops-agent -- pg_dump -U aiops_user aiops_agent > backup.sql

# 备份到外部存储
kubectl cp aiops-agent/postgres-0:/backup.sql ./backup_$(date +%Y%m%d).sql
```

### 2. 数据恢复

```bash
# 恢复数据库
kubectl cp ./backup.sql aiops-agent/postgres-0:/backup.sql
kubectl exec -it postgres-0 -n aiops-agent -- psql -U aiops_user aiops_agent < /backup.sql
```

### 3. etcd备份

```bash
# 备份etcd
ETCDCTL_API=3 etcdctl snapshot save snapshot.db

# 恢复etcd
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db
```

---

## 安全配置

### 1. Pod安全策略

创建 `k8s/pod-security-policy.yaml`:

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
  namespace: aiops-agent
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'MustRunAs'
    ranges:
    - min: 1
      max: 65535
```

### 2. Network策略

创建 `k8s/network-policy.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aiops-network-policy
  namespace: aiops-agent
spec:
  podSelector:
    matchLabels:
      app: aiops-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: aiops-agent
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
    - protocol: TCP
      port: 6333
```

---

## 附录

### A. kubectl命令速查

```bash
# 集群管理
kubectl cluster-info
kubectl get nodes
kubectl top nodes

# 命名空间
kubectl get namespaces
kubectl create namespace <name>
kubectl config set-context --current --namespace=<name>

# Pod管理
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
kubectl exec -it <pod-name> -n <namespace> -- bash
kubectl delete pod <pod-name> -n <namespace>

# Deployment管理
kubectl get deployments -n <namespace>
kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout restart deployment/<name> -n <namespace>
kubectl scale deployment/<name> --replicas=3 -n <namespace>

# Service管理
kubectl get services -n <namespace>
kubectl describe service <name> -n <namespace>

# ConfigMap管理
kubectl get configmaps -n <namespace>
kubectl describe configmap <name> -n <namespace>
kubectl edit configmap <name> -n <namespace>

# Secret管理
kubectl get secrets -n <namespace>
kubectl describe secret <name> -n <namespace>
kubectl create secret generic <name> --from-literal=key=value -n <namespace>

# 存储管理
kubectl get pv
kubectl get pvc -n <namespace>
kubectl describe pv <name>
kubectl describe pvc <name> -n <namespace>
```

### B. 最佳实践

1. 使用命名空间隔离不同环境
2. 使用ConfigMap和Secret管理配置
3. 设置资源限制防止资源耗尽
4. 配置健康检查确保Pod健康
5. 使用HPA实现自动扩缩容
6. 使用NetworkPolicy实现网络隔离
7. 定期备份etcd和重要数据
8. 监控集群和应用性能
9. 使用RBAC控制访问权限
10. 定期更新Kubernetes版本

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31