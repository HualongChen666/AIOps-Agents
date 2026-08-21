#!/bin/bash
# -*- coding: utf-8 -*-
"""
Performance Benchmark Execution Script
======================================

This script executes performance benchmarks, collects results, and generates reports.
It handles environment setup, dependency installation, test execution, and reporting.

Usage:
    ./scripts/run_performance_benchmarks.sh [options]

Options:
    --skip-setup       Skip environment setup
    --quick-run        Run quick benchmark subset
    --full-run         Run full benchmark suite
    --output-dir DIR   Specify output directory
"""

set -e  # Exit on error
set -o pipefail  # Catch errors in pipes

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/performance_reports"
BENCHMARK_DIR="${PROJECT_ROOT}/.benchmarks"
HISTORY_DIR="${PROJECT_ROOT}/performance_history"

# Default values
SKIP_SETUP=false
QUICK_RUN=false
FULL_RUN=false
OUTPUT_DIR="$REPORT_DIR"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --quick-run)
            QUICK_RUN=true
            shift
            ;;
        --full-run)
            FULL_RUN=true
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Environment preparation
prepare_environment() {
    log_info "Preparing environment for performance testing..."
    
    # Create necessary directories
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$BENCHMARK_DIR"
    mkdir -p "$HISTORY_DIR"
    
    # Set environment variables
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
    export PYTEST_ADDOPTS=""
    export COVERAGE_FILE=""
    
    log_success "Environment prepared"
}

# Dependency installation
install_dependencies() {
    log_info "Installing dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Install core dependencies
    python -m pip install --upgrade pip setuptools wheel
    
    # Install project dependencies
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    fi
    
    # Install performance testing dependencies
    pip install pytest pytest-asyncio pytest-benchmark pytest-xdist pytest-timeout
    pip install psutil matplotlib pandas
    pip install locust
    
    # Verify installations
    python -c "import pytest; print('pytest:', pytest.__version__)"
    python -c "import psutil; print('psutil:', psutil.__version__)"
    
    log_success "Dependencies installed"
}

# Pre-test checks
run_pre_checks() {
    log_info "Running pre-test checks..."
    
    # Check Python version
    PYTHON_VERSION=$(python --version | awk '{print $2}')
    log_info "Python version: $PYTHON_VERSION"
    
    # Check available memory
    TOTAL_MEM=$(free -m | awk '/Mem:/ {print $2}')
    log_info "Available memory: ${TOTAL_MEM}MB"
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    log_info "CPU cores: $CPU_CORES"
    
    # Check disk space
    DISK_SPACE=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    log_info "Available disk space: $DISK_SPACE"
    
    log_success "Pre-test checks completed"
}

# Execute performance benchmarks
run_benchmarks() {
    log_info "Running performance benchmarks..."
    
    cd "$PROJECT_ROOT"
    
    # Build pytest command based on run mode
    PYTEST_CMD="python -m pytest tests/benchmarks/ -v --tb=short --no-cov"
    
    if [ "$QUICK_RUN" = true ]; then
        log_info "Running quick benchmark subset..."
        PYTEST_CMD="$PYTEST_CMD -k 'quick or smoke'"
    elif [ "$FULL_RUN" = true ] || [ "$RUN_FULL_BENCHMARK" = "true" ]; then
        log_info "Running full benchmark suite..."
        PYTEST_CMD="$PYTEST_CMD --benchmark-only"
    else
        log_info "Running standard benchmark suite..."
        PYTEST_CMD="$PYTEST_CMD -m 'benchmark'"
    fi
    
    # Add benchmark-specific options
    PYTEST_CMD="$PYTEST_CMD --benchmark-autosave"
    PYTEST_CMD="$PYTEST_CMD --benchmark-save=$BENCHMARK_DIR/latest"
    PYTEST_CMD="$PYTEST_CMD --benchmark-save-data"
    PYTEST_CMD="$PYTEST_CMD --benchmark-json=$OUTPUT_DIR/benchmark_results.json"
    PYTEST_CMD="$PYTEST_CMD --benchmark-columns=min,max,mean,stddev,median,rounds"
    
    # Run benchmarks
    log_info "Executing: $PYTEST_CMD"
    eval $PYTEST_CMD
    BENCHMARK_EXIT_CODE=$?
    
    if [ $BENCHMARK_EXIT_CODE -eq 0 ]; then
        log_success "Benchmarks completed successfully"
    else
        log_error "Benchmarks failed with exit code: $BENCHMARK_EXIT_CODE"
    fi
    
    return $BENCHMARK_EXIT_CODE
}

# Run performance tests
run_performance_tests() {
    log_info "Running performance tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run the existing performance test script
    if [ -f scripts/run_performance_tests.py ]; then
        python scripts/run_performance_tests.py
        PERF_EXIT_CODE=$?
    else
        log_warning "Performance test script not found, skipping..."
        PERF_EXIT_CODE=0
    fi
    
    return $PERF_EXIT_CODE
}

# Collect resource usage metrics
collect_resource_metrics() {
    log_info "Collecting resource usage metrics..."
    
    METRICS_FILE="$OUTPUT_DIR/resource_metrics.json"
    
    python << EOF
import json
import psutil
import time
from datetime import datetime

# Collect system metrics
metrics = {
    "timestamp": datetime.now().isoformat(),
    "cpu": {
        "percent": psutil.cpu_percent(interval=1),
        "count": psutil.cpu_count(),
        "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
    },
    "memory": {
        "total": psutil.virtual_memory().total,
        "available": psutil.virtual_memory().available,
        "percent": psutil.virtual_memory().percent,
        "used": psutil.virtual_memory().used
    },
    "disk": {
        "total": psutil.disk_usage('/').total,
        "used": psutil.disk_usage('/').used,
        "free": psutil.disk_usage('/').free,
        "percent": psutil.disk_usage('/').percent
    },
    "network": {
        "bytes_sent": psutil.net_io_counters().bytes_sent,
        "bytes_recv": psutil.net_io_counters().bytes_recv,
        "packets_sent": psutil.net_io_counters().packets_sent,
        "packets_recv": psutil.net_io_counters().packets_recv
    }
}

with open('$METRICS_FILE', 'w') as f:
    json.dump(metrics, f, indent=2, default=str)

print("Resource metrics collected")
EOF
    
    log_success "Resource metrics collected"
}

# Generate performance report
generate_report() {
    log_info "Generating performance report..."
    
    cd "$PROJECT_ROOT"
    
    REPORT_FILE="$OUTPUT_DIR/performance_report.json"
    
    # Combine benchmark results and resource metrics
    python << EOF
import json
import os
from datetime import datetime

report = {
    "timestamp": datetime.now().isoformat(),
    "commit": os.environ.get('GITHUB_SHA', 'unknown'),
    "branch": os.environ.get('GITHUB_REF_NAME', 'unknown'),
    "run_mode": "full" if os.environ.get('RUN_FULL_BENCHMARK') == 'true' else "standard"
}

# Load benchmark results if available
benchmark_file = "$OUTPUT_DIR/benchmark_results.json"
if os.path.exists(benchmark_file):
    with open(benchmark_file, 'r') as f:
        benchmark_data = json.load(f)
        report["benchmarks"] = benchmark_data

# Load resource metrics if available
metrics_file = "$OUTPUT_DIR/resource_metrics.json"
if os.path.exists(metrics_file):
    with open(metrics_file, 'r') as f:
        metrics_data = json.load(f)
        report["resource_metrics"] = metrics_data

# Load existing performance report if available
existing_report = "$OUTPUT_DIR/performance_report.json"
if os.path.exists(existing_report):
    try:
        with open(existing_report, 'r') as f:
            existing_data = json.load(f)
            if "throughput_ops_per_sec" in existing_data:
                report["throughput_ops_per_sec"] = existing_data["throughput_ops_per_sec"]
            if "avg_latency_ns" in existing_data:
                report["avg_latency_ns"] = existing_data["avg_latency_ns"]
            if "p99_latency_ns" in existing_data:
                report["p99_latency_ns"] = existing_data["p99_latency_ns"]
            if "duration_seconds" in existing_data:
                report["duration_seconds"] = existing_data["duration_seconds"]
    except:
        pass

with open('$REPORT_FILE', 'w') as f:
    json.dump(report, f, indent=2, default=str)

print("Performance report generated")
EOF
    
    log_success "Performance report generated: $REPORT_FILE"
}

# Generate HTML report
generate_html_report() {
    log_info "Generating HTML report..."
    
    HTML_FILE="$OUTPUT_DIR/performance_report.html"
    
    python << EOF
import json
from datetime import datetime

report_file = "$OUTPUT_DIR/performance_report.json"
with open(report_file, 'r') as f:
    data = json.load(f)

html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e9f7ef; border-radius: 3px; }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Performance Test Report</h1>
        <p><strong>Timestamp:</strong> {data.get('timestamp', 'N/A')}</p>
        <p><strong>Commit:</strong> {data.get('commit', 'N/A')}</p>
        <p><strong>Branch:</strong> {data.get('branch', 'N/A')}</p>
    </div>
"""

# Add resource metrics if available
if 'resource_metrics' in data:
    html += """
    <div class="section">
        <h2>Resource Metrics</h2>
        <div class="metric">
            <strong>CPU:</strong> {cpu_percent}%
        </div>
        <div class="metric">
            <strong>Memory:</strong> {memory_percent}%
        </div>
        <div class="metric">
            <strong>Disk:</strong> {disk_percent}%
        </div>
    </div>
    """.format(
        cpu_percent=data['resource_metrics'].get('cpu', {}).get('percent', 0),
        memory_percent=data['resource_metrics'].get('memory', {}).get('percent', 0),
        disk_percent=data['resource_metrics'].get('disk', {}).get('percent', 0)
    )

# Add benchmark results if available
if 'benchmarks' in data:
    html += """
    <div class="section">
        <h2>Benchmark Results</h2>
        <table>
            <tr>
                <th>Test</th>
                <th>Min</th>
                <th>Max</th>
                <th>Mean</th>
                <th>StdDev</th>
                <th>Median</th>
            </tr>
    """
    
    benchmarks = data['benchmarks'].get('benchmarks', {})
    for bench_name, bench_data in benchmarks.items():
        stats = bench_data.get('stats', {})
        html += f"""
            <tr>
                <td>{bench_name}</td>
                <td>{stats.get('min', 'N/A')}</td>
                <td>{stats.get('max', 'N/A')}</td>
                <td>{stats.get('mean', 'N/A')}</td>
                <td>{stats.get('stddev', 'N/A')}</td>
                <td>{stats.get('median', 'N/A')}</td>
            </tr>
        """
    
    html += """
        </table>
    </div>
    """

html += """
</body>
</html>
"""

with open('$HTML_FILE', 'w') as f:
    f.write(html)

print("HTML report generated")
EOF
    
    log_success "HTML report generated: $HTML_FILE"
}

# Store results in history
store_history() {
    log_info "Storing results in history..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    HISTORY_FILE="$HISTORY_DIR/performance_${TIMESTAMP}.json"
    
    cp "$OUTPUT_DIR/performance_report.json" "$HISTORY_FILE"
    
    # Keep only last 30 history files
    cd "$HISTORY_DIR"
    ls -t performance_*.json | tail -n +31 | xargs -r rm
    
    log_success "Results stored in history: $HISTORY_FILE"
}

# Cleanup
cleanup() {
    log_info "Cleaning up temporary files..."
    
    # Remove temporary files
    find "$OUTPUT_DIR" -name "*.tmp" -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting performance benchmark execution..."
    log_info "Output directory: $OUTPUT_DIR"
    
    # Environment preparation
    if [ "$SKIP_SETUP" = false ]; then
        prepare_environment
        install_dependencies
    fi
    
    run_pre_checks
    
    # Execute tests
    run_benchmarks
    BENCHMARK_EXIT=$?
    
    run_performance_tests
    PERF_EXIT=$?
    
    # Collect metrics and generate reports
    collect_resource_metrics
    generate_report
    generate_html_report
    store_history
    
    cleanup
    
    # Determine final exit code
    if [ $BENCHMARK_EXIT -ne 0 ] || [ $PERF_EXIT -ne 0 ]; then
        log_error "Performance tests failed"
        exit 1
    else
        log_success "Performance tests completed successfully"
        exit 0
    fi
}

# Run main function
main
