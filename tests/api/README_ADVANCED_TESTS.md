# Advanced Router Tests

This directory contains comprehensive test suites for the advanced router modules:

## Test Files

1. **test_alerts_advanced_router.py** - Tests for alert management advanced features
   - Dashboard, configuration, notification channels
   - Prediction, correlation, acknowledgements
   - Escalation, suppression, forwarding rules
   - Webhook configs, intelligent analysis
   - Dynamic threshold, deduplication, aggregation rules
   - Alert routing, rules, third-party integrations

2. **test_ai_advanced_router.py** - Tests for AI analysis features
   - Model Fine-tuning
   - Runbook Generation
   - Intelligent Analysis
   - LangGraph (DSL, Executor, Visualizer, Workflow)
   - Deep Learning
   - Advanced AI Features
   - Model Optimization
   - AI Feedback
   - Knowledge Retrieval
   - Document Index
   - Semantic Search
   - Pattern Matching
   - Cross-layer Tracking
   - Topology Analysis
   - Root Cause Analysis
   - Knowledge Graph
   - Fusion
   - Reranker
   - Vectorizer
   - Retriever
   - RAG Knowledge Base
   - Load Balancer
   - Capability Evaluator
   - Cost Optimizer
   - LLM Router

3. **test_integration_providers_router.py** - Tests for integration provider configurations
   - Microsoft Teams
   - Kafka
   - Cloud Platforms (AWS, Azure, GCP, Alibaba)
   - GitOps (ArgoCD, Flux, Jenkins X)
   - CI/CD (Jenkins, GitLab CI, CircleCI, GitHub Actions)
   - ITSM (ServiceNow, BMC, Cherwell)
   - Oncall (PagerDuty, OpsGenie)
   - Slack
   - Jira
   - ServiceNow
   - Message Queues (RabbitMQ, ActiveMQ, Redis, SQS)
   - GitHub
   - ELK Stack
   - Datadog
   - Grafana
   - Prometheus

## Running the Tests

### Quick Start (Standalone)

Run the simple standalone test to verify basic functionality:

```bash
cd tests/api
python test_advanced_simple.py
```

### Run All Advanced Tests

Use the provided test runner:

```bash
cd tests/api
python run_advanced_tests.py
```

### Run Individual Test Files

```bash
# Alerts advanced router tests
cd tests/api
pytest test_alerts_advanced_router.py -v

# AI advanced router tests
pytest test_ai_advanced_router.py -v

# Integration providers router tests
pytest test_integration_providers_router.py -v
```

### Run with Coverage

```bash
cd tests/api
pytest test_alerts_advanced_router.py --cov=api.alerts_advanced_router --cov-report=html
pytest test_ai_advanced_router.py --cov=api.ai_advanced_router --cov-report=html
pytest test_integration_providers_router.py --cov=api.integration_providers_router --cov-report=html
```

## Test Coverage

The test suites are designed to achieve 90%+ code coverage and include:

- **Normal case testing**: All API endpoints with valid inputs
- **Error case testing**: Invalid inputs, missing fields, validation errors
- **Data validation**: Field validation, type checking, range validation
- **Error handling**: 404 errors, 422 validation errors, 500 server errors
- **Performance testing**: Multiple creates, concurrent operations
- **Security testing**: Sensitive data masking, extra field handling

## Test Structure

Each test file follows this structure:

1. **Test Fixtures**: Reusable test data and client setup
2. **Endpoint Tests**: Tests for each API endpoint (GET, POST, PUT, PATCH, DELETE)
3. **Data Validation Tests**: Field validation and type checking
4. **Error Handling Tests**: Error scenarios and edge cases
5. **Performance Tests**: Load and performance scenarios
6. **Security Tests**: Security-related test cases

## Key Features

- **Mock Support**: Uses unittest.mock to simulate dependencies
- **Independent Testing**: Tests run independently without requiring the full application
- **Comprehensive Coverage**: Tests all CRUD operations for each resource
- **Validation Testing**: Tests Pydantic model validation
- **Error Scenarios**: Tests 404, 422, and 500 error responses
- **Performance**: Tests multiple operations and concurrent access

## Notes

- These tests are designed to run independently of the main application
- They use FastAPI's TestClient for HTTP testing
- CORS middleware is added to the test client to avoid CORS issues
- The tests use the actual router modules from the api package
- Mock objects are used to simulate external dependencies when needed

## Requirements

- pytest
- fastapi
- httpx (or httpx2)
- pytest-asyncio (for async tests)
- pytest-cov (for coverage reports)

## Troubleshooting

If you encounter import errors, ensure:
1. You're running from the project root directory
2. The Python path includes the project root
3. All dependencies are installed: `pip install -r requirements.txt`

For testing without the full application context, use the standalone test runner provided.
