# -*- coding: utf-8 -*-
"""
AI Cost Monitor
AI推理成本监控工具
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelPricing:
    """模型定价"""

    model_name: str
    input_price_per_1k: float  # 输入token价格（每1K）
    output_price_per_1k: float  # 输出token价格（每1K）
    currency: str = "USD"


@dataclass
class TokenUsage:
    """Token使用情况"""

    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: datetime


@dataclass
class CostRecord:
    """成本记录"""

    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: datetime


class AICostMonitor:
    """AI成本监控器"""

    def __init__(self):
        """初始化成本监控器"""
        # 模型定价（示例价格，实际需要根据API提供商更新）
        self.pricing = {
            "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", 0.0005, 0.0015),
            "gpt-4": ModelPricing("gpt-4", 0.03, 0.06),
            "gpt-4-turbo": ModelPricing("gpt-4-turbo", 0.01, 0.03),
            "claude-3-sonnet": ModelPricing("claude-3-sonnet", 0.003, 0.015),
            "claude-3-opus": ModelPricing("claude-3-opus", 0.015, 0.075),
            "claude-3-haiku": ModelPricing("claude-3-haiku", 0.00025, 0.00125),
        }

        self.usage_records: List[TokenUsage] = []
        self.cost_records: List[CostRecord] = []

    def add_pricing(self, model_name: str, input_price: float, output_price: float):
        """添加模型定价"""
        self.pricing[model_name] = ModelPricing(model_name, input_price, output_price)

    def record_usage(self, model_name: str, prompt_tokens: int, completion_tokens: int):
        """记录Token使用情况"""
        usage = TokenUsage(
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            timestamp=datetime.now(),
        )
        self.usage_records.append(usage)

        # 计算成本
        self._calculate_cost(usage)

    def _calculate_cost(self, usage: TokenUsage) -> CostRecord:
        """计算成本"""
        pricing = self.pricing.get(usage.model_name)
        if not pricing:
            logger.warning(f"No pricing found for model: {usage.model_name}")
            pricing = ModelPricing(usage.model_name, 0.0, 0.0)

        input_cost = (usage.prompt_tokens / 1000) * pricing.input_price_per_1k
        output_cost = (usage.completion_tokens / 1000) * pricing.output_price_per_1k
        total_cost = input_cost + output_cost

        cost_record = CostRecord(
            model_name=usage.model_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            timestamp=usage.timestamp,
        )

        self.cost_records.append(cost_record)
        return cost_record

    def get_total_cost(self, model_name: Optional[str] = None) -> float:
        """获取总成本"""
        if model_name:
            return sum(r.total_cost for r in self.cost_records if r.model_name == model_name)
        return sum(r.total_cost for r in self.cost_records)

    def get_total_tokens(self, model_name: Optional[str] = None) -> int:
        """获取总Token数"""
        if model_name:
            return sum(r.total_tokens for r in self.cost_records if r.model_name == model_name)
        return sum(r.total_tokens for r in self.cost_records)

    def get_cost_by_model(self) -> Dict[str, float]:
        """按模型获取成本"""
        costs = {}
        for record in self.cost_records:
            if record.model_name not in costs:
                costs[record.model_name] = 0.0
            costs[record.model_name] += record.total_cost
        return costs

    def get_usage_by_model(self) -> Dict[str, Dict[str, int]]:
        """按模型获取使用情况"""
        usage = {}
        for record in self.cost_records:
            if record.model_name not in usage:
                usage[record.model_name] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            usage[record.model_name]["prompt_tokens"] += record.prompt_tokens
            usage[record.model_name]["completion_tokens"] += record.completion_tokens
            usage[record.model_name]["total_tokens"] += record.total_tokens
        return usage

    def get_cost_over_time(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指定时间内的成本趋势"""
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_records = [r for r in self.cost_records if r.timestamp >= cutoff_time]

        # 按小时分组
        hourly_costs = {}
        for record in filtered_records:
            hour_key = record.timestamp.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_costs:
                hourly_costs[hour_key] = 0.0
            hourly_costs[hour_key] += record.total_cost

        return [{"time": time, "cost": cost} for time, cost in sorted(hourly_costs.items())]

    def generate_cost_report(self) -> Dict[str, Any]:
        """生成成本报告"""
        return {
            "summary": {
                "total_cost": self.get_total_cost(),
                "total_tokens": self.get_total_tokens(),
                "total_requests": len(self.cost_records),
                "avg_cost_per_request": (
                    self.get_total_cost() / len(self.cost_records) if self.cost_records else 0
                ),
                "avg_tokens_per_request": (
                    self.get_total_tokens() / len(self.cost_records) if self.cost_records else 0
                ),
            },
            "by_model": {"costs": self.get_cost_by_model(), "usage": self.get_usage_by_model()},
            "cost_trend": self.get_cost_over_time(hours=24),
            "pricing": {name: asdict(pricing) for name, pricing in self.pricing.items()},
        }

    def generate_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """生成成本优化建议"""
        suggestions = []

        cost_by_model = self.get_cost_by_model()
        self.get_usage_by_model()

        # 检查是否有昂贵的模型使用过多
        for model_name, cost in cost_by_model.items():
            if cost > 10.0:  # 成本超过10美元
                # 检查是否可以降级到更便宜的模型
                if "gpt-4" in model_name.lower():
                    suggestions.append(
                        {
                            "type": "model_downgrade",
                            "model": model_name,
                            "suggestion": (
                                f"考虑将部分{model_name}请求降级到gpt-3.5-turbo以降低成本"
                            ),
                            "potential_savings": cost * 0.8,  # 预计节省80%
                            "priority": "high",
                        }
                    )

        # 检查平均Token使用量
        avg_tokens = self.get_total_tokens() / len(self.cost_records) if self.cost_records else 0
        if avg_tokens > 1000:
            suggestions.append(
                {
                    "type": "token_optimization",
                    "suggestion": f"平均每次请求使用{avg_tokens:.0f}个token，考虑优化提示词长度",
                    "potential_savings": (avg_tokens - 500) / 1000 * 0.001 * len(self.cost_records),
                    "priority": "medium",
                }
            )

        # 检查是否有重复请求
        if len(self.cost_records) > 100:
            suggestions.append(
                {
                    "type": "caching",
                    "suggestion": "考虑实现响应缓存以减少重复推理",
                    "potential_savings": self.get_total_cost() * 0.3,  # 预计节省30%
                    "priority": "high",
                }
            )

        # 检查批量处理机会
        suggestions.append(
            {
                "type": "batch_processing",
                "suggestion": "考虑使用批量处理API以降低成本",
                "potential_savings": self.get_total_cost() * 0.1,  # 预计节省10%
                "priority": "low",
            }
        )

        return suggestions

    def reset(self):
        """重置监控数据"""
        self.usage_records.clear()
        self.cost_records.clear()


async def monitor_ai_costs(
    model_name: str, prompt_tokens: int, completion_tokens: int
) -> Dict[str, Any]:
    """
    监控AI成本的便捷函数

    Args:
        model_name: 模型名称
        prompt_tokens: 输入token数
        completion_tokens: 输出token数

    Returns:
        成本信息
    """
    monitor = AICostMonitor()
    monitor.record_usage(model_name, prompt_tokens, completion_tokens)

    return {
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost": monitor.get_total_cost(),
        "report": monitor.generate_cost_report(),
    }
