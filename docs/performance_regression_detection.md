# Performance Regression Detection System

## Overview

The Performance Regression Detection System is an enterprise-level solution for automatically detecting performance regressions in your applications. It provides statistical analysis, baseline management, trend analysis, anomaly detection, and comprehensive reporting capabilities.

## Features

### Statistical Detection Algorithms
- **T-Test**: Independent two-sample t-test for comparing means
- **Mann-Whitney U Test**: Non-parametric test for comparing distributions
- **Z-Test**: Large sample mean comparison
- **Percentile Comparison**: Compare specific percentiles (P50, P90, P95, P99)
- **Regression Analysis**: Linear regression for trend detection
- **Change Point Detection**: Detect significant changes in time series
- **Seasonal Decomposition**: Decompose time series into trend, seasonal, and residual components

### Data Management
- **Historical Data Storage**: Persistent storage of performance baselines
- **Baseline Management**: Automatic baseline establishment and updates
- **Data Caching**: In-memory caching for fast access
- **Sample Limiting**: Configurable maximum sample retention

### Analysis Capabilities
- **Trend Analysis**: Detect increasing, decreasing, or stable trends
- **Anomaly Detection**: Z-score and IQR-based outlier detection
- **Confidence Intervals**: Statistical confidence for comparisons
- **Effect Size**: Measure practical significance

### Alerting & Reporting
- **Multiple Alert Channels**: Log, webhook, email, Slack
- **Severity Levels**: Info, Warning, Critical, Blocker
- **Cooldown Period**: Prevent alert spam
- **Comprehensive Reports**: JSON and text report formats
- **CI/CD Integration**: Exit codes for pipeline integration

## Installation

The system is integrated into the existing codebase. Ensure you have the required dependencies:

```bash
pip install numpy scipy
```

## Quick Start

### Basic Usage

```python
from core.performance_regression_detector import PerformanceRegressionDetector

# Initialize detector
detector = PerformanceRegressionDetector(storage_path=".benchmarks/history")

# Establish baseline
detector.establish_baseline(
    test_name="api_response_time",
    metric_type="p95_latency_ms",
    values=[100.0, 105.0, 95.0, 100.0, 105.0]
)

# Detect regression
result = detector.detect_regression(
    test_name="api_response_time",
    metric_type="p95_latency_ms",
    current_values=[110.0, 115.0, 105.0, 110.0, 115.0]
)

if result.detected:
    print(f"Regression detected! Severity: {result.severity.value}")
    print(f"P-value: {result.p_value}")
    print(f"Effect size: {result.effect_size}")
```

### Pytest Integration

```python
import pytest
from tests.benchmarks.regression_integration import RegressionTestHelper

def test_api_performance(regression_helper):
    # Run your performance test
    response_times = measure_api_response_time()
    
    # Check for regression
    result = regression_helper.check_regression(
        test_name="api_response_time",
        metric_type="p95_latency_ms",
        current_values=response_times
    )
    
    # Assert no regression (will fail test if regression detected)
    regression_helper.assert_no_regression(result)
```

## Configuration

### Environment Variables

Configure the system using environment variables:

```bash
# Enable/disable regression detection
export REGRESSION_DETECTION_ENABLED=true

# Auto-update baseline when no regression detected
export AUTO_UPDATE_BASELINE=false

# Fail tests when regression detected
export FAIL_ON_REGRESSION=true

# Storage path for historical data
export REGRESSION_STORAGE_PATH=".benchmarks/history"

# Significance level for statistical tests
export REGRESSION_ALPHA=0.05

# Detection methods to use (comma-separated)
export REGRESSION_METHODS="t_test,mann_whitney_u,percentile_comparison"

# Minimum severity for alerts
export REGRESSION_SEVERITY_THRESHOLD=warning

# Alert configuration
export REGRESSION_ALERT_ENABLED=true
export REGRESSION_ALERT_WEBHOOK="https://your-webhook-url.com"
export REGRESSION_ALERT_SLACK="#alerts"
```

### Alert Configuration

```python
from core.performance_regression_detector import PerformanceRegressionDetector, AlertConfig, RegressionSeverity

alert_config = AlertConfig(
    enabled=True,
    severity_threshold=RegressionSeverity.WARNING,
    notification_channels=["log", "webhook"],
    webhook_url="https://your-webhook-url.com",
    slack_channel="#alerts",
    cooldown_minutes=30
)

detector = PerformanceRegressionDetector(
    storage_path=".benchmarks/history",
    alert_config=alert_config
)
```

## Detection Methods

### T-Test

Best for comparing means when:
- Data is normally distributed
- Sample sizes are small (< 30)
- Variances are similar

```python
from core.performance_regression_detector import DetectionMethod

result = detector.detect_regression(
    test_name="test",
    metric_type="metric",
    current_values=[1.0, 2.0, 3.0],
    methods=[DetectionMethod.T_TEST],
    alpha=0.05
)
```

### Mann-Whitney U Test

Best for:
- Non-normal distributions
- Ordinal data
- Small sample sizes
- When assumptions of t-test are violated

```python
result = detector.detect_regression(
    test_name="test",
    metric_type="metric",
    current_values=[1.0, 2.0, 3.0],
    methods=[DetectionMethod.MANN_WHITNEY_U],
    alpha=0.05
)
```

### Percentile Comparison

Best for:
- Latency percentiles (P95, P99)
- When you care about tail behavior
- Distribution-agnostic

```python
result = detector.detect_regression(
    test_name="test",
    metric_type="metric",
    current_values=[1.0, 2.0, 3.0],
    methods=[DetectionMethod.PERCENTILE_COMPARISON]
)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Performance Regression Tests

on: [push, pull_request]

jobs:
  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run performance tests with regression detection
        env:
          REGRESSION_DETECTION_ENABLED: true
          FAIL_ON_REGRESSION: true
          REGRESSION_STORAGE_PATH: .benchmarks/history
        run: |
          pytest tests/benchmarks/ -v --cov
      
      - name: Upload regression reports
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: regression-reports
          path: .benchmarks/
```

### GitLab CI

```yaml
performance_regression:
  stage: test
  script:
    - pip install -r requirements.txt
    - pytest tests/benchmarks/ -v
  variables:
    REGRESSION_DETECTION_ENABLED: "true"
    FAIL_ON_REGRESSION: "true"
  artifacts:
    paths:
      - .benchmarks/
    when: always
```

### Standalone CI Checker

```python
from tests.benchmarks.regression_integration import CIRegressionChecker

# Initialize checker
checker = CIRegressionChecker()

# Check performance
report = checker.check_and_report(
    test_name="critical_api",
    metric_type="latency",
    current_values=[100.0, 105.0, 95.0]
)

# Get exit code for CI
exit_code = checker.get_exit_code()
exit(exit_code)
```

## Advanced Usage

### Batch Detection

```python
test_data = [
    {"test_name": "api1", "metric_type": "latency", "values": [100.0, 105.0]},
    {"test_name": "api2", "metric_type": "latency", "values": [200.0, 205.0]},
    {"test_name": "api3", "metric_type": "throughput", "values": [1000.0, 1050.0]}
]

results = detector.batch_detect(test_data)

for result in results:
    if result.detected:
        print(f"Regression in {result.test_name}: {result.severity.value}")
```

### Trend Analysis

```python
trend_result = detector.analyze_trend(
    test_name="api_response_time",
    metric_type="latency",
    values=[100.0, 102.0, 104.0, 106.0, 108.0]
)

print(f"Trend: {trend_result['trend']['trend']}")
print(f"Slope: {trend_result['trend']['slope']}")
print(f"R²: {trend_result['trend']['r_squared']}")
```

### Anomaly Detection

```python
anomaly_result = detector.detect_anomalies(
    test_name="api_response_time",
    metric_type="latency",
    values=[100.0, 105.0, 95.0, 100.0, 500.0, 105.0]
)

print(f"Z-score outliers: {anomaly_result['zscore_outliers']}")
print(f"IQR outliers: {anomaly_result['iqr_outliers']}")
print(f"Total anomalies: {anomaly_result['total_anomalies']}")
```

### Report Generation

```python
from core.performance_regression_detector import RegressionReportGenerator

# Generate report
generator = RegressionReportGenerator(detector)

# JSON report
json_report = generator.generate_json_report(results)
print(json_report)

# Text report
text_report = generator.generate_summary_report(results)
print(text_report)

# Save to file
generator.save_report(
    results=results,
    output_path=".benchmarks/regression_report.json",
    format="json"
)
```

## Testing

### Running Tests

```bash
# Run all regression detection tests
pytest tests/benchmarks/test_performance_regression_detector.py -v

# Run integration tests
pytest tests/benchmarks/test_regression_integration.py -v

# Run with coverage
pytest tests/benchmarks/test_performance_regression_detector.py \
       tests/benchmarks/test_regression_integration.py \
       --cov=core.performance_regression_detector \
       --cov=tests.benchmarks.regression_integration \
       --cov-report=html
```

### Test Coverage

The current test coverage is **84.10%** with 102 tests passing.

### Writing Custom Tests

```python
import pytest
from tests.benchmarks.regression_integration import RegressionTestHelper

@pytest.fixture
def regression_helper():
    config = RegressionTestConfig()
    config.storage_path = ".benchmarks/test_history"
    return RegressionTestHelper(config)

def test_custom_performance_metric(regression_helper):
    # Establish baseline
    regression_helper.detector.establish_baseline(
        "custom_metric", "value", [1.0, 1.0, 1.0]
    )
    
    # Test current performance
    current_values = [1.1, 1.1, 1.1]
    result = regression_helper.check_regression(
        "custom_metric", "value", current_values
    )
    
    # Assert no regression
    regression_helper.assert_no_regression(result)
```

## Best Practices

### 1. Baseline Establishment

- Establish baselines with sufficient sample size (≥ 30 samples recommended)
- Use representative workload and conditions
- Update baselines periodically to account for natural performance drift
- Store baselines in version control for reproducibility

### 2. Detection Method Selection

- Use T-Test for normally distributed data with small samples
- Use Mann-Whitney U for non-normal distributions
- Use Percentile Comparison for latency metrics
- Combine multiple methods for robustness

### 3. Threshold Configuration

- Set appropriate significance level (α = 0.05 is standard)
- Configure severity thresholds based on business impact
- Use effect size to distinguish statistical from practical significance
- Consider false positive vs. false negative trade-offs

### 4. Alert Management

- Configure cooldown periods to prevent alert fatigue
- Use multiple notification channels for critical regressions
- Escalate severity based on impact and duration
- Integrate with incident management systems

### 5. CI/CD Integration

- Run regression tests in parallel with functional tests
- Use separate stages for baseline establishment and regression checking
- Store historical data in CI artifacts
- Fail builds only on critical regressions

## Troubleshooting

### No Baseline Available

**Problem**: "No baseline available for comparison" error

**Solution**: Establish a baseline first:
```python
detector.establish_baseline(test_name, metric_type, values)
```

### Insufficient Data

**Problem**: "Insufficient data for t-test" error

**Solution**: Ensure you have enough samples:
- T-Test: ≥ 2 samples per group
- Mann-Whitney U: ≥ 3 samples per group
- Z-Test: ≥ 30 samples per group

### High False Positive Rate

**Problem**: Too many false regressions detected

**Solution**:
- Increase significance level (α)
- Use multiple detection methods
- Adjust severity thresholds
- Increase sample size
- Use effect size filtering

### High False Negative Rate

**Problem**: Missing actual regressions

**Solution**:
- Decrease significance level (α)
- Add more detection methods
- Lower severity thresholds
- Check baseline quality
- Review statistical power

## Performance Considerations

### Storage

- Baseline data is stored as pickle files
- Implement sample limiting to manage storage growth
- Use compression for large datasets
- Consider database storage for production use

### Computation

- Statistical tests are O(n) complexity
- Batch processing for multiple tests
- Use caching for repeated queries
- Parallelize independent tests

### Memory

- In-memory caching for frequently accessed baselines
- Lazy loading of historical data
- Stream processing for large datasets
- Monitor memory usage in CI environments

## API Reference

### PerformanceRegressionDetector

Main class for regression detection.

#### Methods

- `establish_baseline(test_name, metric_type, values, timestamps, metadata)` - Establish performance baseline
- `detect_regression(test_name, metric_type, current_values, methods, alpha)` - Detect performance regression
- `batch_detect(test_data, methods, alpha)` - Batch detect regressions
- `analyze_trend(test_name, metric_type, values)` - Analyze performance trends
- `detect_anomalies(test_name, metric_type, values)` - Detect performance anomalies

### RegressionTestHelper

Helper class for pytest integration.

#### Methods

- `check_regression(test_name, metric_type, current_values)` - Check for regression
- `check_performance_result(performance_result, metric_type)` - Check from PerformanceResult
- `assert_no_regression(result)` - Assert no regression detected
- `assert_regression_below_severity(result, max_severity)` - Assert severity below threshold
- `get_summary()` - Get test summary
- `save_report(output_path, format)` - Save regression report

### StatisticalTests

Static methods for statistical tests.

#### Methods

- `t_test(baseline, current, alpha)` - Perform t-test
- `mann_whitney_u_test(baseline, current, alpha)` - Perform Mann-Whitney U test
- `z_test(baseline, current, alpha)` - Perform z-test
- `percentile_comparison(baseline, current, percentile, threshold)` - Compare percentiles

### TrendAnalysis

Static methods for trend analysis.

#### Methods

- `linear_regression(values, timestamps)` - Perform linear regression
- `moving_average(values, window_size)` - Calculate moving average
- `detect_change_point(values, min_size)` - Detect change points
- `seasonal_decomposition(values, period)` - Decompose time series

### AnomalyDetector

Static methods for anomaly detection.

#### Methods

- `detect_outliers_zscore(values, threshold)` - Detect outliers using z-score
- `detect_outliers_iqr(values, multiplier)` - Detect outliers using IQR
- `detect_anomalies_isolation_forest(values, contamination)` - Detect anomalies using isolation forest

## Contributing

When contributing to the regression detection system:

1. Add tests for new features
2. Maintain ≥ 90% code coverage
3. Update documentation
4. Follow existing code style
5. Add examples for new functionality

## License

This system is part of the AIOps SRE Agent project.

## Support

For issues, questions, or contributions, please refer to the main project documentation.
