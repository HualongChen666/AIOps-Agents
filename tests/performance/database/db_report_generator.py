# -*- coding: utf-8 -*-
"""
Database Performance Report Generator
数据库性能测试报告生成器
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class DatabasePerformanceMetric:
    """数据库性能指标"""

    operation: str
    data_volume: str
    mean_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput_ops: float
    success_rate: float


class DatabaseReportGenerator:
    """数据库性能报告生成器"""

    def __init__(self, output_dir: str = "tests/performance/database/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_html_report(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """生成HTML报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database = metadata.get("database", "PostgreSQL") if metadata else "PostgreSQL"
        environment = metadata.get("environment", "N/A") if metadata else "N/A"

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIOps Agent 数据库性能测试报告</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metadata {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .success {{
            color: #28a745;
            font-weight: bold;
        }}
        .warning {{
            color: #ffc107;
            font-weight: bold;
        }}
        .danger {{
            color: #dc3545;
            font-weight: bold;
        }}
        .summary {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .summary-card {{
            background-color: #007bff;
            color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            min-width: 150px;
        }}
        .summary-card h3 {{
            margin: 0;
            font-size: 24px;
        }}
        .summary-card p {{
            margin: 5px 0 0 0;
            font-size: 14px;
        }}
        .section {{
            margin: 30px 0;
        }}
        .chart-placeholder {{
            background-color: #e9ecef;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 5px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AIOps Agent 数据库性能测试报告</h1>

        <div class="metadata">
            <p><strong>生成时间:</strong> {timestamp}</p>
            <p><strong>数据库:</strong> {database}</p>
            <p><strong>测试环境:</strong> {environment}</p>
        </div>

        <h2>测试摘要</h2>
        <div class="summary">
            <div class="summary-card">
                <h3>{data.get('total_tests', 0)}</h3>
                <p>总测试数</p>
            </div>
            <div class="summary-card">
                <h3>{data.get('passed_tests', 0)}</h3>
                <p>通过测试</p>
            </div>
            <div class="summary-card">
                <h3>{data.get('failed_tests', 0)}</h3>
                <p>失败测试</p>
            </div>
            <div class="summary-card">
                <h3>{data.get('total_duration', 0):.2f}s</h3>
                <p>总耗时</p>
            </div>
        </div>

        <div class="section">
            <h2>CRUD操作性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>操作</th>
                        <th>数据量</th>
                        <th>平均时间(ms)</th>
                        <th>最小时间(ms)</th>
                        <th>最大时间(ms)</th>
                        <th>标准差(ms)</th>
                        <th>吞吐量(ops/s)</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        crud_metrics = data.get("crud_metrics", [])
        for metric in crud_metrics:
            status_class = (
                "success"
                if metric["mean_time_ms"] < 100
                else "warning" if metric["mean_time_ms"] < 500 else "danger"
            )
            status = (
                "优秀"
                if metric["mean_time_ms"] < 100
                else "良好" if metric["mean_time_ms"] < 500 else "需优化"
            )

            html += f"""
                <tr>
                    <td>{metric['operation']}</td>
                    <td>{metric['data_volume']}</td>
                    <td>{metric['mean_time_ms']:.2f}</td>
                    <td>{metric['min_time_ms']:.2f}</td>
                    <td>{metric['max_time_ms']:.2f}</td>
                    <td>{metric['std_dev_ms']:.2f}</td>
                    <td>{metric['throughput_ops']:.2f}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>连接池性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>测试项</th>
                        <th>并发数</th>
                        <th>平均时间(ms)</th>
                        <th>最优池大小</th>
                        <th>连接泄漏</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        pool_metrics = data.get("pool_metrics", [])
        for metric in pool_metrics:
            status_class = (
                "success"
                if metric["avg_time_ms"] < 10
                else "warning" if metric["avg_time_ms"] < 50 else "danger"
            )
            status = (
                "优秀"
                if metric["avg_time_ms"] < 10
                else "良好" if metric["avg_time_ms"] < 50 else "需优化"
            )

            html += f"""
                <tr>
                    <td>{metric['test_name']}</td>
                    <td>{metric['concurrency']}</td>
                    <td>{metric['avg_time_ms']:.2f}</td>
                    <td>{metric.get('optimal_pool_size', 'N/A')}</td>
                    <td>{metric.get('connection_leak', 0)}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>事务性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>事务类型</th>
                        <th>数据量</th>
                        <th>平均时间(ms)</th>
                        <th>单条vs批量提升</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        tx_metrics = data.get("transaction_metrics", [])
        for metric in tx_metrics:
            status_class = (
                "success"
                if metric["mean_time_ms"] < 100
                else "warning" if metric["mean_time_ms"] < 500 else "danger"
            )
            status = (
                "优秀"
                if metric["mean_time_ms"] < 100
                else "良好" if metric["mean_time_ms"] < 500 else "需优化"
            )

            improvement = metric.get("improvement", 0)
            improvement_str = f"{improvement:.1f}%" if improvement > 0 else "N/A"

            html += f"""
                <tr>
                    <td>{metric['transaction_type']}</td>
                    <td>{metric['data_volume']}</td>
                    <td>{metric['mean_time_ms']:.2f}</td>
                    <td>{improvement_str}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>索引性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>查询类型</th>
                        <th>有索引(ms)</th>
                        <th>无索引(ms)</th>
                        <th>性能提升</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        index_metrics = data.get("index_metrics", [])
        for metric in index_metrics:
            improvement = metric.get("improvement", 0)
            status_class = (
                "success" if improvement > 50 else "warning" if improvement > 20 else "danger"
            )
            status = "显著" if improvement > 50 else "明显" if improvement > 20 else "不明显"

            html += f"""
                <tr>
                    <td>{metric['query_type']}</td>
                    <td>{metric['indexed_time_ms']:.2f}</td>
                    <td>{metric['non_indexed_time_ms']:.2f}</td>
                    <td>{improvement:.1f}%</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>慢查询分析</h2>
            <table>
                <thead>
                    <tr>
                        <th>查询ID</th>
                        <th>平均时间(ms)</th>
                        <th>调用次数</th>
                        <th>总时间(ms)</th>
                        <th>优化建议</th>
                    </tr>
                </thead>
                <tbody>
"""

        slow_queries = data.get("slow_queries", [])
        for query in slow_queries[:10]:  # 只显示前10个
            suggestions = ", ".join(query.get("suggestions", [])[:2])

            html += f"""
                <tr>
                    <td>{query['query_id'][:20]}</td>
                    <td>{query['mean_time_ms']:.2f}</td>
                    <td>{query['calls']}</td>
                    <td>{query['total_time_ms']:.2f}</td>
                    <td>{suggestions}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>优化建议</h2>
            <ul>
"""

        for suggestion in data.get("optimization_suggestions", []):
            priority_class = (
                "danger"
                if suggestion["priority"] == "high"
                else "warning" if suggestion["priority"] == "medium" else "success"
            )
            priority = suggestion["priority"]
            suggestion_text = suggestion["suggestion"]
            estimated_improvement = suggestion["estimated_improvement"]
            priority_str = priority.upper()
            suggestion_html = (
                f'<li class="{priority_class}">'
                f"<strong>[{priority_str}]</strong> {suggestion_text} "
                f"(预计提升: {estimated_improvement:.1f}%)</li>"
            )
            html += f"""
                {suggestion_html}
"""

        html += """
            </ul>
        </div>

        <p style="margin-top: 30px; color: #666; font-size: 12px;">
            本报告由AIOps Agent数据库性能测试框架自动生成
        </p>
    </div>
</body>
</html>
"""

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = os.path.join(self.output_dir, f"db_performance_report_{timestamp_str}.html")

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)

        return html_file

    def generate_json_report(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """生成JSON报告"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "database": metadata.get("database", "PostgreSQL") if metadata else "PostgreSQL",
                "environment": metadata.get("environment", "N/A") if metadata else "N/A",
            },
            "summary": {
                "total_tests": data.get("total_tests", 0),
                "passed_tests": data.get("passed_tests", 0),
                "failed_tests": data.get("failed_tests", 0),
                "total_duration": data.get("total_duration", 0),
            },
            "crud_metrics": data.get("crud_metrics", []),
            "pool_metrics": data.get("pool_metrics", []),
            "transaction_metrics": data.get("transaction_metrics", []),
            "index_metrics": data.get("index_metrics", []),
            "slow_queries": data.get("slow_queries", []),
            "optimization_suggestions": data.get("optimization_suggestions", []),
        }

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(self.output_dir, f"db_performance_report_{timestamp_str}.json")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return json_file
