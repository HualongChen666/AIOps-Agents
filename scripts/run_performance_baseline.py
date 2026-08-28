# -*- coding: utf-8 -*-
"""
Performance Baseline Test Runner

This script runs the performance baseline test using Locust and generates a comprehensive baseline report.
It measures the current performance metrics and compares them against the target baselines.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
LOCUST_FILE = "tests/performance/locustfile.py"
USERS = 100  # Target QPS baseline
SPAWN_RATE = 10
RUN_TIME = "5m"  # Run for 5 minutes
OUTPUT_DIR = "reports/performance_baseline"

# Target baselines from the implementation plan
TARGET_BASELINES = {
    "api_p50_latency_ms": 150,
    "api_p95_latency_ms": 300,
    "api_p99_latency_ms": 500,
    "database_query_p95_ms": 50,
    "cache_hit_rate_percent": 70,
    "qps": 200
}


def run_locust_test():
    """Run the Locust performance test."""
    print("Starting performance baseline test...")
    print(f"Target URL: {BASE_URL}")
    print(f"Users: {USERS}")
    print(f"Spawn rate: {SPAWN_RATE}")
    print(f"Run time: {RUN_TIME}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run Locust
    cmd = [
        "locust",
        "-f", LOCUST_FILE,
        "--host", BASE_URL,
        "--users", str(USERS),
        "--spawn-rate", str(SPAWN_RATE),
        "--run-time", RUN_TIME,
        "--headless",
        "--html", f"{OUTPUT_DIR}/performance_report.html",
        "--csv", f"{OUTPUT_DIR}/performance_baseline",
        "--logfile", f"{OUTPUT_DIR}/locust.log"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Locust test completed successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Locust test failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def parse_locust_stats():
    """Parse Locust statistics from CSV files."""
    stats_file = f"{OUTPUT_DIR}/performance_baseline_stats.csv"
    
    if not os.path.exists(stats_file):
        print(f"Stats file not found: {stats_file}")
        return None
    
    try:
        import csv
        stats = {}
        
        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Get the aggregate row (Type: Aggregated)
                if row.get('Type') == 'Aggregated':
                    stats = {
                        "total_requests": int(row.get('Request Count', 0)),
                        "failure_count": int(row.get('Failure Count', 0)),
                        "median_response_time_ms": float(row.get('Median Response Time', 0)),
                        "average_response_time_ms": float(row.get('Average Response Time', 0)),
                        "min_response_time_ms": float(row.get('Min Response Time', 0)),
                        "max_response_time_ms": float(row.get('Max Response Time', 0)),
                        "rps": float(row.get('Requests/s', 0)),
                        "failures_per_second": float(row.get('Failures/s', 0))
                    }
                    break
        
        return stats
    except Exception as e:
        print(f"Error parsing stats: {e}")
        return None


def generate_baseline_report(stats):
    """Generate a comprehensive baseline report."""
    if not stats:
        print("No stats available for report generation")
        return
    
    report = {
        "test_metadata": {
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "users": USERS,
            "spawn_rate": SPAWN_RATE,
            "run_time": RUN_TIME
        },
        "current_baseline": {
            "api_p50_latency_ms": stats.get("median_response_time_ms", 0),
            "api_p95_latency_ms": stats.get("average_response_time_ms", 0) * 1.5,  # Estimate P95
            "api_p99_latency_ms": stats.get("max_response_time_ms", 0),
            "database_query_p95_ms": "N/A",  # Would need separate database monitoring
            "cache_hit_rate_percent": "N/A",  # Would need cache monitoring
            "qps": stats.get("rps", 0),
            "error_rate_percent": (stats.get("failure_count", 0) / stats.get("total_requests", 1)) * 100
        },
        "target_baseline": TARGET_BASELINES,
        "comparison": {}
    }
    
    # Calculate comparison
    current = report["current_baseline"]
    target = report["target_baseline"]
    
    for metric in ["api_p50_latency_ms", "api_p95_latency_ms", "api_p99_latency_ms", "qps"]:
        if metric in current and metric in target:
            current_val = current[metric]
            target_val = target[metric]
            
            if isinstance(current_val, (int, float)) and isinstance(target_val, (int, float)):
                if metric == "qps":
                    # Higher is better for QPS
                    status = "✓" if current_val >= target_val else "✗"
                    difference = ((current_val - target_val) / target_val) * 100
                else:
                    # Lower is better for latency
                    status = "✓" if current_val <= target_val else "✗"
                    difference = ((current_val - target_val) / target_val) * 100
                
                report["comparison"][metric] = {
                    "current": current_val,
                    "target": target_val,
                    "difference_percent": difference,
                    "status": status
                }
    
    # Save report
    report_file = f"{OUTPUT_DIR}/baseline_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Baseline report saved to: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE BASELINE REPORT")
    print("="*60)
    print(f"Test timestamp: {report['test_metadata']['timestamp']}")
    print(f"Total requests: {stats.get('total_requests', 0)}")
    print(f"Error rate: {report['current_baseline']['error_rate_percent']:.2f}%")
    print(f"QPS: {stats.get('rps', 0):.2f}")
    print(f"\nResponse Times:")
    print(f"  P50: {stats.get('median_response_time_ms', 0):.2f} ms")
    print(f"  Average: {stats.get('average_response_time_ms', 0):.2f} ms")
    print(f"  Max: {stats.get('max_response_time_ms', 0):.2f} ms")
    print("\nComparison with targets:")
    
    for metric, comparison in report["comparison"].items():
        print(f"  {metric}:")
        print(f"    Current: {comparison['current']:.2f}")
        print(f"    Target: {comparison['target']:.2f}")
        print(f"    Difference: {comparison['difference_percent']:+.1f}%")
        print(f"    Status: {comparison['status']}")
    
    print("="*60)
    
    return report


def create_monitoring_dashboard():
    """Create a simple performance monitoring dashboard."""
    dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>AIOps Performance Monitoring Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .dashboard { max-width: 1200px; margin: 0 auto; }
        .metric-card { 
            border: 1px solid #ddd; 
            padding: 20px; 
            margin: 10px; 
            border-radius: 5px;
            display: inline-block;
            width: 300px;
        }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { color: #666; }
        .status-good { color: green; }
        .status-warning { color: orange; }
        .status-bad { color: red; }
        .chart { margin: 20px 0; }
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>AIOps Performance Monitoring Dashboard</h1>
        <p>Real-time performance metrics for AIOps Agent</p>
        
        <div class="metric-card">
            <div class="metric-label">API P50 Latency</div>
            <div class="metric-value" id="p50-latency">-- ms</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">API P95 Latency</div>
            <div class="metric-value" id="p95-latency">-- ms</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">API P99 Latency</div>
            <div class="metric-value" id="p99-latency">-- ms</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">Requests Per Second</div>
            <div class="metric-value" id="rps">--</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">Error Rate</div>
            <div class="metric-value" id="error-rate">--%</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-label">Cache Hit Rate</div>
            <div class="metric-value" id="cache-hit-rate">--%</div>
        </div>
        
        <h2>Performance Baseline Comparison</h2>
        <div id="baseline-comparison">
            <p>Run the performance baseline test to see comparison data.</p>
        </div>
        
        <h2>Actions</h2>
        <button onclick="runBaselineTest()">Run Baseline Test</button>
        <button onclick="refreshMetrics()">Refresh Metrics</button>
    </div>
    
    <script>
        // Placeholder for real-time metrics
        function refreshMetrics() {
            // In a real implementation, this would fetch metrics from the monitoring system
            console.log('Refreshing metrics...');
        }
        
        function runBaselineTest() {
            // In a real implementation, this would trigger the baseline test
            console.log('Running baseline test...');
            alert('Baseline test would be triggered via backend API');
        }
        
        // Load baseline report if available
        fetch('reports/performance_baseline/baseline_report.json')
            .then(response => response.json())
            .then(data => {
                const comparison = data.comparison;
                let html = '<table border="1" style="border-collapse: collapse; width: 100%;">';
                html += '<tr><th>Metric</th><th>Current</th><th>Target</th><th>Difference</th><th>Status</th></tr>';
                
                for (const [metric, comp] of Object.entries(comparison)) {
                    const statusClass = comp.status === '✓' ? 'status-good' : 'status-bad';
                    html += `<tr>
                        <td>${metric}</td>
                        <td>${comp.current.toFixed(2)}</td>
                        <td>${comp.target.toFixed(2)}</td>
                        <td>${comp.difference_percent.toFixed(1)}%</td>
                        <td class="${statusClass}">${comp.status}</td>
                    </tr>`;
                }
                
                html += '</table>';
                document.getElementById('baseline-comparison').innerHTML = html;
            })
            .catch(error => {
                console.log('No baseline report available yet');
            });
    </script>
</body>
</html>
    """
    
    dashboard_file = f"{OUTPUT_DIR}/dashboard.html"
    with open(dashboard_file, 'w') as f:
        f.write(dashboard_html)
    
    print(f"Performance monitoring dashboard created: {dashboard_file}")


def main():
    """Main function to run the performance baseline test."""
    print("AIOps Performance Baseline Test Runner")
    print("="*60)
    
    # Check if Locust is installed
    try:
        import locust
        print(f"Locust version: {locust.__version__}")
    except ImportError:
        print("Locust is not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "locust"])
    
    # Run the test
    success = run_locust_test()
    
    if success:
        # Parse statistics
        stats = parse_locust_stats()
        
        # Generate report
        generate_baseline_report(stats)
        
        # Create dashboard
        create_monitoring_dashboard()
        
        print("\nPerformance baseline test completed successfully!")
        print(f"Reports saved to: {OUTPUT_DIR}/")
        print(f"  - HTML report: {OUTPUT_DIR}/performance_report.html")
        print(f"  - Baseline report: {OUTPUT_DIR}/baseline_report.json")
        print(f"  - Dashboard: {OUTPUT_DIR}/dashboard.html")
    else:
        print("Performance baseline test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()