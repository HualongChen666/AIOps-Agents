#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Trend Report Generator
===================================

Generates HTML trend reports showing performance changes over time.
Visualizes historical performance data with charts and summaries.

Usage:
    python scripts/generate_performance_trend.py --history-dir DIR --current FILE --output FILE
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class PerformanceTrendGenerator:
    """Generates performance trend reports"""
    
    def __init__(self, history_dir: str):
        self.history_dir = Path(history_dir)
        self.history_data: List[Dict[str, Any]] = []
        self.load_history()
    
    def load_history(self):
        """Load historical performance data"""
        if not self.history_dir.exists():
            print(f"Warning: History directory not found: {self.history_dir}")
            return
        
        # Load all JSON files in history directory
        for history_file in sorted(self.history_dir.glob("performance_*.json")):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.history_data.append(data)
            except Exception as e:
                print(f"Warning: Could not load {history_file}: {e}")
        
        print(f"Loaded {len(self.history_data)} historical records")
    
    def extract_metric_series(self, metric_name: str) -> List[Dict[str, Any]]:
        """Extract time series data for a specific metric"""
        series = []
        
        for record in self.history_data:
            timestamp = record.get("timestamp")
            value = None
            
            # Try to extract metric from various locations
            if metric_name in record:
                value = record[metric_name]
            elif "benchmarks" in record:
                benchmarks = record["benchmarks"].get("benchmarks", {})
                for bench_name, bench_data in benchmarks.items():
                    stats = bench_data.get("stats", {})
                    if metric_name in stats:
                        value = stats[metric_name]
                        break
            
            if value is not None:
                series.append({
                    "timestamp": timestamp,
                    "value": value
                })
        
        return series
    
    def calculate_trend(self, series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend statistics for a metric series"""
        if len(series) < 2:
            return {"trend": "insufficient_data"}
        
        values = [s["value"] for s in series]
        
        # Calculate simple trend
        first_value = values[0]
        last_value = values[-1]
        change_percent = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0
        
        # Determine trend direction
        if change_percent > 5:
            trend = "increasing"
        elif change_percent < -5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "change_percent": change_percent,
            "first_value": first_value,
            "last_value": last_value,
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": sum(values) / len(values)
        }
    
    def generate_html_report(self, current_report: Dict[str, Any]) -> str:
        """Generate HTML trend report"""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Trend Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .header h1 {
            color: #333;
            margin: 0;
        }
        .header .subtitle {
            color: #666;
            margin-top: 10px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }
        .summary-card h3 {
            margin: 0 0 10px 0;
            color: #333;
            font-size: 14px;
        }
        .summary-card .value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
        .chart-section {
            margin: 30px 0;
            padding: 20px;
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
        }
        .chart-section h2 {
            margin-top: 0;
            color: #333;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        .trend-indicator {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .trend-increasing {
            background: #d4edda;
            color: #155724;
        }
        .trend-decreasing {
            background: #f8d7da;
            color: #721c24;
        }
        .trend-stable {
            background: #fff3cd;
            color: #856404;
        }
        .table-section {
            margin: 30px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
        }
        tr:hover {
            background: #f5f5f5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Performance Trend Report</h1>
            <div class="subtitle">
                Generated: {timestamp} | 
                Historical Records: {record_count} |
                Commit: {commit}
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Current Throughput</h3>
                <div class="value">{throughput}</div>
            </div>
            <div class="summary-card">
                <h3>Avg Latency</h3>
                <div class="value">{latency}</div>
            </div>
            <div class="summary-card">
                <h3>P99 Latency</h3>
                <div class="value">{p99}</div>
            </div>
            <div class="summary-card">
                <h3>History Size</h3>
                <div class="value">{record_count}</div>
            </div>
        </div>
"""
        
        # Fill in summary values
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit = current_report.get("commit", "N/A")[:8]
        record_count = len(self.history_data)
        throughput = f"{current_report.get('throughput_ops_per_sec', 0):.0f} ops/s"
        latency = f"{current_report.get('avg_latency_ns', 0) / 1_000_000:.2f} ms"
        p99 = f"{current_report.get('p99_latency_ns', 0) / 1_000_000:.2f} ms"
        
        html = html.format(
            timestamp=timestamp,
            record_count=record_count,
            commit=commit,
            throughput=throughput,
            latency=latency,
            p99=p99
        )
        
        # Add charts for key metrics
        metrics_to_chart = [
            ("throughput_ops_per_sec", "Throughput (ops/s)"),
            ("avg_latency_ns", "Average Latency (ns)"),
            ("p99_latency_ns", "P99 Latency (ns)")
        ]
        
        for metric, label in metrics_to_chart:
            series = self.extract_metric_series(metric)
            if len(series) >= 2:
                trend = self.calculate_trend(series)
                html += self._generate_chart_section(metric, label, series, trend)
        
        # Add historical data table
        html += self._generate_history_table()
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def _generate_chart_section(
        self,
        metric: str,
        label: str,
        series: List[Dict[str, Any]],
        trend: Dict[str, Any]
    ) -> str:
        """Generate HTML section for a single chart"""
        trend_class = f"trend-{trend['trend']}"
        
        html = f"""
        <div class="chart-section">
            <h2>{label}</h2>
            <div>
                <span class="trend-indicator {trend_class}">
                    Trend: {trend['trend'].upper()} ({trend['change_percent']:.1f}%)
                </span>
            </div>
            <div class="chart-container">
                <canvas id="chart-{metric}"></canvas>
            </div>
        </div>
"""
        
        # Add chart JavaScript
        labels = [s["timestamp"][:19] for s in series]  # Truncate to datetime
        values = [s["value"] for s in series]
        
        html += f"""
        <script>
        (function() {{
            const ctx = document.getElementById('chart-{metric}').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '{label}',
                        data: {json.dumps(values)},
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false
                        }}
                    }}
                }}
            }});
        }})();
        </script>
"""
        
        return html
    
    def _generate_history_table(self) -> str:
        """Generate HTML table of historical data"""
        html = """
        <div class="table-section">
            <h2>Historical Performance Data</h2>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Commit</th>
                        <th>Throughput (ops/s)</th>
                        <th>Avg Latency (ms)</th>
                        <th>P99 Latency (ms)</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for record in reversed(self.history_data[-20:]):  # Show last 20 records
            timestamp = record.get("timestamp", "N/A")[:19]
            commit = record.get("commit", "N/A")[:8]
            throughput = record.get("throughput_ops_per_sec", 0)
            avg_latency = record.get("avg_latency_ns", 0) / 1_000_000
            p99_latency = record.get("p99_latency_ns", 0) / 1_000_000
            
            html += f"""
                    <tr>
                        <td>{timestamp}</td>
                        <td>{commit}</td>
                        <td>{throughput:.0f}</td>
                        <td>{avg_latency:.2f}</td>
                        <td>{p99_latency:.2f}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
        
        return html


def main():
    parser = argparse.ArgumentParser(description="Generate performance trend report")
    parser.add_argument("--history-dir", required=True, help="Directory containing historical performance data")
    parser.add_argument("--current", required=True, help="Path to current performance report")
    parser.add_argument("--output", required=True, help="Path to output HTML report")
    
    args = parser.parse_args()
    
    # Load current report
    with open(args.current, 'r') as f:
        current_report = json.load(f)
    
    # Generate trend report
    generator = PerformanceTrendGenerator(args.history_dir)
    html = generator.generate_html_report(current_report)
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"Trend report generated: {args.output}")


if __name__ == "__main__":
    main()
