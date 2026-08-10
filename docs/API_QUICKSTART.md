# AIOps Agent API Quick Start Guide

## Overview

AIOps Agent provides a comprehensive REST API for AI-powered operations management, including health monitoring, root cause analysis, alert management, and automated repair capabilities.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require authentication. Include your JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

Health check endpoints allow local access without authentication for Kubernetes probes.

## Quick Start

### 1. Health Check

Check if the service is running:

```bash
curl http://localhost:8000/api/v1/health/ping
```

Response:
```json
{
 "status": "alive"
}
```

### 2. Detailed Health Status

Get comprehensive health status:

```bash
curl http://localhost:8000/api/v1/health/detailed
```

Response:
```json
{
 "status": "healthy",
 "timestamp": "2026-07-02T00:00:00Z",
 "components": {
 "database": {"status": "healthy", "response_time_ms": 5},
 "redis": {"status": "healthy", "response_time_ms": 2},
 "ai_engine": {"status": "healthy", "model_loaded": true}
 },
 "metrics": {
 "cpu_usage": 45.2,
 "memory_usage": 68.3,
 "active_connections": 42
 }
}
```

### 3. AI Root Cause Analysis

Submit a natural language query for AI-powered root cause analysis:

```bash
curl -X POST http://localhost:8000/api/ai/analyze \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer <your_token>" \
 -d '{
 "query": "Why is the server slow?",
 "platform": "linux",
 "include_metrics": true,
 "include_rich_context": true
 }'
```

Response:
```json
{
 "analysis": "High CPU usage detected in python3 process consuming 85% CPU",
 "confidence": 0.92,
 "suggested_actions": [
 "Check process logs for unusual activity",
 "Consider scaling resources",
 "Monitor memory usage"
 ],
 "context_used": {
 "cpu_usage": 85.2,
 "memory_usage": 68.3,
 "top_processes": [
 {"name": "python3", "cpu": 85.2, "memory": 12.5}
 ]
 },
 "timestamp": "2026-07-02T00:00:00Z"
}
```

## Common Endpoints

### Health Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/v1/health/ping` | GET | Simple health check | No |
| `/health` | GET | Kubernetes liveness probe | No |
| `/ready` | GET | Kubernetes readiness probe | No |
| `/api/v1/health/detailed` | GET | Detailed health status | Yes (remote) |
| `/api/v1/health/check` | POST | Trigger fresh health checks | Yes (remote) |

### AI Analysis Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/ai/analyze` | POST | AI root cause analysis | Yes |

### Alert Management

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/alerts` | GET | List all alerts | Yes |
| `/api/alerts/{alert_id}` | GET | Get specific alert | Yes |
| `/api/alerts/{alert_id}/acknowledge` | POST | Acknowledge alert | Yes |

### Repair Operations

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/repair/autoheal` | POST | Trigger autoheal | Yes |
| `/api/repair/{repair_id}` | GET | Get repair status | Yes |

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

Error response format:
```json
{
 "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse. Default limits:
- 100 requests per minute per IP
- 1000 requests per minute per authenticated user

Exceeded limits return `429 Too Many Requests`.

## WebSocket Support

Real-time updates are available via WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/sse/workflow');
ws.onmessage = (event) => {
 console.log('Update:', event.data);
};
```

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For API issues or questions:
- Check the [Architecture Documentation](./ARCHITECTURE.md)
- Review [Deployment Guide](./DEPLOYMENT.md)
- Open an issue in the project repository
