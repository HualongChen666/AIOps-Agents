# VictoriaMetrics Performance Testing and Capacity Planning

## Overview
This document provides guidelines for performance testing and capacity planning for VictoriaMetrics in the AIOps Agent environment.

## Performance Testing Methodology

### 1. Baseline Performance Metrics
Establish baseline metrics before load testing:

```bash
# Monitor VictoriaMetrics internal metrics
curl http://localhost:8428/metrics | grep vmmetrics

# Key metrics to track:
# - vmmetrics_storage_size_bytes
# - vmmetrics_request_duration_seconds
# - vmmetrics_rows_per_second
# - vmmetrics_slow_queries_total
```

### 2. Load Testing Scenarios

#### Scenario 1: Ingestion Rate Test
Test maximum sustainable ingestion rate.

```bash
# Use vmctl to simulate metric ingestion
vmctl import -format prometheus -input metrics.txt \
  -http-urls http://localhost:8428

# Metrics.txt format:
metric_name{label1="value1",label2="value2"} value timestamp
```

**Test Parameters:**
- Start: 10,000 samples/sec
- Increment: 10,000 samples/sec every 5 minutes
- Target: 1,000,000 samples/sec
- Duration: 1 hour at each increment

**Success Criteria:**
- Query latency < 100ms (p95)
- CPU usage < 80%
- Memory usage < 80%
- No errors in logs

#### Scenario 2: Query Load Test
Test query performance under load.

```bash
# Use vegeta for load testing
echo "GET http://localhost:8428/api/v1/query?query=up" | \
  vegeta attack -rate=100 -duration=5m | vegeta report
```

**Test Parameters:**
- Query types: instant queries, range queries, aggregations
- Rate: 10-1000 queries/sec
- Duration: 10 minutes
- Concurrent users: 10-100

**Success Criteria:**
- p95 latency < 500ms
- p99 latency < 1s
- Error rate < 1%

#### Scenario 3: Mixed Workload Test
Test realistic mixed workload (ingestion + queries).

```bash
# Run ingestion and query tests simultaneously
# Monitor resource usage and performance
```

## Capacity Planning

### Hardware Requirements

#### Minimum (Development/Testing)
- CPU: 2 cores
- RAM: 4 GB
- Storage: 50 GB SSD
- Network: 1 Gbps
- Expected ingestion: < 100K samples/sec

#### Recommended (Production - Small)
- CPU: 4 cores
- RAM: 8 GB
- Storage: 200 GB SSD
- Network: 1 Gbps
- Expected ingestion: 100K-500K samples/sec

#### Recommended (Production - Medium)
- CPU: 8 cores
- RAM: 16 GB
- Storage: 500 GB SSD
- Network: 10 Gbps
- Expected ingestion: 500K-1M samples/sec

#### Recommended (Production - Large)
- CPU: 16+ cores
- RAM: 32+ GB
- Storage: 1TB+ SSD (NVMe preferred)
- Network: 10+ Gbps
- Expected ingestion: 1M+ samples/sec

### Storage Capacity Planning

#### Calculation Formula
```
Storage per day = (samples_per_sec * bytes_per_sample * 86400) / compression_ratio

Where:
- bytes_per_sample: ~2 bytes (typical after compression)
- compression_ratio: 5-10x (VictoriaMetrics compression)
```

#### Example Calculations
```
100K samples/sec:
  Raw: 100,000 * 2 * 86400 = 17.28 GB/day
  Compressed (5x): 3.46 GB/day
  30 days: 104 GB

1M samples/sec:
  Raw: 1,000,000 * 2 * 86400 = 172.8 GB/day
  Compressed (5x): 34.56 GB/day
  30 days: 1.04 TB
```

### Retention Policy Impact

| Retention | 100K samples/sec | 500K samples/sec | 1M samples/sec |
|----------|------------------|------------------|----------------|
| 7 days   | 24 GB            | 120 GB           | 242 GB         |
| 30 days  | 104 GB           | 518 GB           | 1.04 TB        |
| 90 days  | 311 GB           | 1.55 TB         | 3.11 TB        |
| 180 days | 622 GB           | 3.11 TB         | 6.22 TB        |

## Performance Optimization

### 1. VictoriaMetrics Configuration

```bash
# Startup flags for performance optimization
--storageDataPath=/victoria-data
--httpListenAddr=:8428
--retentionPeriod=30d

# Memory optimization
--memory.allowedPercent=60  # Use 60% of available RAM
--memory.allowedBytes=8GB   # Or specific limit

# Query optimization
--search.maxPointsPerTimeseries=30000
--search.maxUniqueTimeseries=30000
--search.maxQueryDuration=5m

# Ingestion optimization
--ingestion.maxSamplesPerSecond=1000000
--ingestion.maxRowsPerSecond=1000000

# Compression optimization
--dedup.minScrapeInterval=1m
--dedup.maxScrapeInterval=10m
```

### 2. Data Model Optimization

#### Reduce Cardinality
```promql
# Bad: High cardinality label
http_requests_total{user_id="12345"}

# Good: Aggregate by service
http_requests_total{service="api", endpoint="/users"}
```

#### Use Efficient Metric Names
```promql
# Good: Follow naming conventions
aiops_http_requests_total
aiops_request_duration_seconds
aiops_memory_usage_bytes
```

### 3. Query Optimization

#### Use Recording Rules
```yaml
# Pre-compute expensive queries
- record: aiops:http_requests_total:rate5m
  expr: sum by (job, status) (rate(http_requests_total[5m]))
```

#### Limit Query Time Range
```promql
# Query last 24 hours at 5m resolution
rate(http_requests_total[5m])[24h:5m]

# Avoid querying months at high resolution
rate(http_requests_total[5m])[90d:5m]
```

## Monitoring Performance

### Key Metrics to Monitor

```promql
# Storage usage
vmmetrics_storage_size_bytes

# Ingestion rate
rate(vmmetrics_rows_per_second[5m])

# Query performance
histogram_quantile(0.95, rate(vmmetrics_request_duration_seconds_bucket[5m]))

# Slow queries
rate(vmmetrics_slow_queries_total[5m])

# Memory usage
process_resident_memory_bytes{job="victoriametrics"}

# CPU usage
rate(process_cpu_seconds_total{job="victoriametrics"}[5m])
```

### Performance Alerts

```yaml
# High ingestion rate
- alert: VictoriaMetricsHighIngestionRate
  expr: rate(vmmetrics_rows_per_second[5m]) > 1000000
  for: 5m
  labels:
    severity: warning

# Slow queries
- alert: VictoriaMetricsSlowQueries
  expr: histogram_quantile(0.95, rate(vmmetrics_request_duration_seconds_bucket[5m])) > 5
  for: 5m
  labels:
    severity: warning

# High storage usage
- alert: VictoriaMetricsHighStorageUsage
  expr: (vmmetrics_storage_size_bytes / vmmetrics_storage_size_bytes_limit) > 0.8
  for: 5m
  labels:
    severity: warning
```

## Scaling Strategy

### Vertical Scaling (Single Node)
When to scale vertically:
- Ingestion rate < 1M samples/sec
- Query load moderate
- Simple deployment required

Steps:
1. Increase CPU cores
2. Add more RAM
3. Use faster storage (NVMe)
4. Optimize configuration

### Horizontal Scaling (Cluster)
When to scale horizontally:
- Ingestion rate > 1M samples/sec
- High query load
- High availability required

Components:
- VMStorage: Data storage nodes (3+ for replication)
- VMSelect: Query routing nodes (2+)
- VMInsert: Write routing nodes (2+)
- Load balancer: nginx/haproxy

## Performance Testing Checklist

- [ ] Establish baseline metrics
- [ ] Test ingestion rate at various loads
- [ ] Test query performance under load
- [ ] Test mixed workload scenarios
- [ ] Monitor resource usage during tests
- [ ] Validate data consistency
- [ ] Test failover scenarios (if clustered)
- [ ] Document performance characteristics
- [ ] Set up performance monitoring
- [ ] Configure performance alerts

## Capacity Planning Checklist

- [ ] Estimate current ingestion rate
- [ ] Project future growth (6-12 months)
- [ ] Calculate storage requirements
- [ ] Select appropriate hardware
- [ ] Configure retention policies
- [ ] Set up monitoring and alerts
- [ ] Plan scaling strategy
- [ ] Document capacity plan
- [ ] Review and update quarterly
