# APM仪表板文档

## 概述

本文档描述了AIOps SRE Agent的APM（Application Performance Monitoring）仪表板配置，包括仪表板设计、配置和最佳实践。

---

## 仪表板架构

### 仪表板层次结构

```
┌─────────────────────────────────────────────────────────┐
│                  APM Dashboard System                    │
├─────────────────────────────────────────────────────────┤
│  Overview Dashboard (总览仪表板)                        │
│  ├── System Health (系统健康)                          │
│  ├── Performance Overview (性能概览)                    │
│  ├── Alert Summary (告警摘要)                          │
│  └── Resource Usage (资源使用)                          │
├─────────────────────────────────────────────────────────┤
│  Performance Dashboards (性能仪表板)                     │
│  ├── API Performance (API性能)                         │
│  ├── Database Performance (数据库性能)                 │
│  ├── Cache Performance (缓存性能)                       │
│  └── Queue Performance (队列性能)                      │
├─────────────────────────────────────────────────────────┤
│  Business Dashboards (业务仪表板)                       │
│  ├── Alert Processing (告警处理)                        │
│  ├── Repair Execution (修复执行)                        │
│  ├── AI Analysis (AI分析)                              │
│  └── User Activity (用户活动)                           │
├─────────────────────────────────────────────────────────┤
│  Infrastructure Dashboards (基础设施仪表板)               │
│  ├── Server Metrics (服务器指标)                        │
│  ├── Network Metrics (网络指标)                        │
│  ├── Storage Metrics (存储指标)                        │
│  └── Container Metrics (容器指标)                      │
└─────────────────────────────────────────────────────────┘
```

---

## 仪表板列表

### 1. 系统总览仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "System Overview",
    "uid": "system-overview",
    "tags": ["overview", "system"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Health Score",
        "type": "stat",
        "targets": [
          {
            "expr": "system_health_score",
            "legendFormat": "{{value}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Active Alerts",
        "type": "stat",
        "targets": [
          {
            "expr": "active_alerts_total",
            "legendFormat": "{{value}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Active Repairs",
        "type": "stat",
        "targets": [
          {
            "expr": "active_repairs",
            "legendFormat": "{{value}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_cpu_usage",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_memory_usage",
            "legendFormat": "{{instance}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 系统健康评分
- 活跃告警数量
- 活跃修复数量
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络I/O

### 2. API性能仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "API Performance",
    "uid": "api-performance",
    "tags": ["performance", "api"],
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds)",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Request Duration Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_bucket[5m])",
            "legendFormat": "{{le}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 请求速率
- 响应时间（P50, P95, P99）
- 错误率
- 请求持续时间分布
- 端点性能对比

### 3. 数据库性能仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Database Performance",
    "uid": "database-performance",
    "tags": ["performance", "database"],
    "panels": [
      {
        "id": 1,
        "title": "Query Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(pg_stat_statements_calls_total[5m])",
            "legendFormat": "{{query}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Query Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, pg_stat_statements_mean_time)",
            "legendFormat": "{{query}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Connection Pool",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_activity_count",
            "legendFormat": "{{state}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Cache Hit Ratio",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)",
            "legendFormat": "{{database}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 查询速率
- 查询持续时间
- 连接池使用情况
- 缓存命中率
- 锁等待时间
- 死锁数量

### 4. 缓存性能仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Cache Performance",
    "uid": "cache-performance",
    "tags": ["performance", "cache"],
    "panels": [
      {
        "id": 1,
        "title": "Cache Hit Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))",
            "legendFormat": "{{cache}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Cache Size",
        "type": "graph",
        "targets": [
          {
            "expr": "cache_size_bytes",
            "legendFormat": "{{cache}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Eviction Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(cache_evictions_total[5m])",
            "legendFormat": "{{cache}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, cache_response_time)",
            "legendFormat": "{{cache}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 缓存命中率
- 缓存大小
- 驱逐速率
- 响应时间
- 内存使用
- 键空间使用

### 5. 队列性能仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Queue Performance",
    "uid": "queue-performance",
    "tags": ["performance", "queue"],
    "panels": [
      {
        "id": 1,
        "title": "Queue Size",
        "type": "graph",
        "targets": [
          {
            "expr": "queue_size",
            "legendFormat": "{{queue}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(queue_processed_total[5m])",
            "legendFormat": "{{queue}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, queue_processing_time)",
            "legendFormat": "{{queue}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(queue_errors_total[5m])",
            "legendFormat": "{{queue}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 队列大小
- 处理速率
- 处理时间
- 错误率
- 重试次数
- 死信队列大小

### 6. 告警处理仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Alert Processing",
    "uid": "alert-processing",
    "tags": ["business", "alerts"],
    "panels": [
      {
        "id": 1,
        "title": "Alerts by Severity",
        "type": "piechart",
        "targets": [
          {
            "expr": "alerts_total",
            "legendFormat": "{{severity}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Alert Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, alert_processing_duration)",
            "legendFormat": "{{severity}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Alert Trends",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(alerts_total[1h])",
            "legendFormat": "{{severity}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Alert Resolution Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "alerts_resolved_total / alerts_total",
            "legendFormat": "{{value}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 按严重程度分类的告警数量
- 告警处理时间
- 告警趋势
- 告警解决率
- 平均解决时间
- 告警重复率

### 7. 修复执行仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Repair Execution",
    "uid": "repair-execution",
    "tags": ["business", "repairs"],
    "panels": [
      {
        "id": 1,
        "title": "Repairs by Type",
        "type": "piechart",
        "targets": [
          {
            "expr": "repairs_total",
            "legendFormat": "{{repair_type}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Repair Execution Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, repair_execution_duration)",
            "legendFormat": "{{repair_type}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Repair Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "repairs_successful_total / repairs_total",
            "legendFormat": "{{value}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Repair Trends",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(repairs_total[1h])",
            "legendFormat": "{{repair_type}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 按类型分类的修复数量
- 修复执行时间
- 修复成功率
- 修复趋势
- 平均修复时间
- 修复失败原因

### 8. AI分析仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "AI Analysis",
    "uid": "ai-analysis",
    "tags": ["business", "ai"],
    "panels": [
      {
        "id": 1,
        "title": "AI Analysis Requests",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(ai_analysis_requests_total[5m])",
            "legendFormat": "{{analysis_type}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "AI Analysis Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, ai_analysis_duration)",
            "legendFormat": "{{analysis_type}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "AI Model Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "ai_model_accuracy",
            "legendFormat": "{{model}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(ai_tokens_used_total[5m])",
            "legendFormat": "{{model}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- AI分析请求数量
- AI分析持续时间
- AI模型准确率
- Token使用量
- API调用成本
- 模型响应时间

### 9. 用户活动仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "User Activity",
    "uid": "user-activity",
    "tags": ["business", "users"],
    "panels": [
      {
        "id": 1,
        "title": "Active Users",
        "type": "graph",
        "targets": [
          {
            "expr": "active_users",
            "legendFormat": "{{user_type}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "User Sessions",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(user_sessions_total[5m])",
            "legendFormat": "{{user_type}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "User Actions",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(user_actions_total[5m])",
            "legendFormat": "{{action}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Session Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, session_duration)",
            "legendFormat": "{{user_type}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 活跃用户数量
- 用户会话数量
- 用户操作数量
- 会话持续时间
- 用户留存率
- 用户转化率

### 10. 服务器指标仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Server Metrics",
    "uid": "server-metrics",
    "tags": ["infrastructure", "server"],
    "panels": [
      {
        "id": 1,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_cpu_usage",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_memory_usage",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Disk I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(disk_io_bytes[5m])",
            "legendFormat": "{{instance}} {{device}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Network I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(network_io_bytes[5m])",
            "legendFormat": "{{instance}} {{interface}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- CPU使用率
- 内存使用率
- 磁盘I/O
- 网络I/O
- 系统负载
- 进程数量

### 11. 网络指标仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Network Metrics",
    "uid": "network-metrics",
    "tags": ["infrastructure", "network"],
    "panels": [
      {
        "id": 1,
        "title": "Network Traffic",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(network_bytes_total[5m])",
            "legendFormat": "{{interface}} {{direction}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Network Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "network_latency_seconds",
            "legendFormat": "{{target}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Packet Loss",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(network_packets_dropped[5m])",
            "legendFormat": "{{interface}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Connection Count",
        "type": "graph",
        "targets": [
          {
            "expr": "network_connections",
            "legendFormat": "{{state}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 网络流量
- 网络延迟
- 丢包率
- 连接数量
- 带宽使用率
- 错误率

### 12. 容器指标仪表板

#### 仪表板配置
```json
{
  "dashboard": {
    "title": "Container Metrics",
    "uid": "container-metrics",
    "tags": ["infrastructure", "container"],
    "panels": [
      {
        "id": 1,
        "title": "Container CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_cpu_usage",
            "legendFormat": "{{container}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Container Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage",
            "legendFormat": "{{container}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Container Network I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_network_io_bytes[5m])",
            "legendFormat": "{{container}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Container Restarts",
        "type": "graph",
        "targets": [
          {
            "expr": "container_restarts_total",
            "legendFormat": "{{container}}"
          }
        ]
      }
    ]
  }
}
```

#### 关键指标
- 容器CPU使用率
- 容器内存使用率
- 容器网络I/O
- 容器重启次数
- 容器状态
- 资源限制

---

## 仪表板配置文件

### Grafana Provisioning

#### 数据源配置
```yaml
# grafana/provisioning/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

#### 仪表板配置
```yaml
# grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1

providers:
  - name: 'APM Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

---

## 仪表板最佳实践

### 1. 仪表板设计
- 使用清晰的标题和描述
- 合理组织面板布局
- 使用一致的配色方案
- 提供时间范围选择器

### 2. 指标选择
- 选择关键性能指标
- 避免指标过载
- 使用相关的指标组合
- 提供上下文信息

### 3. 可视化类型
- 使用合适的图表类型
- 避免过度复杂的可视化
- 使用颜色传达信息
- 提供交互功能

### 4. 告警集成
- 设置合理的告警阈值
- 提供告警通知
- 记录告警历史
- 提供告警恢复通知

---

## 仪表板导入

### 导入脚本
```python
# scripts/import_dashboards.py
import requests
import json

def import_dashboard(dashboard_json, grafana_url, api_key):
    """导入Grafana仪表板"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{grafana_url}/api/dashboards/db",
        headers=headers,
        json=dashboard_json
    )
    
    if response.status_code == 200:
        print(f"Dashboard imported successfully: {response.json()['uid']}")
    else:
        print(f"Failed to import dashboard: {response.text}")

if __name__ == "__main__":
    # 导入所有仪表板
    dashboards = [
        "system-overview.json",
        "api-performance.json",
        "database-performance.json",
        "cache-performance.json",
        "queue-performance.json",
        "alert-processing.json",
        "repair-execution.json",
        "ai-analysis.json",
        "user-activity.json",
        "server-metrics.json",
        "network-metrics.json",
        "container-metrics.json"
    ]
    
    for dashboard_file in dashboards:
        with open(f"dashboards/{dashboard_file}") as f:
            dashboard_json = json.load(f)
            import_dashboard(dashboard_json, "http://localhost:3000", "your-api-key")
```

---

## 仪表板验证

### 验证清单

#### 功能验证
- [ ] 所有仪表板成功导入
- [ ] 数据源连接正常
- [ ] 指标数据正常显示
- [ ] 时间范围选择器工作正常
- [ ] 刷新功能工作正常

#### 性能验证
- [ ] 仪表板加载时间<3秒
- [ ] 查询响应时间<1秒
- [ ] 内存使用正常
- [ ] CPU使用正常

#### 可用性验证
- [ ] 仪表板可访问
- [ ] 数据持续更新
- [ ] 告警正常触发
- [ ] 用户权限正常

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队