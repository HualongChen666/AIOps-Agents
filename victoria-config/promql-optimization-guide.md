# PromQL Query Optimization Guide for VictoriaMetrics

## Overview
This guide provides best practices for optimizing PromQL queries in VictoriaMetrics for better performance and resource utilization.

## General Best Practices

### 1. Use Efficient Label Selectors
```promql
# Good: Exact match
up{job="aiops-agent"}

# Avoid: Regex match when exact match works
up{job=~".*aiops-agent.*"}
```

### 2. Avoid High Cardinality Labels
High cardinality labels (labels with many unique values) can severely impact performance.

```promql
# Bad: Using user_id or request_id as label
http_requests_total{user_id="12345"}

# Good: Use aggregated metrics
sum(http_requests_total) by (service, endpoint)
```

### 3. Use Recording Rules for Complex Queries
Pre-compute frequently used complex queries using recording rules.

```yaml
# In recording-rules.yml
- record: aiops:http_requests_total:rate5m
  expr: sum by (job, status) (rate(http_requests_total[5m]))
```

### 4. Limit Query Time Range
Avoid querying excessively long time ranges.

```promql
# Good: Query last 24 hours
rate(http_requests_total[5m])[24h:5m]

# Avoid: Querying months of data at high resolution
rate(http_requests_total[5m])[90d:5m]
```

## Query Optimization Techniques

### 1. Use Subqueries for Time-Based Calculations
```promql
# Calculate rate over time with subquery
rate(http_requests_total[5m])[1h:5m]

# This is equivalent to:
rate_over_time(http_requests_total[1h])
```

### 2. Leverage Aggregation Functions
```promql
# Sum by relevant labels only
sum by (service, endpoint) (http_requests_total)

# Avoid: Sum without grouping (can be expensive)
sum(http_requests_total)
```

### 3. Use Binary Operators Efficiently
```promql
# Good: Filter before aggregation
rate(http_requests_total{status="5xx"}[5m])

# Less efficient: Aggregate then filter
rate(http_requests_total[5m]) > 0
```

### 4. Use Histogram Functions
```promql
# Calculate percentiles efficiently
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# This is more efficient than calculating percentiles from raw data
```

## Indexing Strategy

### 1. Label Cardinality Management
Keep label cardinality low for frequently queried labels:

- **Low cardinality (< 100 values)**: job, instance, service, component
- **Medium cardinality (100-1000 values)**: endpoint, status_code
- **High cardinality (> 1000 values)**: Avoid or use carefully: user_id, request_id

### 2. Label Ordering
VictoriaMetrics indexes labels in the order they appear in metric names. Put frequently filtered labels first.

```promql
# Good label ordering
aiops_http_requests_total{service="api", endpoint="/users", status="200"}

# Label priority: service > endpoint > status
```

### 3. Use Metric Naming Conventions
```promql
# Follow Prometheus metric naming conventions
# - Use snake_case
# - Include unit suffix when applicable
# - Use _total for counters
# - Use _seconds for durations
# - Use _bytes for sizes

aiops_http_requests_total
aiops_request_duration_seconds
aiops_memory_usage_bytes
```

## Specific Optimizations for AIOps Agent

### 1. Alert Engine Metrics
```promql
# Optimized alert backlog query
sum by (severity) (aiops_alert_backlog_count)

# Optimized alert rate query
rate(aiops_alerts_total[5m])
```

### 2. AI Engine Metrics
```promql
# Optimized AI response time query
histogram_quantile(0.95, 
    sum(rate(aiops_ai_response_duration_seconds_bucket[5m])) by (le, model)
)

# Optimized AI success rate
sum(rate(aiops_ai_successes_total[5m])) / 
sum(rate(aiops_ai_attempts_total[5m]))
```

### 3. Repair Engine Metrics
```promql
# Optimized repair success rate
sum(rate(aiops_repair_successes_total[5m])) / 
sum(rate(aiops_repair_attempts_total[5m]))

# Optimized active repairs
sum(aiops_repair_active_count) by (type)
```

## Performance Monitoring

### Monitor Query Performance
```promql
# Monitor slow queries
rate(vmmetrics_slow_queries_total[5m])

# Monitor query duration
histogram_quantile(0.95, rate(vmmetrics_request_duration_seconds_bucket[5m]))

# Monitor rows scanned
rate(vmmetrics_rows_per_second[5m])
```

### Set Up Query Performance Alerts
```yaml
# In alert-rules.yml
- alert: VictoriaMetricsSlowQueries
  expr: histogram_quantile(0.95, rate(vmmetrics_request_duration_seconds_bucket[5m])) > 5
  for: 5m
  labels:
    severity: warning
```

## Query Caching

VictoriaMetrics automatically caches query results. To maximize cache hits:

1. Use consistent time ranges in queries
2. Avoid using `now()` in queries when possible
3. Use absolute timestamps for historical queries

```promql
# Good for caching
rate(http_requests_total[5m])[24h:5m]

# Less cache-friendly
rate(http_requests_total[5m]) offset 24h
```

## Downsampling for Long-Term Storage

Configure VictoriaMetrics to downsample old data for better performance:

```bash
# In VictoriaMetrics startup flags
--retentionPeriod=30d
--downsampling.period=30d:1h  # Downsample to 1h after 30 days
--downsampling.period=90d:24h # Downsample to 24h after 90 days
```

## Query Profiling

Use VictoriaMetrics query profiling to identify slow queries:

```bash
# Enable query profiling
curl http://localhost:8428/debug/pprof/profile?seconds=30

# View query statistics
curl http://localhost:8428/internal/resetRollupResultCache
```

## Common Query Patterns

### Time Series Comparison
```promql
# Compare current vs previous period
rate(http_requests_total[5m])
/
rate(http_requests_total[5m] offset 1h)
```

### Anomaly Detection
```promql
# Detect anomalies using standard deviation
rate(http_requests_total[5m])
>
(rate(http_requests_total[5m] offset 1h) + 
 3 * stddev_over_time(rate(http_requests_total[5m])[1h:5m]))
```

### Trend Analysis
```promql
# Calculate trend using linear regression
predict_linear(rate(http_requests_total[5m])[1h:5m], 3600)
```

## Resource Limits

Configure query limits to prevent resource exhaustion:

```bash
# In VictoriaMetrics startup flags
--search.maxPointsPerTimeseries=30000
--search.maxUniqueTimeseries=30000
--search.maxQueryDuration=5m
```
