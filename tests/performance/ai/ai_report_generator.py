# -*- coding: utf-8 -*-
"""
AI Performance Report Generator
AI性能测试报告生成器
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class AIPerformanceMetric:
    """AI性能指标"""

    operation: str
    model: str
    mean_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    throughput_ops: float
    token_usage: int
    cost_usd: float


class AIReportGenerator:
    """AI性能报告生成器"""

    def __init__(self, output_dir: str = "tests/performance/ai/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_html_report(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """生成HTML报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        environment = metadata.get("environment", "N/A") if metadata else "N/A"

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIOps Agent AI性能测试报告</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>AIOps Agent AI性能测试报告</h1>

        <div class="metadata">
            <p><strong>生成时间:</strong> {timestamp}</p>
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
                <h3>{data.get('total_cost', 0):.4f}</h3>
                <p>总成本(USD)</p>
            </div>
            <div class="summary-card">
                <h3>{data.get('total_tokens', 0):,}</h3>
                <p>总Token数</p>
            </div>
        </div>

        <div class="section">
            <h2>LLM推理性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>操作</th>
                        <th>模型</th>
                        <th>平均时间(ms)</th>
                        <th>P95(ms)</th>
                        <th>P99(ms)</th>
                        <th>Token数</th>
                        <th>成本(USD)</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        llm_metrics = data.get("llm_metrics", [])
        for metric in llm_metrics:
            status_class = (
                "success"
                if metric["mean_time_ms"] < 500
                else "warning" if metric["mean_time_ms"] < 2000 else "danger"
            )
            status = (
                "优秀"
                if metric["mean_time_ms"] < 500
                else "良好" if metric["mean_time_ms"] < 2000 else "需优化"
            )

            html += f"""
                <tr>
                    <td>{metric['operation']}</td>
                    <td>{metric['model']}</td>
                    <td>{metric['mean_time_ms']:.2f}</td>
                    <td>{metric.get('p95_ms', 0):.2f}</td>
                    <td>{metric.get('p99_ms', 0):.2f}</td>
                    <td>{metric['token_usage']:,}</td>
                    <td>{metric['cost_usd']:.6f}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>RAG系统性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>操作</th>
                        <th>检索时间(ms)</th>
                        <th>生成时间(ms)</th>
                        <th>总延迟(ms)</th>
                        <th>检索文档数</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        rag_metrics = data.get("rag_metrics", [])
        for metric in rag_metrics:
            status_class = (
                "success"
                if metric["total_latency_ms"] < 5000
                else "warning" if metric["total_latency_ms"] < 10000 else "danger"
            )
            status = (
                "优秀"
                if metric["total_latency_ms"] < 5000
                else "良好" if metric["total_latency_ms"] < 10000 else "需优化"
            )

            html += f"""
                <tr>
                    <td>{metric['operation']}</td>
                    <td>{metric['retrieval_time_ms']:.2f}</td>
                    <td>{metric['generation_time_ms']:.2f}</td>
                    <td>{metric['total_latency_ms']:.2f}</td>
                    <td>{metric['num_docs']}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>向量检索性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>操作</th>
                        <th>向量维度</th>
                        <th>检索时间(ms)</th>
                        <th>集合大小</th>
                        <th>Top-K</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        vector_metrics = data.get("vector_metrics", [])
        for metric in vector_metrics:
            status_class = (
                "success"
                if metric["search_time_ms"] < 100
                else "warning" if metric["search_time_ms"] < 500 else "danger"
            )
            status = (
                "优秀"
                if metric["search_time_ms"] < 100
                else "良好" if metric["search_time_ms"] < 500 else "需优化"
            )

            html += f"""
                <tr>
                    <td>{metric['operation']}</td>
                    <td>{metric['vector_dim']}</td>
                    <td>{metric['search_time_ms']:.2f}</td>
                    <td>{metric['collection_size']:,}</td>
                    <td>{metric['top_k']}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>代理编排性能</h2>
            <table>
                <thead>
                    <tr>
                        <th>操作</th>
                        <th>代理数量</th>
                        <th>执行模式</th>
                        <th>总时间(ms)</th>
                        <th>通信开销(ms)</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>
"""

        agent_metrics = data.get("agent_metrics", [])
        for metric in agent_metrics:
            status_class = (
                "success"
                if metric["total_time_ms"] < 1000
                else "warning" if metric["total_time_ms"] < 5000 else "danger"
            )
            status = (
                "优秀"
                if metric["total_time_ms"] < 1000
                else "良好" if metric["total_time_ms"] < 5000 else "需优化"
            )

            html += f"""
                <tr>
                    <td>{metric['operation']}</td>
                    <td>{metric['num_agents']}</td>
                    <td>{metric['execution_mode']}</td>
                    <td>{metric['total_time_ms']:.2f}</td>
                    <td>{metric['communication_overhead_ms']:.2f}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>成本分析</h2>
            <table>
                <thead>
                    <tr>
                        <th>模型</th>
                        <th>总Token数</th>
                        <th>输入Token数</th>
                        <th>输出Token数</th>
                        <th>总成本(USD)</th>
                        <th>占比</th>
                    </tr>
                </thead>
                <tbody>
"""

        cost_by_model = data.get("cost_by_model", [])
        total_cost = sum(m["total_cost"] for m in cost_by_model)

        for cost in cost_by_model:
            percentage = (cost["total_cost"] / total_cost * 100) if total_cost > 0 else 0

            html += f"""
                <tr>
                    <td>{cost['model']}</td>
                    <td>{cost['total_tokens']:,}</td>
                    <td>{cost['input_tokens']:,}</td>
                    <td>{cost['output_tokens']:,}</td>
                    <td>{cost['total_cost']:.4f}</td>
                    <td>{percentage:.1f}%</td>
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
            potential_savings = suggestion.get("potential_savings", 0)
            priority_str = priority.upper()
            savings_str = f"{potential_savings:.2f}"
            suggestion_html = (
                f'<li class="{priority_class}">'
                f"<strong>[{priority_str}]</strong> {suggestion_text} "
                f"(预计节省: {savings_str} USD)</li>"
            )
            html += f"""
                {suggestion_html}
"""

        html += """
            </ul>
        </div>

        <p style="margin-top: 30px; color: #666; font-size: 12px;">
            本报告由AIOps Agent AI性能测试框架自动生成
        </p>
    </div>
</body>
</html>
"""

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = os.path.join(self.output_dir, f"ai_performance_report_{timestamp_str}.html")

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)

        return html_file

    def generate_json_report(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """生成JSON报告"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "environment": metadata.get("environment", "N/A") if metadata else "N/A",
            },
            "summary": {
                "total_tests": data.get("total_tests", 0),
                "passed_tests": data.get("passed_tests", 0),
                "total_cost": data.get("total_cost", 0),
                "total_tokens": data.get("total_tokens", 0),
            },
            "llm_metrics": data.get("llm_metrics", []),
            "rag_metrics": data.get("rag_metrics", []),
            "vector_metrics": data.get("vector_metrics", []),
            "agent_metrics": data.get("agent_metrics", []),
            "cost_by_model": data.get("cost_by_model", []),
            "optimization_suggestions": data.get("optimization_suggestions", []),
        }

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(self.output_dir, f"ai_performance_report_{timestamp_str}.json")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return json_file
