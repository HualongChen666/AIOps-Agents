# LogQL Query Optimization Guide for Loki

## Overview
LogQL (Log Query Language) is Loki's query language for selecting and aggregating log data. This guide provides best practices for optimizing LogQL queries in the AIOps Agent environment.

## LogQL Syntax Basics

### Log Stream Selector
Select logs based on label selectors:

```logql
{job="aiops-agent", service="api"}
{job="aiops-agent"} |= "error"
{job="aiops-agent"} |~ "error.*timeout"
```

### Log Pipeline
Process log lines with pipeline operators:

```logql
{job="aiops-agent"}
  | json
  | line_format "{{.level}}: {{.message}}"
  | label_format level="{{.level}}"
```

### Metrics Queries
Convert logs to metrics:

```logql
# Count logs
count_over_time({job="aiops-agent"} [5m])

# Rate of logs
rate({job="aiops-agent"}[5m])

# Sum by label
sum(count_over_time({job="aiops-agent"} [5m])) by (level)

# Percentile
quantile_over_time(0.95, {job="aiops-agent"} | unwrap duration [5m])
```

## Query Optimization Techniques

### 1. Use Efficient Label Selectors
```logql
# Good: Exact match
{job="aiops-agent", level="error"}

# Avoid: Regex match when exact match works
{job=~".*aiops-agent.*"}
```

### 2. Filter Early
Apply filters as early as possible in the pipeline:

```logql
# Good: Filter before processing
{job="aiops-agent"} |= "error" | json

# Less efficient: Process before filtering
{job="aiops-agent"} | json | line_format "{{.message}}" |= "error"
```

### 3. Limit Time Range
Avoid querying excessively long time ranges:

```logql
# Good: Query last 24 hours
{job="aiops-agent"} [24h]

# Avoid: Querying months of data
{job="aiops-agent"} [90d]
```

### 4. Use Aggregation Functions
Aggregate data to reduce query load:

```logql
# Good: Aggregate by label
sum(count_over_time({job="aiops-agent"} [5m])) by (level)

# Less efficient: Count all logs
count_over_time({job="aiops-agent"} [5m])
```

## Indexing Strategy

### 1. Label Cardinality Management
Keep label cardinality low for frequently queried labels:

- **Low cardinality (< 100 values)**: job, service, environment
- **Medium cardinality (100-1000 values)**: level, endpoint
- **High cardinality (> 1000 values)**: Avoid or use carefully: user_id, request_id

### 2. Label Ordering
Loki indexes labels in the order they appear. Put frequently filtered labels first:

```logql
# Good label ordering
{job="aiops-agent", service="api", level="error"}

# Label priority: job > service > level
```

### 3. Use Structured Metadata
Extract important fields as labels:

```logql
{job="aiops-agent"}
  | json
  | label_format level="{{.level}}", service="{{.service}}"
```

## Specific Optimizations for AIOps Agent

### 1. Error Log Queries
```logql
# Query error logs
{job="aiops-agent", level="error"}

# Count errors by service
sum(count_over_time({job="aiops-agent", level="error"} [5m])) by (service)

# Error rate
rate({job="aiops-agent", level="error"}[5m])
```

### 2. AI Engine Logs
```logql
# Query AI response logs
{job="aiops-agent", service="ai-engine"} |= "response"

# Average response time
{job="aiops-agent", service="ai-engine"}
  | json
  | unwrap duration
  | avg_over_time(duration[5m])

# AI error rate
rate({job="aiops-agent", service="ai-engine"} |~ "error" [5m])
```

### 3. Repair Engine Logs
```logql
# Query repair logs
{job="aiops-agent", service="repair-engine"}

# Repair success rate
sum(count_over_time({job="aiops-agent", service="repair-engine"} |= "success" [5m]))
/
sum(count_over_time({job="aiops-agent", service="repair-engine"} [5m]))

# Active repairs
count_over_time({job="aiops-agent", service="repair-engine"} |= "started" [5m])
```

## Performance Monitoring

### Monitor Query Performance
```logql
# Monitor slow queries
{job="loki"} |= "slow query"

# Monitor query duration
{job="loki"} | json | unwrap duration
```

### Set Up Query Performance Alerts
```yaml
# In Loki ruler configuration
groups:
  - name: loki_performance
    rules:
      - alert: LokiSlowQueries
        expr: rate({job="loki"} |~ "query.*duration.*>.*5s"[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
```

## Query Caching

Loki automatically caches query results. To maximize cache hits:

1. Use consistent time ranges in queries
2. Avoid using relative time ranges when possible
3. Use absolute timestamps for historical queries

```logql
# Good for caching
{job="aiops-agent"} [24h]

# Less cache-friendly
{job="aiops-agent"} offset 24h
```

## Common Query Patterns

### Error Pattern Detection
```logql
# Detect error patterns
{job="aiops-agent", level="error"}
  | pattern `<error_type> - <message>`
  | label_format error_type="{{.error_type}}"
```

### Time Series Analysis
```logql
# Analyze log volume over time
sum(count_over_time({job="aiops-agent"} [5m]))

# Compare current vs previous period
sum(count_over_time({job="aiops-agent"} [5m]))
/
sum(count_over_time({job="aiops-agent"} offset 1h [5m]))
```

### Anomaly Detection
```logql
# Detect log volume anomalies
abs(
  sum(count_over_time({job="aiops-agent"} [5m]))
  -
  avg_over_time(sum(count_over_time({job="aiops-agent"} [5m])) [1h:5m])
)
>
2 * stddev_over_time(sum(count_over_time({job="aiops-agent"} [5m])) [1h:5m])
```

## Resource Limits

Configure query limits to prevent resource exhaustion:

```yaml
# In Loki configuration
limits_config:
  max_entries_limit_per_query: 5000
  max_query_series: 1000
  max_query_parallelism: 32
  max_streams_matchers_per_query: 1000
```

## Best Practices Summary

1. **Use efficient label selectors**: Prefer exact matches over regex
2. **Filter early**: Apply filters before processing
3. **Limit time range**: Query only necessary time ranges
4. **Aggregate data**: Use aggregation functions to reduce load
5. **Monitor performance**: Track query performance and optimize slow queries
6. **Use caching**: Write cache-friendly queries
7. **Manage cardinality**: Keep label cardinality low
8. **Set limits**: Configure query limits to prevent abuse
