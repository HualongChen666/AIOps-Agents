# Tempo Deployment Architecture

## Overview
Tempo is a distributed tracing system that provides high-scale, low-latency tracing for cloud-native applications. This document describes the deployment architecture for AIOps Agent.

## Deployment Options

### 1. Single-Node Deployment (Recommended for Initial Setup)
**Use Case**: Development, testing, small-scale production

**Architecture**:
- Single Tempo instance (all-in-one mode)
- Local storage persistence
- Simple configuration
- Easy to deploy and maintain

**Components**:
- Tempo server (port 3200 for HTTP, 4317 for OTLP gRPC, 4318 for OTLP HTTP)
- Data persistence via Docker volumes

**Pros**:
- Simple setup
- Low resource requirements
- Easy to debug
- Suitable for most use cases

**Cons**:
- Single point of failure
- Limited scalability
- No high availability

### 2. Distributed Deployment (Recommended for Production)
**Use Case**: Medium to large-scale production

**Architecture**:
- Separate components for scalability
- Distributor for trace ingestion
- Ingester for trace processing
- Querier for trace queries
- Metrics generator for service graph
- Storage backend (S3/GCS/Azure)

**Components**:
- 2+ Gateway instances (API access)
- 2+ Distributor instances (trace ingestion)
- 3+ Ingester instances (trace processing)
- 2+ Querier instances (trace queries)
- 2+ Metrics generator instances (service graph)
- Object storage backend (S3/GCS)
- Load balancer

**Pros**:
- High availability
- Horizontal scalability
- Fault tolerance
- Better performance for high load

**Cons**:
- Complex setup
- Higher resource requirements
- More maintenance overhead

## Recommended Architecture for AIOps Agent

### Phase 1: Single-Node Deployment
Start with single-node deployment for simplicity and quick setup.

**Configuration**:
- Tempo v2.3.0 or later
- 2 CPU cores minimum
- 4GB RAM minimum
- 50GB SSD storage minimum
- Retention: 30 days default, configurable

**Storage Layout**:
```
/tempo-data/
  ├── traces/            # Trace data
  └── blocks/            # Block storage
```

**Network**:
- HTTP port: 3200
- OTLP gRPC port: 4317
- OTLP HTTP port: 4318
- Metrics port: 3100

### Phase 2: Distributed Migration (Future)
When trace volume exceeds single-node capacity, migrate to distributed deployment.

## Performance Considerations

### Data Retention
- Default: 30 days
- Hot data: 7 days (fast access)
- Warm data: 23 days (compressed)
- Cold data: Archive to S3 (optional)

### Sampling Strategy
- Default: 10% sampling rate
- Adjust based on traffic volume
- Use dynamic sampling for better coverage

### Query Optimization
- Use efficient trace ID queries
- Limit time range for searches
- Leverage tags for filtering
- Use service graph for dependency analysis

## Monitoring and Alerting

### Key Metrics to Monitor
- `tempo_traces_ingested_total` - Traces ingested
- `tempo_spans_ingested_total` - Spans ingested
- `tempo_query_duration_seconds` - Query latency
- `tempo_search_duration_seconds` - Search latency
- `tempo_storage_blocks_loaded_total` - Blocks loaded

### Alerting Rules
- High ingestion rate (> 100K spans/sec)
- High query latency (> 5s p95)
- High storage usage (> 80%)
- Service down

## Security

### Authentication
- Basic auth (username/password)
- Token-based authentication
- TLS encryption for data in transit

### Network Security
- Firewall rules
- Network segmentation
- VPN access for remote management

## Integration with OpenTelemetry

Tempo supports OpenTelemetry Protocol (OTLP) for trace ingestion:

```yaml
# OTLP gRPC endpoint
otlp:
  grpc:
    enabled: true
    endpoint: 0.0.0.0:4317

# OTLP HTTP endpoint
otlp:
  http:
    enabled: true
    endpoint: 0.0.0.0:4318
```

## Metrics Generator

Tempo can generate metrics from traces for service graph visualization:

```yaml
metrics-generator:
  enabled: true
  processor:
    service-graph:
      enabled: true
      histogram-buckets: [0.1, 0.2, 0.5, 1, 2, 5, 10]
```
