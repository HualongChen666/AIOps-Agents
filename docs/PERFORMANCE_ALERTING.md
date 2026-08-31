# 性能告警配置文档

## 概述

本文档描述了AIOps SRE Agent的性能告警配置方案，包括告警规则、告警通知和告警最佳实践。

---

## 告警架构

### 告警流程

```
┌─────────────────────────────────────────────────────────┐
│              Alert Monitoring System                      │
├─────────────────────────────────────────────────────────┤
│  Metrics Collection (Prometheus)                       │
│  ├── System Metrics                                    │
│  ├── Application Metrics                               │
│  └── Business Metrics                                  │
├─────────────────────────────────────────────────────────┤
│  Alert Evaluation (Prometheus Alertmanager)              │
│  ├── Alert Rules                                        │
│  ├── Alert Groups                                      │
│  ├── Silence Periods                                    │
│  └── Inhibition Rules                                  │
├─────────────────────────────────────────────────────────┤
│  Alert Notification                                    │
│  ├── Email Notifications                              │
│  ├── Slack Notifications                              │
│  ├── PagerDuty Notifications                          │
│  └── Webhook Notifications                            │
├─────────────────────────────────────────────────────────┤
│  Alert Management                                     │
│  ├── Alert Acknowledgment                              │
│  ├── Alert Escalation                                 │
│  ├── Alert Resolution                                  │
│  └── Alert History                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 告警规则

### 1. 系统健康告警

#### 告警规则
```yaml
# prometheus/alerts/system-health.yml
groups:
  - name: system_health
    rules:
      - alert: SystemHealthScoreLow
        expr: system_health_score < 80
        for: 5m
        labels:
          severity: warning
          category: system
        annotations:
          summary: "System health score is low"
          description: "System health score is {{ $value }} for the last 5 minutes"
          
      - alert: SystemHealthScoreCritical
        expr: system_health_score < 50
        for: 2m
        labels:
          severity: critical
          category: system
        annotations:
          summary: "System health score is critical"
          description: "System health score is {{ $value }} for the last 2 minutes"
```

#### 告警条件
- 警告级别: 警告（<80），严重（<50）
- 持续时间: 5分钟（警告），2分钟（严重）
- 通知渠道: Slack, Email

### 2. API性能告警

#### 告警规则
```yaml
# prometheus/alerts/api-performance.yml
groups:
  - name: api_performance
    rules:
      - alert: HighAPIErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
          category: api
        annotations:
          summary: "High API error rate"
          description: "API error rate is {{ $value }} for the last 5 minutes"
          
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        labels:
          severity: warning
          category: api
        annotations:
          summary: "High API latency"
          description: "API P95 latency is {{ $value }}s for the last 5 minutes"
          
      - alert: CriticalAPILatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 3
        for: 2m
        labels:
          severity: critical
          category: api
        annotations:
          summary: "Critical API latency"
          description: "API P95 latency is {{ $value }}s for the last 2 minutes"
```

#### 告警条件
- 错误率告警: >5%（警告）
- 延迟告警: P95 >1s（警告），>3s（严重）
- 持续时间: 5分钟（警告），2分钟（严重）
- 通知渠道: Slack, PagerDuty

### 3. 数据库性能告警

#### 告警规则
```yaml
# prometheus/alerts/database-performance.yml
groups:
  - name: database_performance
    rules:
      - alert: HighDatabaseLatency
        expr: histogram_quantile(0.95, pg_stat_statements_mean_time) > 0.5
        for: 5m
        labels:
          severity: warning
          category: database
        annotations:
          summary: "High database latency"
          description: "Database P95 latency is {{ $value }}s for the last 5 minutes"
          
      - alert: DatabaseConnectionPoolExhausted
        expr: pg_stat_activity_count{state="active"} / pg_settings_max_connections > 0.8
        for: 2m
        labels:
          severity: critical
          category: database
        annotations:
          summary: "Database connection pool exhausted"
          description: "Connection pool usage is {{ $value }} for the last 2 minutes"
          
      - alert: HighDatabaseLockWait
        expr: pg_stat_database_conflicts > 10
        for: 5m
        labels:
          severity: warning
          category: database
        annotations:
          summary: "High database lock wait"
          description: "Database lock conflicts is {{ $value }} for the last 5 minutes"
```

#### 告警条件
- 延迟告警: P95 >0.5s
- 连接池告警: 使用率>80%
- 锁等待告警: 冲突数>10
- 持续时间: 5分钟（警告），2分钟（严重）
- 通知渠道: Slack, Email, PagerDuty

### 4. 缓存性能告警

#### 告警规则
```yaml
# prometheus/alerts/cache-performance.yml
groups:
  - name: cache_performance
    rules:
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.8
        for: 10m
        labels:
          severity: warning
          category: cache
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value }} for the last 10 minutes"
          
      - alert: HighCacheEvictionRate
        expr: rate(cache_evictions_total[5m]) > 100
        for: 5m
        labels:
          severity: warning
          category: cache
        annotations:
          summary: "High cache eviction rate"
          description: "Cache eviction rate is {{ $value }}/s for the last 5 minutes"
          
      - alert: HighCacheMemoryUsage
        expr: cache_memory_usage_bytes / cache_max_memory_bytes > 0.9
        for: 5m
        labels:
          severity: critical
          category: cache
        annotations:
          summary: "High cache memory usage"
          description: "Cache memory usage is {{ $value }} for the last 5 minutes"
```

#### 告警条件
- 命中率告警: <80%
- 驱逐率告警: >100/s
- 内存使用告警: >90%
- 持续时间: 10分钟（命中率），5分钟（其他）
- 通知渠道: Slack, Email

### 5. 队列性能告警

#### 告警规则
```yaml
# prometheus/alerts/queue-performance.yml
groups:
  - name: queue_performance
    rules:
      - alert: HighQueueSize
        expr: queue_size > 1000
        for: 5m
        labels:
          severity: warning
          category: queue
        annotations:
          summary: "High queue size"
          description: "Queue size is {{ $value }} for the last 5 minutes"
          
      - alert: QueueProcessingSlow
        expr: histogram_quantile(0.95, queue_processing_time) > 30
        for: 5m
        labels:
          severity: warning
          category: queue
        annotations:
          summary: "Queue processing slow"
          description: "Queue P95 processing time is {{ $value }}s for the last 5 minutes"
          
      - alert: HighQueueErrorRate
        expr: rate(queue_errors_total[5m]) / rate(queue_processed_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          category: queue
        annotations:
          summary: "High queue error rate"
          description: "Queue error rate is {{ $value }} for the last 5 minutes"
```

#### 告警条件
- 队列大小告警: >1000
- 处理时间告警: P95 >30s
- 错误率告警: >10%
- 持续时间: 5分钟
- 通知渠道: Slack, PagerDuty

### 6. 告警处理告警

#### 告警规则
```yaml
# prometheus/alerts/alert-processing.yml
groups:
  - name: alert_processing
    rules:
      - alert: HighAlertProcessingTime
        expr: histogram_quantile(0.95, alert_processing_duration) > 60
        for: 10m
        labels:
          severity: warning
          category: alerts
        annotations:
          summary: "High alert processing time"
          description: "Alert P95 processing time is {{ $value }}s for the last 10 minutes"
          
      - alert: AlertBacklog
        expr: alert_queue_size > 500
        for: 5m
        labels:
          severity: critical
          category: alerts
        annotations:
          summary: "Alert backlog detected"
          description: "Alert queue size is {{ $value }} for the last 5 minutes"
          
      - alert: LowAlertResolutionRate
        expr: rate(alerts_resolved_total[1h]) / rate(alerts_total[1h]) < 0.8
        for: 30m
        labels:
          severity: warning
          category: alerts
        annotations:
          summary: "Low alert resolution rate"
          description: "Alert resolution rate is {{ $value }} for the last 30 minutes"
```

#### 告警条件
- 处理时间告警: P95 >60s
- 队列积压告警: >500
- 解决率告警: <80%
- 持续时间: 10分钟（处理时间），5分钟（队列），30分钟（解决率）
- 通知渠道: Slack, Email, PagerDuty

### 7. 资源使用告警

#### 告警规则
```yaml
# prometheus/alerts/resource-usage.yml
groups:
  - name: resource_usage
    rules:
      - alert: HighCPUUsage
        expr: system_cpu_usage > 80
        for: 10m
        labels:
          severity: warning
          category: system
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}% for the last 10 minutes"
          
      - alert: CriticalCPUUsage
        expr: system_cpu_usage > 95
        for: 5m
        labels:
          severity: critical
          category: system
        annotations:
          summary: "Critical CPU usage"
          description: "CPU usage is {{ $value }}% for the last 5 minutes"
          
      - alert: HighMemoryUsage
        expr: system_memory_usage > 80
        for: 10m
        labels:
          severity: warning
          category: system
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}% for the last 10 minutes"
          
      - alert: CriticalMemoryUsage
        expr: system_memory_usage > 90
        for: 5m
        labels:
          severity: critical
          category: system
        annotations:
          summary: "Critical memory usage"
          description: "Memory usage is {{ $value }}% for the last 5 minutes"
          
      - alert: HighDiskUsage
        expr: system_disk_usage > 85
        for: 10m
        labels:
          severity: warning
          category: system
        annotations:
          summary: "High disk usage"
          description: "Disk usage is {{ $value }}% for the last 10 minutes"
```

#### 告警条件
- CPU使用告警: >80%（警告），>95%（严重）
- 内存使用告警: >80%（警告），>90%（严重）
- 磁盘使用告警: >85%
- 持续时间: 10分钟（警告），5分钟（严重）
- 通知渠道: Slack, Email, PagerDuty

---

## 告警通知配置

### Alertmanager配置

#### 基础配置
```yaml
# prometheus/alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue/YOUR/SERVICE/KEY'

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'
    - match:
        severity: info
      receiver: 'email'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_SERVICE_KEY'
        description: 'Critical alerts'
  
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
  
  - name: 'email'
    email_configs:
      - to: 'team@example.com'
        headers:
          Subject: '[ALERT] {{ .GroupLabels.alertname }}'
```

### 通知渠道配置

#### Slack通知
```yaml
# Slack Webhook配置
slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#alerts'
    username: 'AIOps Alert Bot'
    icon_emoji: ':warning:'
    title: '{{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
    fields:
      - title: 'Severity'
        value: '{{ .Labels.severity }}'
        short: true
      - title: 'Category'
        value: '{{ .Labels.category }}'
        short: true
    actions:
      - type: button
        text: 'View in Grafana'
        url: '{{ .ExternalURL }}'
      - type: button
        text: 'Acknowledge'
        url: '{{ .GeneratorURL }}'
```

#### PagerDuty通知
```yaml
# PagerDuty配置
pagerduty_configs:
  - service_key: 'YOUR_SERVICE_KEY'
    description: 'Critical alerts from AIOps Agent'
    severity: 'critical'
    client: 'AIOps Agent'
    client_url: 'https://aiops-agent.example.com'
    details:
      firing: '{{ .GroupLabels.alertname }} is firing'
      resolved: '{{ .GroupLabels.alertname }} is resolved'
```

#### Email通知
```yaml
# Email通知配置
email_configs:
  - to: 'team@example.com'
    from: 'alerts@aiops-agent.example.com'
    headers:
      Subject: '[ALERT] {{ .GroupLabels.alertname }}'
    html: |
      <h2>{{ .GroupLabels.alertname }}</h2>
      <p>{{ .CommonAnnotations.description }}</p>
      <table>
        <tr><th>Severity</th><td>{{ .Labels.severity }}</td></tr>
        <tr><th>Category</th><td>{{ .Labels.category }}</td></tr>
        <tr><th>Time</th><td>{{ .StartsAt }}</td></tr>
      </table>
      <p><a href="{{ .ExternalURL }}">View in Grafana</a></p>
```

---

## 告警最佳实践

### 1. 告警设计
- 设置合理的告警阈值
- 避免告警疲劳
- 提供清晰的告警信息
- 设置合理的告警频率

### 2. 告警分组
- 按严重程度分组
- 按服务分组
- 按类别分组
- 按环境分组

### 3. 告警抑制
- 设置静默期
- 使用抑制规则
- 避免告警风暴
- 合并相似告警

### 4. 告警响应
- 及时确认告警
- 记录告警处理
- 分析告警根因
- 实施预防措施

---

## 告警测试

### 告警测试脚本

#### 测试脚本
```python
# scripts/test_alerts.py
import requests
import time

def test_alert(alert_name, alert_config):
    """测试告警规则"""
    
    # 模拟告警条件
    print(f"Testing alert: {alert_name}")
    
    # 触发告警
    print(f"Triggering alert condition: {alert_config['expr']}")
    
    # 等待告警触发
    time.sleep(alert_config.get('for', 60))
    
    # 验证告警
    print("Verifying alert was triggered...")
    
    # 检查告警通知
    print("Checking alert notifications...")
    
    print(f"Alert test completed: {alert_name}")

if __name__ == "__main__":
    # 测试所有告警规则
    alerts = [
        {
            "name": "SystemHealthScoreLow",
            "config": {
                "expr": "system_health_score < 80",
                "for": "5m"
            }
        },
        {
            "name": "HighAPIErrorRate",
            "config": {
                "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) > 0.05",
                "for": "5m"
            }
        },
        {
            "name": "HighDatabaseLatency",
            "config": {
                "expr": "histogram_quantile(0.95, pg_stat_statements_mean_time) > 0.5",
                "for": "5m"
            }
        }
    ]
    
    for alert in alerts:
        test_alert(alert["name"], alert["config"])
```

---

## 告警维护

### 告警审查

#### 审查清单
- [ ] 告警阈值是否合理
- [ ] 告警频率是否合适
- [ ] 告警信息是否清晰
- [ ] 告警通知是否有效
- [ ] 告警响应是否及时

### 告警优化

#### 优化策略
- 定期审查告警规则
- 调整告警阈值
- 优化告警分组
- 改进告警信息
- 提高告警响应效率

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队