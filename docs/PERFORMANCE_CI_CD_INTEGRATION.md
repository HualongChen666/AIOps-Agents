# Performance Testing CI/CD Integration Guide

## Overview

This document describes the complete integration of performance testing into the CI/CD pipeline for the AIOps Agent project. The integration ensures that performance regressions are detected early and prevents code with performance issues from being merged.

## Architecture

### Components

1. **GitHub Actions Workflow** (`.github/workflows/performance-test.yml`)
   - Main CI/CD workflow for performance testing
   - Runs on push, pull requests, and daily schedule
   - Includes performance gates and regression detection

2. **Performance Benchmark Script** (`scripts/run_performance_benchmarks.sh`)
   - Shell script for executing performance benchmarks
   - Handles environment setup, dependency installation, and report generation
   - Supports quick and full benchmark modes

3. **Performance Gate Checker** (`scripts/check_performance_gates.py`)
   - Python script for checking performance against quality gates
   - Validates performance, regression, resource usage, and coverage thresholds
   - Returns appropriate exit codes for CI/CD integration

4. **Regression Analyzer** (`scripts/analyze_performance_regression.py`)
   - Analyzes current performance against baseline
   - Detects regressions exceeding configurable thresholds
   - Generates detailed regression reports

5. **Trend Report Generator** (`scripts/generate_performance_trend.py`)
   - Generates HTML trend reports showing performance over time
   - Visualizes historical data with charts
   - Helps identify long-term performance trends

## CI/CD Pipeline Integration

### Main CI Workflow (`.github/workflows/ci.yml`)

The main CI workflow has been updated to trigger performance testing:

```yaml
performance-test:
  runs-on: ubuntu-latest
  needs: [test]
  if: github.event_name == 'push' || github.event_name == 'pull_request'
  
  steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Trigger performance test workflow
      uses: peter-evans/repository-dispatch@v3
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        event-type: performance-test
        client-payload: |
          {
            "ref": "${{ github.ref }}",
            "sha": "${{ github.sha }}",
            "run_full_benchmark": "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}"
          }
```

### Performance Test Workflow (`.github/workflows/performance-test.yml`)

The dedicated performance test workflow includes:

1. **Performance Benchmarks Job**
   - Sets up PostgreSQL and Redis services
   - Runs performance benchmarks using the shell script
   - Analyzes performance regression
   - Checks performance gates
   - Generates trend reports
   - Uploads artifacts and comments on PRs
   - Blocks merge if gates fail

2. **Load Testing Job** (optional)
   - Runs full load tests on main branch or when triggered
   - Uses Locust for stress testing
   - Generates load test reports

3. **Performance Summary Job**
   - Aggregates results from all performance jobs
   - Generates summary in GitHub Actions summary
   - Creates issues on failure

## Performance Gates

### Gate Configuration

Performance gates are configured with the following thresholds:

```python
@dataclass
class GateConfig:
    # Performance thresholds
    max_response_time_ms: float = 1000.0
    min_throughput_ops: float = 100.0
    max_error_rate_percent: float = 5.0
    
    # Resource thresholds
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_disk_percent: float = 90.0
    
    # Coverage threshold
    min_coverage_percent: float = 70.0
    
    # Regression threshold
    max_regression_percent: float = 10.0
```

### Gate Types

1. **Performance Gate**
   - Validates response times against thresholds
   - Checks minimum throughput requirements
   - Evaluates benchmark results

2. **Regression Gate**
   - Compares current performance against baseline
   - Detects regressions exceeding threshold (default 10%)
   - Categorizes regressions by severity (minor, moderate, severe)

3. **Resource Gate**
   - Monitors CPU usage during tests
   - Checks memory consumption
   - Validates disk usage

4. **Coverage Gate**
   - Ensures code coverage meets minimum threshold
   - Reads coverage from coverage.xml
   - Fails if coverage below threshold

### Gate Enforcement

Gates are enforced in the CI/CD pipeline:

```yaml
- name: Check performance gate failure
  if: always()
  run: |
    if [ -f performance_reports/gate_check.json ]; then
      if python -c "import json; data=json.load(open('performance_reports/gate_check.json')); exit(0 if data.get('all_passed', False) else 1)"; then
        echo "✅ All performance gates passed"
      else
        echo "❌ Performance gates failed - blocking merge"
        exit 1
      fi
    else
      echo "⚠️ Gate check report not found"
      exit 1
    fi
```

## Usage

### Running Performance Tests Locally

#### Quick Run
```bash
./scripts/run_performance_benchmarks.sh --quick-run
```

#### Full Run
```bash
./scripts/run_performance_benchmarks.sh --full-run
```

#### Custom Output Directory
```bash
./scripts/run_performance_benchmarks.sh --output-dir /path/to/output
```

#### Skip Setup (for repeated runs)
```bash
./scripts/run_performance_benchmarks.sh --skip-setup
```

### Checking Performance Gates

```bash
python scripts/check_performance_gates.py \
  --report performance_reports/performance_report.json \
  --regression-report performance_reports/regression_analysis.json \
  --coverage-threshold 70 \
  --output performance_reports/gate_check.json
```

### Analyzing Regression

```bash
python scripts/analyze_performance_regression.py \
  --current performance_reports/performance_report.json \
  --baseline performance_history/baseline.json \
  --threshold 10 \
  --output performance_reports/regression_analysis.json
```

### Generating Trend Reports

```bash
python scripts/generate_performance_trend.py \
  --history-dir performance_history \
  --current performance_reports/performance_report.json \
  --output performance_reports/trend_report.html
```

## CI/CD Triggers

### Automatic Triggers

1. **Push to main/develop branches**
   - Runs full performance test suite
   - Updates baseline on main branch
   - Blocks merge if gates fail

2. **Pull Request to main/develop**
   - Runs quick performance test suite
   - Compares against baseline
   - Comments results on PR
   - Blocks merge if gates fail

3. **Daily Schedule (2 AM UTC)**
   - Runs full performance test suite
   - Generates trend reports
   - Creates issues if regressions detected

### Manual Triggers

1. **Workflow Dispatch**
   - Can trigger from GitHub Actions UI
   - Option to run full benchmark suite
   - Useful for ad-hoc performance testing

## Artifacts and Reports

### Generated Artifacts

1. **Performance Reports** (`performance_reports/`)
   - `performance_report.json` - Main performance report
   - `performance_report.html` - HTML visualization
   - `regression_analysis.json` - Regression analysis
   - `gate_check.json` - Gate check results
   - `trend_report.html` - Trend visualization

2. **Benchmark Data** (`.benchmarks/`)
   - Raw benchmark data from pytest-benchmark
   - Historical benchmark comparisons

3. **Performance History** (`performance_history/`)
   - Historical performance data
   - Baseline files
   - Trend analysis data

### Artifact Retention

- Performance reports: 30 days
- Performance history: 90 days
- Load test reports: 30 days

## Notifications

### Pull Request Comments

Performance results are automatically commented on pull requests:

```markdown
## 🚀 Performance Test Results

### Summary
- **Throughput**: 15000 ops/s
- **Avg Latency**: 45.2 ns
- **P99 Latency**: 120.5 ns
- **Duration**: 2.5s

### Regression Analysis
- **Regressions Detected**: 0
- **Status**: ✅ No significant regression

### Quality Gates
- **Performance Gate**: ✅ PASSED
- **Coverage Gate**: ✅ PASSED
- **Resource Gate**: ✅ PASSED
- **Overall Status**: ✅ PASSED
```

### Issue Creation

On performance test failure, an issue is automatically created:

- Title: "Performance Test Failed - {commit_sha}"
- Body: Details about the failure
- Labels: `performance`, `ci-failure`

## Configuration

### Environment Variables

The performance test workflow uses the following environment variables:

```yaml
env:
  PERFORMANCE_REGRESSION_THRESHOLD: 10  # 10% regression threshold
  COVERAGE_THRESHOLD: 70
  PYTHON_VERSION: '3.12'
```

### Service Configuration

PostgreSQL and Redis services are configured for testing:

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: aiops_perf_test
  redis:
    image: redis:7
```

## Troubleshooting

### Common Issues

1. **Performance tests timeout**
   - Increase timeout in benchmark configuration
   - Check resource limits in GitHub Actions
   - Verify service connectivity

2. **Baseline not found**
   - First run will create baseline automatically
   - Check performance_history directory
   - Verify cache configuration

3. **Gate check fails**
   - Review gate_check.json for details
   - Check specific gate that failed
   - Adjust thresholds if needed

4. **Regression detected**
   - Review regression_analysis.json
   - Identify which metrics regressed
   - Investigate code changes causing regression

### Debug Mode

Enable debug logging by setting:

```bash
export DEBUG=1
./scripts/run_performance_benchmarks.sh
```

## Best Practices

1. **Run Locally First**
   - Always run performance tests locally before pushing
   - Use `--quick-run` for faster feedback during development
   - Use `--full-run` before creating PRs

2. **Monitor Trends**
   - Review trend reports regularly
   - Look for gradual performance degradation
   - Address performance issues early

3. **Update Baselines**
   - Baselines update automatically on main branch
   - Manual baseline updates for major performance improvements
   - Document reasons for baseline changes

4. **Threshold Tuning**
   - Adjust thresholds based on application requirements
   - Consider different thresholds for different environments
   - Balance between strictness and practicality

## Maintenance

### Regular Tasks

1. **Review Performance History**
   - Clean up old history files (retention: 90 days)
   - Archive important historical data
   - Monitor storage usage

2. **Update Dependencies**
   - Keep performance testing tools updated
   - Review new features in pytest-benchmark
   - Update threshold configurations as needed

3. **Optimize Test Suite**
   - Remove obsolete benchmarks
   - Add new benchmarks for critical paths
   - Optimize test execution time

## Extending the Integration

### Adding New Benchmarks

1. Create benchmark test in `tests/benchmarks/`
2. Add to benchmark configuration
3. Update gate thresholds if needed
4. Test locally before committing

### Adding New Gates

1. Define gate in `GateConfig` class
2. Implement check method in `PerformanceGateChecker`
3. Add to gate check workflow
4. Update documentation

### Custom Notifications

1. Add notification step in workflow
2. Use GitHub Actions or external services
3. Configure notification content
4. Test notification delivery

## References

- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://github.com/GoogleCloudPlatform/professional-services/tree/main/examples/performance-testing)

## Support

For issues or questions about the performance testing integration:

1. Check this documentation
2. Review workflow logs in GitHub Actions
3. Open an issue with the `performance` label
4. Contact the DevOps team
