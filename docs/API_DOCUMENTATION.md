# API Documentation
API文档

## 概述

AIOps SRE Agent提供RESTful API，支持业务影响分析、混沌工程、AI功能、插件市场等功能。

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **响应格式**: JSON
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```

## 业务影响分析API

### 获取分析列表

**GET** `/business-impact/analysis`

**查询参数**:
- `service_name` (string, optional): 按服务名称筛选
- `status` (string, optional): 按状态筛选 (pending, running, completed, failed)
- `limit` (integer, optional): 返回数量限制 (1-100, 默认20)
- `offset` (integer, optional): 偏移量 (默认0)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "BIA-001",
        "service_name": "user-service",
        "analysis_type": "full",
        "status": "completed",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 100,
    "limit": 20,
    "offset": 0
  }
}
```

### 创建分析

**POST** `/business-impact/analysis`

**请求体**:
```json
{
  "service_name": "user-service",
  "analysis_type": "full",
  "time_range": "1h",
  "include_dependencies": true,
  "include_ux_metrics": true
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": "BIA-002",
    "service_name": "user-service",
    "status": "running"
  },
  "message": "分析创建成功"
}
```

## 混沌工程API

### 获取实验列表

**GET** `/chaos/experiments`

**查询参数**:
- `status` (string, optional): 按状态筛选
- `severity` (string, optional): 按严重程度筛选
- `limit` (integer, optional): 返回数量限制
- `offset` (integer, optional): 偏移量

**响应示例**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "CHAOS-001",
        "name": "Network Latency Test",
        "experiment_type": "network_latency",
        "severity": "medium",
        "status": "completed"
      }
    ],
    "total": 50,
    "limit": 20,
    "offset": 0
  }
}
```

### 创建实验

**POST** `/chaos/experiments`

**请求体**:
```json
{
  "name": "Network Latency Test",
  "experiment_type": "network_latency",
  "parameters": {
    "latency_ms": 100,
    "duration": 60
  },
  "severity": "medium"
}
```

## AI功能API

### 获取微调任务列表

**GET** `/ai/fine-tuning-jobs`

**响应示例**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "FT-001",
        "model_name": "gpt-3.5-turbo",
        "status": "completed",
        "progress": 100.0
      }
    ]
  }
}
```

### 创建微调任务

**POST** `/ai/fine-tuning-jobs`

**请求体**:
```json
{
  "base_model": "gpt-3.5-turbo",
  "model_name": "custom-model",
  "dataset": "training-data"
}
```

## 插件市场API

### 获取插件列表

**GET** `/plugin-marketplace/plugins`

**查询参数**:
- `category` (string, optional): 按分类筛选
- `quality` (string, optional): 按质量筛选
- `enabled` (boolean, optional): 按启用状态筛选
- `limit` (integer, optional): 返回数量限制
- `offset` (integer, optional): 偏移量

**响应示例**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "PLUGIN-001",
        "plugin_id": "monitoring-plugin",
        "plugin_name": "Advanced Monitoring",
        "version": "1.0.0",
        "description": "Advanced monitoring plugin",
        "author": "DevOps Team",
        "category": "monitoring",
        "quality": "verified",
        "download_count": 1000,
        "rating": 4.5,
        "enabled": true
      }
    ],
    "total": 25,
    "limit": 20,
    "offset": 0
  }
}
```

### 上传插件

**POST** `/plugin-marketplace/plugins`

**请求体**:
```json
{
  "plugin_id": "new-plugin",
  "plugin_name": "New Plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "author": "Author Name",
  "category": "general",
  "download_url": "https://example.com/plugin.zip"
}
```

### 安装插件

**POST** `/plugin-marketplace/plugins/{plugin_id}/install`

**请求体**:
```json
{
  "installed_version": "1.0.0",
  "configuration": {
    "setting1": "value1"
  }
}
```

## 权限管理

### 权限枚举

- `read`: 读取权限
- `write`: 写入权限
- `delete`: 删除权限
- `business_impact:read`: 业务影响分析读取
- `business_impact:write`: 业务影响分析写入
- `chaos:execute`: 混沌实验执行
- `ai:train`: AI模型训练
- `plugin:upload`: 插件上传
- `plugin:install`: 插件安装

### 角色枚举

- `admin`: 管理员 (所有权限)
- `operator`: 运维人员 (运维相关权限)
- `developer`: 开发人员 (开发相关权限)
- `viewer`: 查看者 (只读权限)
- `guest`: 访客 (基础读取权限)

## 错误码

| 错误码 | 描述 |
|--------|------|
| VALIDATION_ERROR | 请求参数验证失败 |
| NOT_FOUND | 资源不存在 |
| INTERNAL_ERROR | 服务器内部错误 |
| AUTHENTICATION_ERROR | 认证失败 |
| AUTHORIZATION_ERROR | 权限不足 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 |

## 速率限制

- 默认限制: 100请求/分钟
- 认证用户: 200请求/分钟
- 管理员: 无限制

## 缓存策略

- 列表查询: 5分钟TTL
- 详情查询: 10分钟TTL
- 统计数据: 1小时TTL
- 数据更新时自动失效相关缓存

## Webhook

### 配置Webhook

**POST** `/webhooks`

**请求体**:
```json
{
  "url": "https://your-webhook-url.com",
  "events": ["analysis.completed", "experiment.started"],
  "secret": "webhook_secret"
}
```

## 限流

API实现了基于令牌桶的限流算法：
- 令牌桶大小: 100
- 令牌生成速率: 1令牌/秒
- 突发流量: 允许短时间内超过限制

## 版本控制

API版本通过URL路径指定：
- 当前版本: `/api/v1`
- 向后兼容: 保持旧版本至少6个月