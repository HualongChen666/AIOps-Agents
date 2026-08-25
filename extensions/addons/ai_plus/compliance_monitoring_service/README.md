# Compliance Monitoring Service

Enterprise-grade compliance monitoring service with real-time policy checking, alerting, and reporting capabilities.

## Features

- **Compliance Rule Management**: Define and manage compliance rules across multiple frameworks
- **Policy Checking**: Real-time policy validation against defined compliance standards
- **Alert System**: Automated violation alerts with severity levels
- **Report Generation**: Multi-format compliance reports (JSON, HTML, Markdown, CSV)
- **Trend Analysis**: Compliance trend tracking and analysis
- **Multi-Framework Support**: GDPR, HIPAA, PCI DSS, SOC 2, ISO 27001, NIST

## Supported Compliance Frameworks

- **GDPR** (General Data Protection Regulation)
- **HIPAA** (Health Insurance Portability and Accountability Act)
- **PCI DSS** (Payment Card Industry Data Security Standard)
- **SOC 2** (Service Organization Control 2)
- **ISO 27001** (Information Security Management)
- **NIST** (NIST Cybersecurity Framework)

## Architecture

```
compliance_monitoring_service/
├── main.py                      # FastAPI HTTP server
├── compliance_monitor.py        # Core monitoring logic
├── policy_checker.py           # Policy validation engine
├── report_generator.py         # Report generation
├── grpc/
│   ├── client.py               # gRPC client
│   └── server.py               # gRPC server
├── proto/
│   └── compliance_monitoring.proto  # gRPC protocol definitions
└── config.py                   # Service configuration
```

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /` - Service information

### Compliance Checks
- `POST /checks` - Run compliance check
- `GET /checks/history` - Get check history

### Compliance Rules
- `GET /rules` - List compliance rules
- `POST /rules` - Register custom rule
- `DELETE /rules/{rule_id}` - Delete rule

### Policy Checking
- `GET /policies` - List policies
- `POST /policies/check` - Check specific policy

### Reports
- `POST /reports` - Generate compliance report
- `GET /reports` - List reports
- `GET /reports/{report_id}` - Get specific report
- `DELETE /reports/{report_id}` - Delete report

### Alerts
- `GET /alerts` - List compliance alerts
- `POST /alerts/{alert_id}/acknowledge` - Acknowledge alert

### Trends & Statistics
- `POST /trends` - Get compliance trend analysis
- `GET /statistics` - Get compliance statistics

### Monitoring
- `POST /monitoring/run` - Trigger monitoring cycle

## Configuration

Environment variables:

- `PORT` - HTTP server port (default: 8010)
- `GRPC_PORT` - gRPC server port (default: 50060)
- `AUTO_MONITOR_ENABLED` - Enable auto monitoring (default: true)
- `MONITOR_INTERVAL` - Monitoring interval in seconds (default: 3600)
- `ALERT_THRESHOLD` - Compliance rate threshold for alerts (default: 0.8)
- `LOG_LEVEL` - Logging level (default: INFO)

## Running the Service

### HTTP Server
```bash
python main.py
```

### With Docker
```bash
docker build -t compliance-monitoring-service .
docker run -p 8010:8010 -p 50060:50060 compliance-monitoring-service
```

## Example Usage

### Run Compliance Check
```bash
curl -X POST http://localhost:8010/checks \
  -H "Content-Type: application/json" \
  -d '{"framework": "gdpr"}'
```

### Generate Report
```bash
curl -X POST http://localhost:8010/reports \
  -H "Content-Type: application/json" \
  -d '{
    "framework": "gdpr",
    "period_start": "2024-01-01T00:00:00Z",
    "period_end": "2024-12-31T23:59:59Z",
    "format": "html"
  }'
```

### Get Compliance Trend
```bash
curl -X POST http://localhost:8010/trends \
  -H "Content-Type: application/json" \
  -d '{"framework": "gdpr", "days": 30}'
```

## Integration with Core

This service integrates with:
- `core/compliance.py` - Basic compliance utilities
- `core/compliance_manager.py` - Enterprise compliance management

## Testing

Run the basic test:
```bash
python test_basic.py
```

## License

MIT License
