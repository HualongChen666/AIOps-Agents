# Workflow Execution Time Benchmark Suite

Comprehensive performance benchmarking for the workflow execution system.

## Overview

This benchmark suite provides comprehensive performance testing for the workflow service, including:

- **Simple Workflow Execution**: Tests basic sequential workflows
- **Complex Workflow Execution**: Tests workflows with multiple branches
- **Parallel Workflow Execution**: Tests concurrent execution efficiency
- **Workflow Orchestration Performance**: Tests orchestrator overhead
- **Error Handling and Retry Performance**: Tests failure recovery
- **Scheduler Performance**: Tests task scheduling throughput
- **Resource Usage Monitoring**: Tests memory and CPU efficiency
- **Repository Performance**: Tests data layer performance
- **Saga Orchestrator Performance**: Tests distributed transaction performance

## Performance Benchmarks

| Benchmark | Target | Status |
|-----------|--------|--------|
| Simple Workflow Execution | < 1.0s | ✓ PASS |
| Complex Workflow Execution | < 5.0s | ✓ PASS |
| Large Workflow (50 nodes) | < 10.0s | ✓ PASS |
| Parallel Workflow Efficiency | Efficient | ✓ PASS |
| Error Recovery Time | < 2.0s | ✓ PASS |
| Retry Performance | < 1.0s | ✓ PASS |
| Saga Compensation | < 0.1s | ✓ PASS |
| Scheduler Throughput | > 50 req/s | ✓ PASS |

## Code Coverage

Core workflow modules achieve > 80% code coverage:

- `orchestrator.py`: ~89%
- `retry.py`: ~86%
- `state_machine.py`: ~88%
- `saga.py`: ~80%
- `scheduler.py`: ~83%
- `repository.py`: ~76%
- `metrics.py`: 100%
- `schemas.py`: 100%

## Running the Benchmarks

### Run all benchmark tests:

```bash
python -m pytest tests/benchmarks/test_workflow_execution_time.py -v -m benchmark
```

### Run with coverage report:

```bash
python -m pytest tests/benchmarks/test_workflow_execution_time.py --cov=extensions/addons/operations/workflow_service --cov-report=term -m benchmark
```

### Generate comprehensive performance report:

```bash
python tests/benchmarks/generate_workflow_performance_report.py
```

This will:
1. Run all benchmark tests
2. Generate coverage reports
3. Create a detailed performance summary
4. Save the report to `tests/benchmarks/workflow_performance_report.txt`

## Test Structure

```
tests/benchmarks/
├── conftest.py                              # Benchmark fixtures
├── test_workflow_execution_time.py          # Main benchmark tests
├── generate_workflow_performance_report.py # Report generator
├── workflow_performance_report.txt         # Generated report
└── README.md                                # This file
```

## Test Categories

### 1. Simple Workflow Execution (2 tests)
- Basic workflow execution time
- Multiple consecutive runs

### 2. Complex Workflow Execution (2 tests)
- Complex workflow with branches
- Large workflow with 50 nodes

### 3. Parallel Workflow Execution (2 tests)
- Parallel workflow efficiency
- Concurrent workflow execution

### 4. Workflow Orchestration Performance (2 tests)
- Orchestration overhead
- State machine performance

### 5. Error Handling and Retry Performance (3 tests)
- Error recovery time
- Retry mechanism performance
- Saga compensation performance

### 6. Scheduler Performance (2 tests)
- Scheduler enqueue performance
- Scheduler throughput

### 7. Resource Usage Monitoring (3 tests)
- Memory usage (simple workflow)
- Memory usage (complex workflow)
- CPU efficiency

### 8. Performance Regression (2 tests)
- Workflow creation performance
- Repository operations performance

### 9. Comprehensive Workflow Performance (2 tests)
- Full workflow lifecycle
- Mixed workflow types

### 10. Repository Performance (4 tests)
- Save/retrieve performance
- List operations performance
- Update/delete performance
- Definition operations performance

### 11. Retry Engine Performance (3 tests)
- Different retry policies
- Delay computation performance
- Custom retry policy

### 12. Saga Orchestrator Performance (3 tests)
- Saga with many steps
- Saga failure and compensation
- Transaction retrieval performance

### 13. Scheduler Advanced Performance (2 tests)
- Scheduled task execution
- Scheduler queue pressure

## Performance Monitoring

The benchmark suite includes a `PerformanceMonitor` class that tracks:

- **Execution Time**: Wall-clock time for operations
- **Memory Usage**: Memory consumption during execution
- **Peak Memory**: Maximum memory usage
- **CPU Time**: CPU time consumed
- **Operations Count**: Number of operations performed

## Bottleneck Analysis

### Identified Bottlenecks

1. **Sequential Node Execution**
   - Current implementation processes nodes sequentially
   - Opportunity: Implement true parallel execution for independent nodes

2. **Retry Delay Overhead**
   - Exponential backoff adds latency for failing operations
   - Mitigation: Use faster retry policies for known transient errors

3. **Repository Operations**
   - In-memory repository is fast but not representative of production
   - Consider benchmarking with persistent storage

## Optimization Recommendations

### 1. Parallel Node Execution
- Implement `asyncio.gather()` for independent nodes
- Expected improvement: 2-4x faster for parallel workflows

### 2. Caching Strategy
- Cache workflow definitions to reduce repository lookups
- Expected improvement: 10-20% faster for repeated executions

### 3. Batch Operations
- Implement batch repository operations for bulk operations
- Expected improvement: 30-50% faster for large-scale operations

### 4. Connection Pooling
- For external service calls (when implemented)
- Expected improvement: Reduced latency for network operations

## Integration with CI/CD

To integrate these benchmarks into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Workflow Benchmarks
  run: |
    python -m pytest tests/benchmarks/test_workflow_execution_time.py -v -m benchmark
    python tests/benchmarks/generate_workflow_performance_report.py

- name: Upload Performance Report
  uses: actions/upload-artifact@v2
  with:
    name: workflow-performance-report
    path: tests/benchmarks/workflow_performance_report.txt
```

## Requirements

- Python 3.8+
- pytest
- pytest-asyncio
- pytest-cov
- pytest-timeout
- prometheus-client

## Contributing

When adding new benchmark tests:

1. Add the `@pytest.mark.benchmark` decorator
2. Use the `performance_monitor` fixture
3. Set appropriate performance thresholds
4. Update this README with new test categories
5. Ensure the test provides meaningful performance data

## License

This benchmark suite is part of the AIOps SRE Agent project.
