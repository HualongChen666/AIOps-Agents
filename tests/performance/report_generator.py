# -*- coding: utf-8 -*-
"""
性能测试报告生成器
生成HTML和JSON格式的性能测试报告
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class PerformanceMetric:
    """性能指标数据类"""

    name: str
    total_requests: int
    success_count: int
    failure_count: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    requests_per_second: float = 0.0


class HTMLReportGenerator:
    """HTML报告生成器"""

    def __init__(self, output_dir: str = "tests/performance/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """生成HTML报告"""
        metrics = self._parse_metrics(data)
        html_content = self._generate_html(metrics, metadata)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = os.path.join(self.output_dir, f"performance_report_{timestamp}.html")

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_file

    def _parse_metrics(self, data: Dict[str, Any]) -> List[PerformanceMetric]:
        """解析性能指标"""
        metrics = []
        for name, result in data.items():
            metric = PerformanceMetric(
                name=name,
                total_requests=result.get("total_requests", 0),
                success_count=result.get("success_count", 0),
                failure_count=result.get("failure_count", 0),
                avg_response_time=result.get("avg_response_time", 0),
                min_response_time=result.get("min_response_time", 0),
                max_response_time=result.get("max_response_time", 0),
                p50_response_time=result.get("p50_response_time", 0),
                p95_response_time=result.get("p95_response_time", 0),
                p99_response_time=result.get("p99_response_time", 0),
                error_rate=result.get("error_rate", 0),
            )
            metrics.append(metric)
        return metrics

    def _generate_html(self, metrics: List[PerformanceMetric], metadata: Dict[str, Any]) -> str:
        """生成HTML内容"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        environment = metadata.get("environment", "N/A") if metadata else "N/A"
        scenario = metadata.get("scenario", "N/A") if metadata else "N/A"
        users = metadata.get("users", "N/A") if metadata else "N/A"

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIOps Agent 性能测试报告</title>
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
        .failure {{
            color: #dc3545;
            font-weight: bold;
        }}
        .warning {{
            color: #ffc107;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>AIOps Agent 性能测试报告</h1>

        <div class="metadata">
            <p><strong>生成时间:</strong> {timestamp}</p>
            <p><strong>测试环境:</strong> {environment}</p>
            <p><strong>测试场景:</strong> {scenario}</p>
            <p><strong>并发用户:</strong> {users}</p>
        </div>

        <h2>测试摘要</h2>
        <div class="summary">
            <div class="summary-card">
                <h3>{len(metrics)}</h3>
                <p>API端点</p>
            </div>
            <div class="summary-card">
                <h3>{sum(m.total_requests for m in metrics):,}</h3>
                <p>总请求数</p>
            </div>
            <div class="summary-card">
                <h3>{sum(m.success_count for m in metrics):,}</h3>
                <p>成功请求</p>
            </div>
            <div class="summary-card">
                <h3>{sum(m.failure_count for m in metrics):,}</h3>
                <p>失败请求</p>
            </div>
        </div>

        <h2>性能指标详情</h2>
        <table>
            <thead>
                <tr>
                    <th>API端点</th>
                    <th>总请求数</th>
                    <th>成功数</th>
                    <th>失败数</th>
                    <th>错误率</th>
                    <th>平均响应时间(ms)</th>
                    <th>P50(ms)</th>
                    <th>P95(ms)</th>
                    <th>P99(ms)</th>
                    <th>最小响应时间(ms)</th>
                    <th>最大响应时间(ms)</th>
                </tr>
            </thead>
            <tbody>
"""

        for metric in metrics:
            error_rate_class = (
                "success"
                if metric.error_rate < 0.01
                else "warning" if metric.error_rate < 0.05 else "failure"
            )
            html += f"""
                <tr>
                    <td>{metric.name}</td>
                    <td>{metric.total_requests:,}</td>
                    <td class="success">{metric.success_count:,}</td>
                    <td class="failure">{metric.failure_count:,}</td>
                    <td class="{error_rate_class}">{metric.error_rate:.2%}</td>
                    <td>{metric.avg_response_time:.2f}</td>
                    <td>{metric.p50_response_time:.2f}</td>
                    <td>{metric.p95_response_time:.2f}</td>
                    <td>{metric.p99_response_time:.2f}</td>
                    <td>{metric.min_response_time:.2f}</td>
                    <td>{metric.max_response_time:.2f}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>

        <h2>性能基准对比</h2>
        <table>
            <thead>
                <tr>
                    <th>API端点</th>
                    <th>当前P95(ms)</th>
                    <th>基准P95(ms)</th>
                    <th>偏差</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
"""

        # 性能基准数据（从performance_baseline.md获取）
        baselines = {
            "/health": 15,
            "/api/v1/alerts": 90,
            "/api/v1/ai/inference": 1800,
            "/api/v1/topology": 150,
            "/api/v1/metrics/summary": 140,
        }

        for metric in metrics:
            baseline = baselines.get(metric.name)
            if baseline:
                deviation = ((metric.p95_response_time - baseline) / baseline) * 100
                status_class = (
                    "success" if deviation < 10 else "warning" if deviation < 20 else "failure"
                )
                status = "正常" if deviation < 10 else "警告" if deviation < 20 else "异常"
                html += f"""
                <tr>
                    <td>{metric.name}</td>
                    <td>{metric.p95_response_time:.2f}</td>
                    <td>{baseline}</td>
                    <td class="{status_class}">{deviation:+.2f}%</td>
                    <td class="{status_class}">{status}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>

        <h2>优化建议</h2>
        <ul>
"""

        # 生成优化建议
        for metric in metrics:
            if metric.error_rate > 0.05:
                html += f"            <li><strong>{
                    metric.name}</strong>: 错误率过高({
                    metric.error_rate:.2%})，建议检查API实现和错误处理</li>\n"
            if metric.p95_response_time > 1000 and not metric.name.startswith("/api/v1/ai"):
                html += f"            <li><strong>{
                    metric.name}</strong>: P95响应时间过长({
                    metric.p95_response_time:.2f}ms)，建议优化查询或增加缓存</li>\n"

        html += """
        </ul>

        <p style="margin-top: 30px; color: #666; font-size: 12px;">
            本报告由AIOps Agent性能测试框架自动生成
        </p>
    </div>
</body>
</html>
"""
        return html


class JSONReportGenerator:
    """JSON报告生成器"""

    def __init__(self, output_dir: str = "tests/performance/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """生成JSON报告"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "environment": metadata.get("environment", "N/A") if metadata else "N/A",
                "scenario": metadata.get("scenario", "N/A") if metadata else "N/A",
                "users": metadata.get("users", "N/A") if metadata else "N/A",
            },
            "summary": {
                "total_endpoints": len(data),
                "total_requests": sum(r.get("total_requests", 0) for r in data.values()),
                "total_success": sum(r.get("success_count", 0) for r in data.values()),
                "total_failures": sum(r.get("failure_count", 0) for r in data.values()),
            },
            "metrics": data,
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = os.path.join(self.output_dir, f"performance_report_{timestamp}.json")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return json_file


class PerformanceRegressionDetector:
    """性能回归检测器"""

    def __init__(self, baseline_file: str = "docs/performance_baseline.md"):
        self.baseline_file = baseline_file
        self.baselines = self._load_baselines()

    def _load_baselines(self) -> Dict[str, Dict[str, float]]:
        """加载性能基准"""
        baselines = {}

        # 从performance_baseline.md解析基准数据
        # 这里简化处理，实际应该解析markdown文件
        baselines = {
            "/health": {"p95": 15, "target": 20},
            "/api/v1/alerts": {"p95": 90, "target": 100},
            "/api/v1/alerts/{id}": {"p95": 70, "target": 80},
            "/api/v1/ai/inference": {"p95": 1800, "target": 2000},
            "/api/v1/ai/rag/retrieve": {"p95": 3500, "target": 4000},
            "/api/v1/autoheal/execute": {"p95": 2500, "target": 3000},
            "/api/v1/topology": {"p95": 150, "target": 200},
            "/api/v1/auth/login": {"p95": 120, "target": 150},
            "/api/v1/metrics/summary": {"p95": 140, "target": 200},
            "/api/v1/logs": {"p95": 250, "target": 300},
        }

        return baselines

    def detect_regression(
        self, metrics: Dict[str, Any], threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """检测性能回归"""
        regressions = []

        for name, metric in metrics.items():
            baseline = self.baselines.get(name)
            if not baseline:
                continue

            current_p95 = metric.get("p95_response_time", 0)
            baseline_p95 = baseline["p95"]

            if current_p95 > 0:
                deviation = (current_p95 - baseline_p95) / baseline_p95

                if deviation > threshold:
                    regressions.append(
                        {
                            "endpoint": name,
                            "current_p95": current_p95,
                            "baseline_p95": baseline_p95,
                            "deviation": deviation,
                            "severity": "critical" if deviation > 0.3 else "warning",
                        }
                    )

        return regressions

    def generate_alert(self, regressions: List[Dict[str, Any]]) -> str:
        """生成告警信息"""
        if not regressions:
            return "无性能回归"

        alert_lines = ["性能回归检测告警:"]
        for regression in regressions:
            severity = regression["severity"].upper()
            alert_lines.append(
                f"[{severity}] {regression['endpoint']}: "
                f"当前P95={regression['current_p95']:.2f}ms, "
                f"基准P95={regression['baseline_p95']}ms, "
                f"偏差={regression['deviation']:.2%}"
            )

        return "\n".join(alert_lines)
