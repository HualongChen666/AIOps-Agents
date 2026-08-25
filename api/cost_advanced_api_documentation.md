# Cost Advanced API Documentation

## Overview

This document describes the advanced cost management API endpoints implemented in `cost_advanced_router.py`. These endpoints provide comprehensive cost management capabilities including overview, analytics, optimization, budget management, forecasting, reporting, anomaly detection, and alerts.

## Base URL

All endpoints are prefixed with `/api/v1/cost`

## Endpoints

### 1. Cost Overview

**GET** `/api/v1/cost/overview`

Get comprehensive cost overview including total costs, budget status, forecasts, and key metrics.

**Response:**
```json
{
  "total_cost": 1234.56,
  "budget_status": {
    "status": "healthy",
    "alert_level": "low",
    "message": "Budget healthy: 45.2% used",
    "budget": {
      "monthly_budget": 5000.0,
      "current_spend": 2250.0,
      "utilization_percent": 45.0,
      "remaining_budget": 2750.0
    }
  },
  "forecast": {
    "period_days": 30,
    "total_forecast": 2400.0,
    "forecast_data": [...]
  },
  "trends": {
    "direction": "up",
    "percent_change": 5.2
  },
  "metrics": {
    "active_budgets": 2,
    "pending_optimizations": 3,
    "open_anomalies": 1,
    "total_alerts": 2
  },
  "cost_by_service": {
    "Amazon EC2": 800.0,
    "Amazon S3": 200.0,
    "Amazon RDS": 234.56
  },
  "last_updated": "2026-01-15T10:30:00"
}
```

---

### 2. Cost Analytics

**GET** `/api/v1/cost/analytics`

Get detailed cost analytics with grouping and filtering options.

**Query Parameters:**
- `start_date` (optional): Start date in ISO format
- `end_date` (optional): End date in ISO format
- `group_by` (default: "service"): Group by field (service, region, category)
- `granularity` (default: "daily"): Time granularity

**Response:**
```json
{
  "summary": {
    "total_cost": 1234.56,
    "average_cost": 41.15,
    "max_cost": 150.0,
    "min_cost": 10.0,
    "record_count": 30
  },
  "grouped_data": {
    "Amazon EC2": 800.0,
    "Amazon S3": 200.0
  },
  "time_series": [...],
  "insights": [
    "Highest cost service: Amazon EC2 ($800.00)",
    "Costs are trending up (5.2%)"
  ],
  "filters": {...},
  "generated_at": "2026-01-15T10:30:00"
}
```

**POST** `/api/v1/cost/analytics`

Run custom cost analytics with specific parameters.

**Request Body:**
```json
{
  "start_date": "2026-01-01T00:00:00",
  "end_date": "2026-01-31T23:59:59",
  "group_by": "service",
  "granularity": "daily"
}
```

---

### 3. Cost Optimization

**GET** `/api/v1/cost/optimization`

Get list of cost optimization suggestions with potential savings.

**Response:**
```json
{
  "suggestions": [
    {
      "id": "opt-1",
      "resource": "i-0123456789abcdef0 (EC2 Instance)",
      "type": "resize",
      "current_cost": 150.0,
      "projected_savings": 45.0,
      "effort": "low",
      "impact": "medium",
      "description": "Resize instance from m5.large to m5.medium",
      "status": "pending",
      "created_at": "2026-01-15T00:00:00"
    }
  ],
  "summary": {
    "total_suggestions": 2,
    "pending_count": 2,
    "applied_count": 0,
    "dismissed_count": 0,
    "total_potential_savings": 135.0
  },
  "by_type": {...},
  "by_effort": {...}
}
```

**POST** `/api/v1/cost/optimization`

Apply or dismiss a specific optimization suggestion.

**Request Body:**
```json
{
  "resource_id": "opt-1",
  "action": "apply"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully applied optimization for i-0123456789abcdef0",
  "suggestion": {...}
}
```

---

### 4. Budget Management

**GET** `/api/v1/cost/budgets`

Get all budgets with their current status.

**Response:**
```json
{
  "budgets": [
    {
      "id": "budget-1",
      "name": "EC2 Monthly Budget",
      "service": "Amazon EC2",
      "amount": 2000.0,
      "spent": 1450.50,
      "remaining": 549.50,
      "period": "monthly",
      "status": "on_track",
      "alerts_enabled": true,
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-15T00:00:00"
    }
  ],
  "summary": {
    "total_budgets": 2,
    "total_budget_amount": 2500.0,
    "total_spent": 1930.50,
    "total_remaining": 569.50,
    "utilization_percent": 77.22,
    "status_counts": {
      "on_track": 1,
      "warning": 1,
      "exceeded": 0
    }
  }
}
```

**POST** `/api/v1/cost/budgets`

Create a new budget.

**Request Body:**
```json
{
  "name": "Lambda Monthly Budget",
  "service": "AWS Lambda",
  "amount": 100.0,
  "period": "monthly",
  "alerts_enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Budget created successfully",
  "budget": {
    "id": "budget-3",
    "name": "Lambda Monthly Budget",
    "service": "AWS Lambda",
    "amount": 100.0,
    "spent": 0.0,
    "remaining": 100.0,
    "period": "monthly",
    "status": "on_track",
    "alerts_enabled": true,
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-01-15T10:30:00"
  }
}
```

**PATCH** `/api/v1/cost/budgets/{budget_id}`

Update an existing budget.

**Request Body:**
```json
{
  "amount": 150.0,
  "alerts_enabled": false
}
```

**DELETE** `/api/v1/cost/budgets/{budget_id}`

Delete a budget.

**Response:**
```json
{
  "success": true,
  "message": "Budget deleted successfully",
  "deleted_budget": {...}
}
```

---

### 5. Cost Forecasts

**GET** `/api/v1/cost/forecasts`

Get cost forecasts for the specified period.

**Query Parameters:**
- `days` (default: 30, min: 1, max: 365): Number of days to forecast
- `service` (optional): Filter by service

**Response:**
```json
{
  "forecast_period": {
    "days": 30,
    "start_date": "2026-01-15T10:30:00",
    "end_date": "2026-02-14T10:30:00"
  },
  "forecast_data": [
    {
      "timestamp": "2026-01-16T10:30:00",
      "forecasted_cost": 75.5,
      "confidence": "medium",
      "currency": "USD"
    }
  ],
  "summary": {
    "total_forecast": 2265.0,
    "average_daily_forecast": 75.5,
    "historical_average": 72.0,
    "growth_rate_percent": 4.86
  },
  "confidence": "medium",
  "generated_at": "2026-01-15T10:30:00"
}
```

---

### 6. Cost Reports

**GET** `/api/v1/cost/reports`

Get list of available cost reports.

**Response:**
```json
{
  "reports": [...],
  "total_count": 0,
  "retrieved_at": "2026-01-15T10:30:00"
}
```

**POST** `/api/v1/cost/reports`

Generate a cost report for the specified period.

**Request Body:**
```json
{
  "period": "30d",
  "format": "json",
  "include_forecast": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Report generated successfully",
  "report": {
    "id": "report-abc12345",
    "period_start": "2025-12-16T10:30:00",
    "period_end": "2026-01-15T10:30:00",
    "period_days": 30,
    "total_cost": 1234.56,
    "budget": 5000.0,
    "variance": -3765.44,
    "variance_percent": -75.31,
    "by_service": {...},
    "by_category": {...},
    "trends": [...],
    "format": "json",
    "include_forecast": true,
    "created_at": "2026-01-15T10:30:00"
  }
}
```

---

### 7. Cost Anomalies

**GET** `/api/v1/cost/anomalies`

Get detected cost anomalies with filtering options.

**Query Parameters:**
- `severity` (optional): Filter by severity (high, medium, low)
- `status` (optional): Filter by status (open, investigating, resolved)

**Response:**
```json
{
  "anomalies": [
    {
      "id": "anom-1",
      "detected_at": "2026-01-15T10:30:00",
      "service": "Amazon EC2",
      "expected_cost": 100.0,
      "actual_cost": 250.0,
      "deviation_percent": 150.0,
      "severity": "high",
      "description": "Unusual spike in EC2 costs",
      "status": "open"
    }
  ],
  "summary": {
    "total_count": 2,
    "filtered_count": 2,
    "severity_counts": {
      "high": 1,
      "medium": 1,
      "low": 0
    },
    "status_counts": {
      "open": 1,
      "investigating": 1,
      "resolved": 0
    },
    "total_impact": 185.0
  },
  "filters": {...},
  "retrieved_at": "2026-01-15T10:30:00"
}
```

---

### 8. Cost Alerts

**GET** `/api/v1/cost/alerts`

Get cost alerts with filtering options.

**Query Parameters:**
- `enabled` (optional): Filter by enabled status (true/false)

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert-1",
      "name": "Budget Exceeded Alert",
      "type": "budget_exceeded",
      "threshold": 90.0,
      "current_value": 95.0,
      "severity": "critical",
      "enabled": true,
      "notification_channels": ["email", "slack"],
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "summary": {
    "total_count": 2,
    "enabled_count": 2,
    "disabled_count": 0,
    "severity_counts": {
      "critical": 1,
      "high": 1,
      "medium": 0,
      "low": 0
    },
    "type_counts": {
      "budget_exceeded": 1,
      "anomaly_detected": 1
    }
  },
  "filters": {...},
  "retrieved_at": "2026-01-15T10:30:00"
}
```

**POST** `/api/v1/cost/alerts`

Create a new cost alert.

**Request Body:**
```json
{
  "name": "S3 Cost Alert",
  "type": "budget_exceeded",
  "threshold": 80.0,
  "severity": "high",
  "notification_channels": ["email"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Alert created successfully",
  "alert": {
    "id": "alert-3",
    "name": "S3 Cost Alert",
    "type": "budget_exceeded",
    "threshold": 80.0,
    "current_value": 0.0,
    "severity": "high",
    "enabled": true,
    "notification_channels": ["email"],
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-01-15T10:30:00"
  }
}
```

---

## Pydantic Models

### BudgetCreate
```python
class BudgetCreate(BaseModel):
    name: str
    service: str
    amount: float
    period: str = "monthly"
    alerts_enabled: bool = True
```

### BudgetUpdate
```python
class BudgetUpdate(BaseModel):
    name: Optional[str]
    amount: Optional[float]
    period: Optional[str]
    alerts_enabled: Optional[bool]
```

### AnalyticsRequest
```python
class AnalyticsRequest(BaseModel):
    start_date: Optional[str]
    end_date: Optional[str]
    group_by: Optional[str] = "service"
    granularity: Optional[str] = "daily"
```

### OptimizationRequest
```python
class OptimizationRequest(BaseModel):
    resource_id: Optional[str]
    action: str
```

### ReportRequest
```python
class ReportRequest(BaseModel):
    period: str = "30d"
    format: str = "json"
    include_forecast: bool = False
```

### AlertCreate
```python
class AlertCreate(BaseModel):
    name: str
    type: str
    threshold: float
    severity: str = "medium"
    notification_channels: List[str]
```

### AlertUpdate
```python
class AlertUpdate(BaseModel):
    name: Optional[str]
    threshold: Optional[float]
    severity: Optional[str]
    enabled: Optional[bool]
    notification_channels: Optional[List[str]]
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful request
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses follow this format:
```json
{
  "detail": "Error message description"
}
```

---

## Implementation Notes

1. **Data Storage**: The current implementation uses in-memory data storage for demonstration. In production, this should be replaced with a proper database.

2. **Cost Collection**: The endpoints leverage the existing `core.cost_monitor` module for cost data collection and forecasting.

3. **Real Business Logic**: Each endpoint implements actual business logic including:
   - Data aggregation and grouping
   - Trend calculations
   - Status determination based on thresholds
   - CRUD operations for budgets and alerts
   - Report generation with configurable parameters

4. **Validation**: All request inputs are validated using Pydantic models.

5. **Error Handling**: Comprehensive error handling with appropriate HTTP status codes and error messages.

6. **Documentation**: Each endpoint includes docstrings and response schemas for automatic API documentation generation.

---

## Frontend Integration

The frontend pages in `frontend/app/cost/` should be updated to use these new endpoints:

- `page.tsx` → `/api/v1/cost/overview`
- `cost-optimization/page.tsx` → `/api/v1/cost/optimization`
- `budget-management/page.tsx` → `/api/v1/cost/budgets`
- `cost-prediction/page.tsx` → `/api/v1/cost/forecasts`
- `cost-report/page.tsx` → `/api/v1/cost/reports`
- `cost-monitoring/page.tsx` → `/api/v1/cost/analytics`

Note: Some frontend pages currently use different endpoint paths. They should be updated to match the new API structure.
