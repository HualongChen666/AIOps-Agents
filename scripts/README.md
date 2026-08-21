# CI/CD Scripts

This directory contains various scripts for CI/CD automation, testing, and quality assurance.

## Performance Testing Scripts

### run_performance_benchmarks.sh
Main script for executing performance benchmarks in CI/CD.

**Usage:**
```bash
./scripts/run_performance_benchmarks.sh [options]
```

**Options:**
- `--skip-setup` - Skip environment setup (for repeated runs)
- `--quick-run` - Run quick benchmark subset
- `--full-run` - Run full benchmark suite
- `--output-dir DIR` - Specify output directory

**Example:**
```bash
./scripts/run_performance_benchmarks.sh --quick-run --output-dir /tmp/perf
```

### check_performance_gates.py
Validates performance results against quality gates.

**Usage:**
```bash
python scripts/check_performance_gates.py \
  --report performance_reports/performance_report.json \
  --regression-report performance_reports/regression_analysis.json \
  --coverage-threshold 70 \
  --output performance_reports/gate_check.json
```

**Options:**
- `--report FILE` - Path to performance report JSON (required)
- `--regression-report FILE` - Path to regression analysis JSON
- `--coverage-threshold N` - Minimum coverage percentage (default: 70)
- `--output FILE` - Path to output gate check JSON
- `--max-response-time N` - Maximum response time in ms (default: 1000)
- `--min-throughput N` - Minimum throughput in ops/s (default: 100)
- `--max-cpu N` - Maximum CPU usage percentage (default: 80)
- `--max-memory N` - Maximum memory usage percentage (default: 85)

### analyze_performance_regression.py
Analyzes current performance against baseline to detect regressions.

**Usage:**
```bash
python scripts/analyze_performance_regression.py \
  --current performance_reports/performance_report.json \
  --baseline performance_history/baseline.json \
  --threshold 10 \
  --output performance_reports/regression_analysis.json
```

**Options:**
- `--current FILE` - Path to current performance report (required)
- `--baseline FILE` - Path to baseline performance report (required)
- `--threshold N` - Regression threshold percentage (default: 10)
- `--output FILE` - Path to output analysis JSON
- `--min-samples N` - Minimum samples for statistical significance (default: 3)

### generate_performance_trend.py
Generates HTML trend reports showing performance changes over time.

**Usage:**
```bash
python scripts/generate_performance_trend.py \
  --history-dir performance_history \
  --current performance_reports/performance_report.json \
  --output performance_reports/trend_report.html
```

**Options:**
- `--history-dir DIR` - Directory containing historical performance data (required)
- `--current FILE` - Path to current performance report (required)
- `--output FILE` - Path to output HTML report (required)

## Other Scripts

### run_performance_tests.py
Existing script for running performance tests separately without xdist/coverage interference.

**Usage:**
```bash
python scripts/run_performance_tests.py [extra pytest args]
```

## Dependencies

All performance testing scripts require:
- Python 3.10+
- pytest
- pytest-benchmark
- pytest-asyncio
- psutil
- matplotlib
- pandas

Install with:
```bash
pip install pytest pytest-benchmark pytest-asyncio psutil matplotlib pandas
```

## Output Structure

```
performance_reports/
├── performance_report.json       # Main performance report
├── performance_report.html      # HTML visualization
├── regression_analysis.json     # Regression analysis
├── gate_check.json              # Gate check results
└── trend_report.html            # Trend visualization

.benchmarks/
└── [pytest-benchmark data]      # Raw benchmark data

performance_history/
├── baseline.json                 # Current baseline
└── performance_*.json           # Historical records
```

## CI/CD Integration

These scripts are integrated into the GitHub Actions workflow:
- `.github/workflows/performance-test.yml` - Main performance testing workflow
- `.github/workflows/ci.yml` - Main CI workflow (triggers performance tests)

See `docs/PERFORMANCE_CI_CD_INTEGRATION.md` for detailed integration documentation.

## Troubleshooting

### Script Permission Issues
On Linux/Mac, ensure the shell script is executable:
```bash
chmod +x scripts/run_performance_benchmarks.sh
```

On Windows, use Git Bash or WSL to run shell scripts.

### Missing Dependencies
Install required packages:
```bash
pip install -r requirements.txt
pip install pytest pytest-benchmark pytest-asyncio psutil matplotlib pandas
```

### Baseline Not Found
The first run will automatically create a baseline. For subsequent runs, ensure:
- `performance_history/` directory exists
- Baseline file is accessible
- Cache is properly configured in CI/CD

### Gate Check Failures
Review the gate check JSON file for details:
```bash
cat performance_reports/gate_check.json
```

Check which specific gate failed and adjust thresholds or code accordingly.

## Contributing

When adding new performance testing scripts:
1. Follow the existing naming convention
2. Add usage documentation to this README
3. Include command-line argument parsing
4. Generate JSON output for CI/CD integration
5. Return appropriate exit codes (0 for success, 1 for failure)
6. Update the integration documentation

## Support

For issues or questions:
- Check the integration documentation: `docs/PERFORMANCE_CI_CD_INTEGRATION.md`
- Review GitHub Actions workflow logs
- Open an issue with the `performance` label
