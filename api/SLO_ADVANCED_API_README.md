# SLO Advanced API Documentation

## Overview

The `slo_advanced_router.py` provides comprehensive SLO/SLA management API endpoints for the AIOps SRE Agent platform. This router implements 19 API endpoints covering SLO definitions, metrics, budgets, burn rates, alerts, reports, historical data, services, objectives, and rollups.

## API Endpoints

### 1. SLO Definitions

#### GET /api/v1/slo/definitions
List all SLO definitions.

**Response:**
```json
{
  "definitions": [
    {
      "id": "DEF-001",
      "name": "API Availability",
      "description": "API service availability SLO",
      "metric_type": "availability",
      "threshold": 99.9,
      "operator": "gte",
      "window": "30d",
      "alerting": true,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

#### POST /api/v1/slo/definitions
Create a new SLO definition.

**Request Body:**
```json
{
  "name": "API Availability",
  "description": "API service availability SLO",
  "metric_type": "availability",
  "threshold": 99.9,
  "operator": "gte",
  "window": "30d",
  "alerting": true
}
```

#### GET /api/v1/slo/definitions/{definition_id}
Get a single SLO definition by ID.

#### PATCH /api/v1/slo/definitions/{definition_id}
Update an existing SLO definition.

#### DELETE /api/v1/slo/definitions/{definition_id}
Delete an SLO definition.

### 2. SLO Metrics

#### GET /api/v1/slo/metrics
Get SLO metrics for all or specific service.

**Query Parameters:**
- `service` (optional): Filter by service name

**Response:**
```json
{
  "metrics": [
    {
      "name": "API Availability",
      "service": "api-service",
      "metric_type": "availability",
      "current": 99.95,
      "target": 99.9,
      "trend": "up",
      "history": [95, 96, 97, 98, 99]
    }
  ]
}
```

### 3. SLO Budgets

#### GET /api/v1/slo/budgets
Get error budgets for all SLOs.

**Response:**
```json
{
  "budgets": [
    {
      "slo_id": "SLO-001",
      "slo_name": "API Availability",
      "service": "api-service",
      "target": 99.9,
      "current": 99.95,
      "error_budget_remaining": 50.0,
      "error_budget_consumed": 50.0,
      "window": "30d",
      "status": "healthy"
    }
  ]
}
```

### 4. SLO Burn Rates

#### GET /api/v1/slo/burn-rates
Get burn rates for all SLOs.

**Response:**
```json
{
  "burn_rates": [
    {
      "slo_id": "SLO-001",
      "slo_name": "API Availability",
      "service": "api-service",
      "burn_rate_1h": 0.05,
      "burn_rate_24h": 0.04,
      "burn_rate_7d": 0.03,
      "status": "healthy",
      "window": "30d"
    }
  ]
}
```

### 5. SLO Error Budgets (Detailed)

#### GET /api/v1/slo/error-budgets
Get detailed error budget information including estimated time remaining.

**Response:**
```json
{
  "error_budgets": [
    {
      "slo_id": "SLO-001",
      "slo_name": "API Availability",
      "service": "api-service",
      "target": 99.9,
      "current": 99.95,
      "error_budget_remaining_percent": 50.0,
      "error_budget_consumed_percent": 50.0,
      "burn_rate": 0.05,
      "estimated_hours_remaining": 1000.0,
      "status": "healthy",
      "window": "30d"
    }
  ]
}
```

### 6. SLO Alerts

#### GET /api/v1/slo/alerts
List SLO alerts, optionally filtered by status or severity.

**Query Parameters:**
- `status` (optional): Filter by status (open, resolved)
- `severity` (optional): Filter by severity (critical, major, minor)

**Response:**
```json
{
  "alerts": [
    {
      "id": "ALT-001",
      "slo_id": "SLO-001",
      "slo_name": "API Availability",
      "severity": "critical",
      "message": "SLO breached",
      "status": "open",
      "created_at": "2024-01-01T00:00:00",
      "resolved_at": null,
      "metadata": {}
    }
  ]
}
```

#### POST /api/v1/slo/alerts
Create a new SLO alert.

**Request Body:**
```json
{
  "slo_id": "SLO-001",
  "severity": "critical",
  "message": "SLO breached",
  "metadata": {}
}
```

### 7. SLO Reports

#### GET /api/v1/slo/reports
Get SLO compliance reports for the specified period.

**Query Parameters:**
- `period` (optional): Report period (default: "30d")

**Response:**
```json
{
  "reports": [
    {
      "id": "SLA-SLO-001-30d",
      "slo_id": "SLO-001",
      "slo_name": "API Availability",
      "service": "api-service",
      "metric": "availability",
      "period": "30d",
      "availability": 99.95,
      "slaTarget": 99.9,
      "compliance": "compliant",
      "incidents": 0,
      "aggregation": "good_ratio"
    }
  ]
}
```

### 8. SLO Historical Data

#### GET /api/v1/slo/historical-data
Get historical SLO data for analysis.

**Query Parameters:**
- `slo_id` (optional): Filter by SLO ID
- `period` (optional): Historical period (default: "7d")

**Response:**
```json
{
  "historical_data": [
    {
      "slo_id": "SLO-001",
      "slo_name": "API Availability",
      "service": "api-service",
      "metric": "availability",
      "period": "7d",
      "data_points": 168,
      "time_series": [
        {
          "timestamp": "2024-01-01 00:00:00",
          "value": 99.95,
          "count": 60
        }
      ]
    }
  ]
}
```

### 9. SLO Services

#### GET /api/v1/slo/services
List services that have SLOs defined.

**Response:**
```json
{
  "services": [
    {
      "name": "api-service",
      "slo_count": 3,
      "slos": [
        {
          "id": "SLO-001",
          "name": "API Availability",
          "target": 99.9
        }
      ]
    }
  ]
}
```

### 10. SLO Objectives

#### GET /api/v1/slo/objectives
List SLO objectives, optionally filtered by service.

**Query Parameters:**
- `service` (optional): Filter by service name

**Response:**
```json
{
  "objectives": [
    {
      "id": "OBJ-001",
      "name": "API Availability",
      "service": "api-service",
      "metric": "availability",
      "target": 99.9,
      "window": "30d",
      "description": "API service availability objective",
      "current": 99.95,
      "status": "healthy",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

#### POST /api/v1/slo/objectives
Create a new SLO objective and corresponding SLO rule.

**Request Body:**
```json
{
  "name": "API Availability",
  "service": "api-service",
  "metric": "availability",
  "target": 99.9,
  "window": "30d",
  "description": "API service availability objective"
}
```

#### PATCH /api/v1/slo/objectives/{objective_id}
Update an existing SLO objective.

#### DELETE /api/v1/slo/objectives/{objective_id}
Delete an SLO objective and its associated SLO rule.

### 11. SLO Rollups

#### GET /api/v1/slo/rollups
Get rollup aggregations of SLO performance by service and metric.

**Query Parameters:**
- `service` (optional): Filter by service name

**Response:**
```json
{
  "rollups": [
    {
      "service": "api-service",
      "total_slos": 3,
      "healthy_slos": 2,
      "warning_slos": 1,
      "critical_slos": 0,
      "avg_current": 99.8,
      "avg_target": 99.9,
      "metrics": {
        "availability": {
          "count": 2,
          "avg_current": 99.9,
          "avg_target": 99.9
        }
      }
    }
  ]
}
```

## Authentication

All endpoints support authentication via:
1. JWT Bearer token (standard user authentication)
2. Internal API key (for service-to-service communication)

Use the `Authorization: Bearer <token>` header for JWT authentication or `X-Internal-Key: <key>` header for internal API key authentication.

## Authorization

Role-based access control is enforced:
- `admin`: Full access to all endpoints
- `operator`: Can create, update, and delete SLO definitions, objectives, and alerts
- `business`: Can view SLOs and reports for assets they have permission to view
- `viewer`: Read-only access

## Data Models

### SLODefinitionCreate
- `name` (str): SLO definition name
- `description` (str): SLO description
- `metric_type` (str): Metric type (availability, latency, error_rate, throughput)
- `threshold` (float): Threshold value (0-100)
- `operator` (str): Operator (gte, lte, gt, lt)
- `window` (str): Time window (e.g., 1h, 24h, 7d, 30d)
- `alerting` (bool): Whether alerting is enabled

### SLOObjectiveCreate
- `name` (str): Objective name
- `service` (str): Service name
- `metric` (str): Metric name
- `target` (float): Target percentage (0-100)
- `window` (str): Time window
- `description` (str, optional): Objective description

### SLOAlertCreate
- `slo_id` (str): SLO ID
- `severity` (str): Severity (critical, major, minor)
- `message` (str): Alert message
- `metadata` (dict, optional): Additional metadata

## Integration with Existing Code

This router integrates with:
- `core.slo_engine`: SLO rule management and evaluation
- `core.metrics_history`: Metric data storage and querying
- `core.auth_service`: Authentication and authorization
- `core.auth_db`: Asset and user permission management

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200 OK`: Successful GET requests
- `201 Created`: Successful POST requests
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found

Error responses include a `detail` field with a descriptive message.

## Testing

Run the test script to verify the API:
```bash
python test_slo_advanced_api.py
```

## Future Enhancements

Potential improvements:
1. Persistent storage for definitions, objectives, and alerts
2. Real-time alert notifications via webhooks
3. Advanced filtering and pagination
4. Export reports in multiple formats (PDF, CSV)
5. Custom alert rules and thresholds
6. Integration with incident management systems
