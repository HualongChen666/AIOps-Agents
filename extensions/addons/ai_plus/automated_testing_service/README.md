# Automated Testing Service

A microservice for automated test execution, scheduling, and reporting.

## Features

- **Test Execution**: Run pytest test suites with support for filtering by test IDs and tags
- **Test Scheduling**: Schedule test runs with interval-based or cron-based scheduling
- **Test Reporting**: Generate comprehensive test reports with coverage information
- **Coverage Collection**: Collect and analyze test coverage statistics
- **gRPC Support**: Inter-service communication via gRPC
- **REST API**: HTTP endpoints for all operations

## Architecture

### Components

- `main.py`: FastAPI application with REST endpoints
- `test_runner.py`: Test execution engine using pytest
- `test_scheduler.py`: Async scheduler for scheduled test runs
- `test_reporter.py`: Report generation in JSON and HTML formats
- `grpc/server.py`: gRPC server for inter-service communication
- `grpc/client.py`: gRPC client for calling the service
- `config.py`: Configuration management

### API Endpoints

#### Health & Info
- `GET /health` - Health check
- `GET /info` - Service information

#### Test Suites
- `POST /invoke` with action `create_suite` - Create a test suite
- `POST /invoke` with action `get_suite` - Get a test suite
- `POST /invoke` with action `list_suites` - List all test suites
- `POST /invoke` with action `update_suite` - Update a test suite
- `POST /invoke` with action `delete_suite` - Delete a test suite

#### Test Execution
- `POST /invoke` with action `run_tests` - Run tests for a suite
- `POST /invoke` with action `get_report` - Get a test report
- `POST /invoke` with action `list_reports` - List test reports

#### Scheduling
- `POST /invoke` with action `create_schedule` - Create a test schedule
- `POST /invoke` with action `get_schedule` - Get a schedule
- `POST /invoke` with action `list_schedules` - List schedules
- `POST /invoke` with action `update_schedule` - Update a schedule
- `POST /invoke` with action `delete_schedule` - Delete a schedule

#### Coverage
- `POST /invoke` with action `get_coverage` - Get coverage information

#### RPC
- `POST /rpc/{method}` - Call RPC method
- `GET /rpc` - List available RPC methods

## Configuration

Environment variables:

- `PORT`: HTTP port (default: 8001)
- `HOST`: HTTP host (default: 127.0.0.1)
- `GRPC_PORT`: gRPC port (default: 50051)
- `TEST_TIMEOUT`: Test execution timeout in seconds (default: 300)
- `MAX_CONCURRENT_TESTS`: Maximum concurrent tests (default: 4)
- `TEST_RESULTS_DIR`: Directory for test results (default: ./test_results)
- `COVERAGE_DIR`: Directory for coverage reports (default: ./coverage)
- `SCHEDULER_CHECK_INTERVAL`: Scheduler check interval in seconds (default: 60)
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage

### Starting the Service

```bash
cd extensions/addons/ai_plus/automated_testing_service
python main.py
```

### Creating a Test Suite

```bash
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_suite",
    "payload": {
      "name": "My Test Suite",
      "description": "Example test suite",
      "test_path": "./tests",
      "framework": "pytest"
    }
  }'
```

### Running Tests

```bash
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "action": "run_tests",
    "payload": {
      "suite_id": "<suite_id>",
      "collect_coverage": true
    }
  }'
```

### Creating a Schedule

```bash
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_schedule",
    "payload": {
      "suite_id": "<suite_id>",
      "schedule_type": "interval",
      "schedule_expression": "3600"
    }
  }'
```

## Test Framework Support

The service currently supports:
- **pytest**: Primary test framework with full feature support
- **unittest**: Basic support (can be extended)

## Dependencies

- FastAPI
- pytest
- pytest-cov (for coverage)
- httpx
- uvicorn

## Example Test File

```python
# tests/example_test.py
import pytest

def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2

@pytest.mark.slow
def test_slow_operation():
    import time
    time.sleep(0.1)
    assert True
```

## gRPC Protocol

The gRPC interface is defined in `proto/automated_testing.proto`.

Key services:
- `CreateTestSuite`
- `RunTests`
- `GetTestReport`
- `CreateSchedule`
- `GetCoverage`
