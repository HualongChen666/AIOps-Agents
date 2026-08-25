# Advanced Service Discovery, Service Mesh, and Service Monitoring API Documentation

## Overview

This document describes the advanced API endpoints for service discovery, service mesh, and service monitoring functionality. These endpoints provide full CRUD operations and integrate with the existing core managers.

## Service Discovery Advanced API

Base Path: `/api/v1/service-discovery`

### Endpoints

#### 1. List Services
- **GET** `/services`
- **Description**: List all registered services with optional filtering
- **Query Parameters**:
  - `status` (optional): Filter by service status
  - `protocol` (optional): Filter by protocol
  - `limit` (optional, default=100): Maximum number of results
  - `offset` (optional, default=0): Offset for pagination
- **Response**: List of services with summary statistics

#### 2. Create Service
- **POST** `/services`
- **Description**: Create a new service
- **Request Body**:
  ```json
  {
    "name": "service-name",
    "host": "localhost",
    "port": 8080,
    "protocol": "http",
    "metadata": {},
    "weight": 1
  }
  ```
- **Response**: Created service with ID

#### 3. Get Service
- **GET** `/services/{service_id}`
- **Description**: Get service details by ID
- **Response**: Service details with discovery information

#### 4. Update Service
- **PATCH** `/services/{service_id}`
- **Description**: Update service details
- **Request Body**: Partial service update data
- **Response**: Updated service

#### 5. Delete Service
- **DELETE** `/services/{service_id}`
- **Description**: Delete service by ID
- **Response**: Deletion confirmation

#### 6. List Health Checks
- **GET** `/health-checks`
- **Description**: List all health checks with optional filtering
- **Query Parameters**:
  - `service_id` (optional): Filter by service ID
  - `status` (optional): Filter by status
- **Response**: List of health checks

#### 7. Create Health Check
- **POST** `/health-checks`
- **Description**: Create a new health check
- **Request Body**:
  ```json
  {
    "service_id": "service-id",
    "check_type": "http",
    "endpoint": "/health",
    "interval_seconds": 30,
    "timeout_seconds": 5,
    "healthy_threshold": 2,
    "unhealthy_threshold": 3
  }
  ```
- **Response**: Created health check

#### 8. List Endpoints
- **GET** `/endpoints`
- **Description**: List all service endpoints
- **Query Parameters**:
  - `service_name` (optional): Filter by service name
  - `healthy_only` (optional, default=false): Only return healthy endpoints
- **Response**: List of endpoints with URLs

#### 9. Register Service Instance
- **POST** `/registration`
- **Description**: Register a service instance
- **Request Body**:
  ```json
  {
    "service_name": "service-name",
    "instance_id": "instance-123",
    "host": "localhost",
    "port": 8080,
    "weight": 1,
    "metadata": {}
  }
  ```
- **Response**: Registration result

#### 10. Deregister Service Instance
- **POST** `/deregistration`
- **Description**: Deregister a service instance
- **Request Body**:
  ```json
  {
    "service_name": "service-name",
    "instance_id": "instance-123"
  }
  ```
- **Response**: Deregistration result

## Service Mesh Advanced API

Base Path: `/api/v1/service-mesh`

### Endpoints

#### 1. List Configurations
- **GET** `/configurations`
- **Description**: List all mesh configurations with optional filtering
- **Query Parameters**:
  - `mesh_type` (optional): Filter by mesh type (istio, linkerd, consul)
  - `status` (optional): Filter by status
  - `limit` (optional, default=100): Maximum number of results
  - `offset` (optional, default=0): Offset for pagination
- **Response**: List of configurations with summary

#### 2. Create Configuration
- **POST** `/configurations`
- **Description**: Create a new mesh configuration
- **Request Body**:
  ```json
  {
    "name": "mesh-config",
    "mesh_type": "istio",
    "namespace": "istio-system",
    "profile": "default",
    "auto_injection_enabled": true,
    "mtls_enabled": true,
    "resource_limits": {},
    "metadata": {}
  }
  ```
- **Response**: Created configuration with mesh ID

#### 3. Get Configuration
- **GET** `/configurations/{config_id}`
- **Description**: Get configuration details by ID
- **Response**: Configuration details

#### 4. Update Configuration
- **PATCH** `/configurations/{config_id}`
- **Description**: Update configuration details
- **Request Body**: Partial configuration update data
- **Response**: Updated configuration

#### 5. Delete Configuration
- **DELETE** `/configurations/{config_id}`
- **Description**: Delete configuration by ID
- **Response**: Deletion confirmation

#### 6. List Traffic Rules
- **GET** `/traffic`
- **Description**: List all traffic rules with optional filtering
- **Query Parameters**:
  - `service_name` (optional): Filter by service name
  - `enabled_only` (optional, default=false): Only return enabled rules
- **Response**: List of traffic rules

#### 7. Create Traffic Rule
- **POST** `/traffic`
- **Description**: Create a new traffic rule
- **Request Body**:
  ```json
  {
    "name": "traffic-rule",
    "service_name": "service-name",
    "match_conditions": {"uri": {"prefix": "/api"}},
    "destination": {"host": "service-name", "subset": "v1"},
    "weight": 100,
    "timeout_seconds": 30,
    "retry_policy": {},
    "fault_injection": {},
    "metadata": {}
  }
  ```
- **Response**: Created traffic rule

#### 8. List Security Policies
- **GET** `/security`
- **Description**: List all security policies with optional filtering
- **Query Parameters**:
  - `policy_type` (optional): Filter by policy type
  - `target_service` (optional): Filter by target service
- **Response**: List of security policies

#### 9. Create Security Policy
- **POST** `/security`
- **Description**: Create a new security policy
- **Request Body**:
  ```json
  {
    "name": "security-policy",
    "policy_type": "authentication",
    "target_service": "service-name",
    "mtls_mode": "STRICT",
    "allowed_principals": [],
    "denied_principals": [],
    "jwt_validation": {},
    "metadata": {}
  }
  ```
- **Response**: Created security policy

#### 10. List Observability Configurations
- **GET** `/observability`
- **Description**: List all observability configurations
- **Query Parameters**:
  - `enabled_only` (optional, default=false): Only return enabled configurations
- **Response**: List of observability configurations

#### 11. Create Observability Configuration
- **POST** `/observability`
- **Description**: Create a new observability configuration
- **Request Body**:
  ```json
  {
    "name": "observability-config",
    "tracing_enabled": true,
    "metrics_enabled": true,
    "access_logging_enabled": true,
    "sampling_rate": 1.0,
    "prometheus_enabled": true,
    "grafana_enabled": false,
    "metadata": {}
  }
  ```
- **Response**: Created observability configuration

#### 12. List Policies
- **GET** `/policies`
- **Description**: List all policies with optional filtering
- **Query Parameters**:
  - `policy_type` (optional): Filter by policy type
  - `target_service` (optional): Filter by target service
  - `enabled_only` (optional, default=false): Only return enabled policies
- **Response**: List of policies

#### 13. Create Policy
- **POST** `/policies`
- **Description**: Create a new policy
- **Request Body**:
  ```json
  {
    "name": "policy",
    "policy_type": "rate-limit",
    "target_service": "service-name",
    "rules": [{"rate": 100, "burst": 200}],
    "enabled": true,
    "metadata": {}
  }
  ```
- **Response**: Created policy

## Service Monitoring Advanced API

Base Path: `/api/v1/service-monitoring`

### Endpoints

#### 1. List Monitored Services
- **GET** `/services`
- **Description**: List all monitored services with optional filtering
- **Query Parameters**:
  - `status` (optional): Filter by service status
  - `limit` (optional, default=100): Maximum number of results
  - `offset` (optional, default=0): Offset for pagination
- **Response**: List of monitored services with summary

#### 2. Get Metrics
- **GET** `/metrics`
- **Description**: Get service metrics with optional filtering and aggregation
- **Query Parameters**:
  - `service_name` (optional): Filter by service name
  - `metric_name` (optional): Filter by metric name
  - `time_range_hours` (optional, default=1): Time range in hours
  - `aggregation` (optional, default="raw"): Aggregation type (raw, avg, min, max, sum)
- **Response**: Service metrics

#### 3. Get SLA Metrics
- **GET** `/sla`
- **Description**: Get service SLA metrics
- **Query Parameters**:
  - `service_name` (optional): Filter by service name
  - `time_range_hours` (optional, default=24): Time range in hours
- **Response**: SLA metrics including availability, latency, error rate

#### 4. List Alerts
- **GET** `/alerts`
- **Description**: List all alerts with optional filtering
- **Query Parameters**:
  - `service_name` (optional): Filter by service name
  - `severity` (optional): Filter by severity
  - `status` (optional): Filter by status (active, resolved, acknowledged)
  - `enabled_only` (optional, default=false): Only return enabled alerts
  - `limit` (optional, default=100): Maximum number of results
  - `offset` (optional, default=0): Offset for pagination
- **Response**: List of alerts

#### 5. Create Alert
- **POST** `/alerts`
- **Description**: Create a new alert
- **Request Body**:
  ```json
  {
    "name": "alert-name",
    "service_name": "service-name",
    "metric_name": "cpu_usage",
    "condition": "greater_than",
    "threshold": 80.0,
    "severity": "warning",
    "description": "Alert description",
    "enabled": true,
    "notification_channels": [],
    "metadata": {}
  }
  ```
- **Response**: Created alert with rule ID

#### 6. List Dashboards
- **GET** `/dashboards`
- **Description**: List all dashboards with optional filtering
- **Query Parameters**:
  - `is_public` (optional): Filter by public status
  - `limit` (optional, default=100): Maximum number of results
  - `offset` (optional, default=0): Offset for pagination
- **Response**: List of dashboards

#### 7. Create Dashboard
- **POST** `/dashboards`
- **Description**: Create a new dashboard
- **Request Body**:
  ```json
  {
    "name": "dashboard-name",
    "description": "Dashboard description",
    "widgets": [
      {
        "type": "metric",
        "title": "CPU Usage",
        "metric": "cpu_usage",
        "service": "service-name"
      }
    ],
    "refresh_interval_seconds": 30,
    "is_public": false,
    "metadata": {}
  }
  ```
- **Response**: Created dashboard

#### 8. Get Dashboard
- **GET** `/dashboards/{dashboard_id}`
- **Description**: Get dashboard details by ID
- **Response**: Dashboard details

#### 9. Update Dashboard
- **PATCH** `/dashboards/{dashboard_id}`
- **Description**: Update dashboard details
- **Request Body**: Partial dashboard update data
- **Response**: Updated dashboard

#### 10. Delete Dashboard
- **DELETE** `/dashboards/{dashboard_id}`
- **Description**: Delete dashboard by ID
- **Response**: Deletion confirmation

#### 11. Get Reports
- **GET** `/reports`
- **Description**: Get monitoring reports
- **Query Parameters**:
  - `service_name` (optional): Filter by service name
  - `report_type` (optional, default="summary"): Report type (summary, detailed, sla)
  - `time_range_hours` (optional, default=24): Time range in hours
- **Response**: Monitoring reports

## Integration with Core Managers

All advanced routers integrate with the existing core managers:

- **Service Discovery Manager**: `core.service_discovery_manager.get_service_discovery_manager()`
- **Service Mesh Manager**: `core.service_mesh_manager.get_service_mesh_manager()`
- **Service Monitoring Manager**: `core.service_monitoring_manager.get_service_monitoring_manager()`

## Error Handling

All endpoints follow a consistent error handling pattern:

- **400 Bad Request**: Invalid request data
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

Error responses follow the format:
```json
{
  "detail": "Error message"
}
```

## Response Format

All successful responses follow the format:
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Testing

A test script is provided at `test_advanced_routers.py` to verify all endpoints:

```bash
python test_advanced_routers.py
```

## Configuration

The advanced routers are enabled when `TOPOLOGY_ENABLED` is set to `true` in the configuration. They are automatically registered in the main application.

## Notes

- All endpoints use in-memory storage for demonstration. In production, replace with a proper database.
- UUIDs are generated for all resources.
- Timestamps are in ISO 8601 format (UTC).
- All endpoints include proper logging for debugging.
- Pydantic models are used for request validation.
