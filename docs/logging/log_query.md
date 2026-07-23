# 日志查询文档

## 概述

本文档提供AIOps Agent系统的日志查询指南，包括日志查询语法、查询工具和查询示例。

## Kibana查询

### 基础查询

#### 按级别查询

```kql
level: "ERROR"
```

#### 按时间范围查询

```kql
@timestamp: [now-1h TO now]
```

#### 按模块查询

```kql
logger: "auth.service"
```

#### 组合查询

```kql
level: "ERROR" AND logger: "database.service"
```

### 高级查询

#### 通配符查询

```kql
message: "*error*"
logger: "api.*"
```

#### 正则表达式查询

```kql
message: /Connection.*timeout/
```

#### 范围查询

```kql
response_time: [0.1 TO 1.0]
status_code: [400 TO 499]
```

#### 字段存在性查询

```kql
_exists_: trace_id
_missing_: user_id
```

### 聚合查询

#### 按级别统计

```kql
GET aiops-logs-*/_search
{
  "size": 0,
  "aggs": {
    "by_level": {
      "terms": {
        "field": "level"
      }
    }
  }
}
```

#### 按时间统计

```kql
GET aiops-logs-*/_search
{
  "size": 0,
  "aggs": {
    "by_time": {
      "date_histogram": {
        "field": "@timestamp",
        "interval": "1h"
      }
    }
  }
}
```

#### 按模块统计

```kql
GET aiops-logs-*/_search
{
  "size": 0,
  "aggs": {
    "by_module": {
      "terms": {
        "field": "logger"
      }
    }
  }
}
```

### 常用查询示例

#### 查询最近的错误日志

```kql
level: "ERROR" AND @timestamp: [now-1h TO now]
```

#### 查询特定用户的操作日志

```kql
context.user_id: "user-123" AND @timestamp: [now-24h TO now]
```

#### 查询慢请求日志

```kql
context.response_time: [1.0 TO *] AND level: "WARNING"
```

#### 查询特定trace的所有日志

```kql
context.trace_id: "abc123def456"
```

#### 查询数据库错误日志

```kql
logger: "database.*" AND level: "ERROR"
```

## Grafana查询

### 基础查询

#### 日志总量

```promql
count_over_time(logs_total[1h])
```

#### 错误日志数量

```promql
count_over_time(logs_error_total[1h])
```

#### 错误率

```promql
rate(logs_error_total[5m]) / rate(logs_total[5m]) * 100
```

### 高级查询

#### 按级别分组

```promql
sum by (level) (logs_total)
```

#### 按模块分组

```promql
sum by (logger) (logs_total)
```

#### 时间序列查询

```promql
rate(logs_total[5m])
```

### 常用查询示例

#### 日志量趋势

```promql
rate(logs_total[5m])
```

#### 错误率趋势

```promql
rate(logs_error_total[5m])
```

#### 响应时间分布

```promql
histogram_quantile(0.95, logs_response_time)
```

#### 模块错误率

```promql
sum by (logger) (rate(logs_error_total[5m])) / sum by (logger) (rate(logs_total[5m])) * 100
```

## Python查询

### 使用Elasticsearch客户端

```python
from elasticsearch import Elasticsearch

# 连接Elasticsearch
es = Elasticsearch(hosts=["localhost:9200"])

# 基础查询
query = {
    "query": {
        "bool": {
            "must": [
                {"match": {"level": "ERROR"}},
                {"range": {"@timestamp": {"gte": "now-1h"}}}
            ]
        }
    },
    "size": 100
}

result = es.search(index="aiops-logs-*", body=query)
for hit in result["hits"]["hits"]:
    print(hit["_source"])
```

### 使用日志分析器

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()

# 添加日志数据
logs = [
    {"timestamp": "2026-07-03T10:30:45Z", "level": "INFO", "message": "Test"},
    {"timestamp": "2026-07-03T10:31:45Z", "level": "ERROR", "message": "Error"}
]
analyzer.add_logs(logs)

# 计算统计信息
stats = analyzer.calculate_statistics()
print(f"Total logs: {stats.total_logs}")
print(f"Error rate: {stats.error_rate}")

# 检测模式
patterns = analyzer.detect_patterns(min_occurrences=2)
for pattern in patterns:
    print(f"Pattern: {pattern.pattern}, Count: {pattern.count}")
```

## 查询语法

### 布尔运算符

| 运算符 | 说明 | 示例 |
|--------|------|------|
| `AND` | 逻辑与 | `level: "ERROR" AND logger: "api"` |
| `OR` | 逻辑或 | `level: "ERROR" OR level: "CRITICAL"` |
| `NOT` | 逻辑非 | `level: "ERROR" NOT logger: "test"` |

### 比较运算符

| 运算符 | 说明 | 示例 |
|--------|------|------|
| `>` | 大于 | `response_time: >1.0` |
| `<` | 小于 | `response_time: <0.1` |
| `>=` | 大于等于 | `response_time: >=1.0` |
| `<=` | 小于等于 | `response_time: <=1.0` |
| `=` | 等于 | `status_code: =200` |

### 通配符

| 通配符 | 说明 | 示例 |
|--------|------|------|
| `*` | 匹配零个或多个字符 | `message: "*error*"` |
| `?` | 匹配单个字符 | `message: "erro?"` |

### 正则表达式

```kql
message: /Connection.*failed/
logger: /api\..*\.service/
```

## 查询优化

### 索引优化

#### 使用时间范围索引

```kql
# 优化前
level: "ERROR"

# 优化后
level: "ERROR" AND @timestamp: [now-24h TO now]
```

#### 使用特定索引

```kql
# 查询特定时间范围的索引
GET aiops-logs-2026.07.03/_search
```

### 查询优化

#### 避免通配符开头

```kql
# 避免这种查询
message: "*error"

# 使用这种查询
message: "error*"
```

#### 使用过滤器而非查询

```kql
# 使用过滤器（不计算分数）
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"level": "ERROR"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

#### 限制返回字段

```kql
{
  "_source": ["timestamp", "level", "message"],
  "query": {
    "match_all": {}
  }
}
```

## 查询工具

### Kibana Dev Tools

Kibana Dev Tools提供了强大的查询和调试功能。

```kql
GET aiops-logs-*/_search
{
  "query": {
    "match_all": {}
  },
  "size": 10
}
```

### Elasticsearch API

使用curl命令行工具查询：

```bash
curl -X GET "localhost:9200/aiops-logs-*/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match": {
      "level": "ERROR"
    }
  }
}'
```

### Python脚本

创建Python脚本进行批量查询：

```python
from elasticsearch import Elasticsearch
import json

es = Elasticsearch(hosts=["localhost:9200"])

def query_logs(query, size=100):
    result = es.search(index="aiops-logs-*", body={"query": query, "size": size})
    return [hit["_source"] for hit in result["hits"]["hits"]]

# 使用示例
query = {"match": {"level": "ERROR"}}
logs = query_logs(query)
for log in logs:
    print(json.dumps(log, indent=2))
```

## 查询示例

### 场景1：排查用户问题

**问题**: 用户报告登录失败

**查询步骤**:

1. 查询特定用户的日志

```kql
context.user_id: "user-123" AND @timestamp: [now-1h TO now]
```

2. 查询认证模块的错误日志

```kql
logger: "auth.*" AND level: "ERROR" AND @timestamp: [now-1h TO now]
```

3. 查询相关trace的所有日志

```kql
context.trace_id: "trace-from-auth"
```

### 场景2：性能问题排查

**问题**: API响应时间变慢

**查询步骤**:

1. 查询慢请求日志

```kql
context.response_time: [1.0 TO *] AND @timestamp: [now-1h TO now]
```

2. 按端点统计平均响应时间

```kql
GET aiops-logs-*/_search
{
  "size": 0,
  "query": {
    "range": {
      "@timestamp": {
        "gte": "now-1h"
      }
    }
  },
  "aggs": {
    "by_endpoint": {
      "terms": {
        "field": "context.request_path"
      },
      "aggs": {
        "avg_response_time": {
          "avg": {
            "field": "context.response_time"
          }
        }
      }
    }
  }
}
```

3. 查询数据库相关日志

```kql
logger: "database.*" AND @timestamp: [now-1h TO now]
```

### 场景3：错误趋势分析

**问题**: 错误率突然上升

**查询步骤**:

1. 查询错误率趋势

```kql
GET aiops-logs-*/_search
{
  "size": 0,
  "query": {
    "range": {
      "@timestamp": {
        "gte": "now-24h"
      }
    }
  },
  "aggs": {
    "by_time": {
      "date_histogram": {
        "field": "@timestamp",
        "interval": "1h"
      },
      "aggs": {
        "error_count": {
          "filter": {
            "terms": {
              "level": ["ERROR", "CRITICAL"]
            }
          }
        }
      }
    }
  }
}
```

2. 查询错误模式

```python
from aiops_core.logging.analysis import LogAnalyzer

analyzer = LogAnalyzer()
# 添加日志数据...
patterns = analyzer.detect_patterns(min_occurrences=5)
for pattern in patterns:
    if pattern.severity == "error":
        print(f"Error pattern: {pattern.pattern}")
```

3. 查询最频繁的错误模块

```kql
GET aiops-logs-*/_search
{
  "size": 0,
  "query": {
    "terms": {
      "level": ["ERROR", "CRITICAL"]
    }
  },
  "aggs": {
    "by_module": {
      "terms": {
        "field": "logger",
        "size": 10
      }
    }
  }
}
```

## 查询最佳实践

### 1. 使用时间范围

始终指定时间范围以限制查询数据量：

```kql
# 推荐
level: "ERROR" AND @timestamp: [now-1h TO now]

# 不推荐
level: "ERROR"
```

### 2. 使用特定字段

使用特定字段而非全文搜索：

```kql
# 推荐
level: "ERROR" AND logger: "api"

# 不推荐
message: "ERROR api"
```

### 3. 限制返回数量

限制返回结果数量以提高查询性能：

```kql
{
  "size": 100,
  "query": {
    "match_all": {}
  }
}
```

### 4. 使用分页

对于大量数据，使用分页查询：

```kql
{
  "from": 0,
  "size": 100,
  "query": {
    "match_all": {}
  }
}
```

### 5. 缓存常用查询

缓存常用查询以提高查询效率：

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_error_logs(hours=1):
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"level": "ERROR"}},
                    {"range": {"@timestamp": {"gte": f"now-{hours}h"}}}
                ]
            }
        }
    }
    return es.search(index="aiops-logs-*", body=query)
```

## 常见问题

### Q: 如何查询跨索引的日志？

A: 使用通配符索引模式：

```kql
GET aiops-logs-*/_search
{
  "query": {
    "match_all": {}
  }
}
```

### Q: 如何查询嵌套字段？

A: 使用点号表示法：

```kql
context.user_id: "user-123"
context.trace_id: "trace-abc"
```

### Q: 如何导出查询结果？

A: 使用Elasticsearch的scroll API或使用Python脚本：

```python
from elasticsearch.helpers import scan

results = scan(es, index="aiops-logs-*", query={"query": {"match_all": {}}})
for result in results:
    print(result["_source"])
```

### Q: 如何实时监控日志？

A: 使用Kibana的实时监控或Grafana面板：

```promql
rate(logs_total[1m])
```

## 技术评审检查清单

- [x] 包含Kibana查询指南
- [x] 包含Grafana查询指南
- [x] 包含Python查询指南
- [x] 包含查询语法说明
- [x] 包含查询优化建议
- [x] 包含查询工具介绍
- [x] 包含查询示例
- [x] 包含场景化查询指南
- [x] 包含查询最佳实践
- [x] 包含常见问题解答
