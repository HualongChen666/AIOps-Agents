# -*- coding: utf-8 -*-
"""
LLM-RAG Automated Runbook Generator
基于LLM和RAG的自动化Runbook生成器

功能:
- RAG检索相关历史案例
- LLM生成修复方案
- Runbook结构化输出
- 多LLM支持（OpenAI、Claude等）
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class RunbookGenerator:
    """
    Runbook生成器

    结合RAG检索和LLM生成，自动创建修复Runbook。

    参数:
        vector_store: 向量存储实例
        llm_provider: LLM提供商（openai, claude, local）
        llm_api_key: LLM API密钥
        llm_model: LLM模型名称
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm_provider: str = "openai",
        llm_api_key: Optional[str] = None,
        llm_model: str = "gpt-4",
    ):
        self.vector_store = vector_store or VectorStore()
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model

        self.is_initialized = False
        self.openai_client: Optional[Any] = None
        self.claude_client: Optional[Any] = None

    def initialize(self) -> None:
        """初始化生成器"""
        logger.info("Initializing runbook generator")

        # 初始化向量存储
        if not self.vector_store.is_initialized:
            self.vector_store.initialize()

        # 初始化LLM客户端
        self._init_llm_client()

        self.is_initialized = True
        logger.info("Runbook generator initialized")

    def _init_llm_client(self) -> None:
        """初始化LLM客户端"""
        if self.llm_provider == "openai":
            try:
                import openai

                self.openai_client = openai.OpenAI(api_key=self.llm_api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("openai not installed")
                self.openai_client = None
        elif self.llm_provider == "claude":
            try:
                import anthropic

                self.claude_client = anthropic.Anthropic(api_key=self.llm_api_key)
                logger.info("Claude client initialized")
            except ImportError:
                logger.warning("anthropic not installed")
                self.claude_client = None
        else:
            logger.warning("Unknown LLM provider: %s", self.llm_provider)

    def retrieve_relevant_cases(
        self, alert: Dict[str, Any], top_k: int = 5, score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        检索相关历史案例

        参数:
            alert: 告警信息
            top_k: 返回top-k结果
            score_threshold: 分数阈值

        返回:
            相关案例列表
        """
        # 构建查询文本
        query_parts = [
            alert.get("title", ""),
            alert.get("description", ""),
            alert.get("service", ""),
            alert.get("metric", ""),
        ]
        query = " ".join([p for p in query_parts if p])

        # 搜索
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        logger.info("Retrieved %d relevant cases for alert: %s", len(results), alert.get("title"))

        return results  # type: ignore

    def generate_runbook(
        self, alert: Dict[str, Any], context: Optional[Dict[str, Any]] = None, use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        生成Runbook

        参数:
            alert: 告警信息
            context: 额外上下文
            use_rag: 是否使用RAG检索

        返回:
            Runbook生成结果
        """
        if not self.is_initialized:
            self.initialize()

        logger.info("Generating runbook for alert: %s", alert.get("title"))

        # RAG检索
        rag_context = []
        if use_rag:
            relevant_cases = self.retrieve_relevant_cases(alert)
            for case in relevant_cases:
                rag_context.append(
                    {
                        "content": case["payload"].get("content", ""),
                        "score": case["score"],
                    }
                )

        # 构建提示词
        prompt = self._build_prompt(alert, context, rag_context)

        # 调用LLM生成
        try:
            llm_response = self._call_llm(prompt)
            runbook = self._parse_runbook(llm_response)

            logger.info("Runbook generated successfully")

            return {
                "success": True,
                "runbook": runbook,
                "rag_context": rag_context,
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model,
            }

        except Exception as e:
            logger.error("Failed to generate runbook: %s", e)

            # 降级：返回模板Runbook
            return {
                "success": False,
                "error": str(e),
                "runbook": self._generate_template_runbook(alert),
                "fallback": True,
            }

    def _build_prompt(
        self,
        alert: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        rag_context: List[Dict[str, Any]],
    ) -> str:
        """
        构建LLM提示词

        参数:
            alert: 告警信息
            context: 额外上下文
            rag_context: RAG检索的上下文

        返回:
            提示词字符串
        """
        prompt_parts = [
            (  # noqa: E501
                "You are an expert AIOps engineer. Generate a comprehensive runbook to address the"
                " following alert."
            ),
            "",
            "## Alert Information",
            f"- Title: {alert.get('title', 'Unknown')}",
            f"- Description: {alert.get('description', 'No description')}",
            f"- Severity: {alert.get('severity', 'Unknown')}",
            f"- Service: {alert.get('service', 'Unknown')}",
            f"- Metric: {alert.get('metric', 'Unknown')}",
            f"- Current Value: {alert.get('current_value', 'N/A')}",
            f"- Threshold: {alert.get('threshold', 'N/A')}",
        ]

        # 添加上下文
        if context:
            prompt_parts.extend(
                [
                    "",
                    "## Additional Context",
                    json.dumps(context, indent=2),
                ]
            )

        # 添加RAG检索的历史案例
        if rag_context:
            prompt_parts.extend(
                [
                    "",
                    "## Relevant Historical Cases",
                ]
            )
            for idx, case in enumerate(rag_context, 1):
                prompt_parts.extend(
                    [
                        f"### Case {idx} (Similarity: {case['score']:.2f})",
                        case["content"],
                    ]
                )

        prompt_parts.extend(
            [
                "",
                "## Runbook Requirements",
                "Generate a structured runbook with the following sections:",
                "1. **Problem Summary**: Brief description of the issue",
                "2. **Root Cause Analysis**: Potential causes based on the alert and context",
                "3. **Immediate Actions**: Steps to mitigate the issue immediately",
                "4. **Long-term Solutions**: Permanent fixes to prevent recurrence",
                "5. **Verification Steps**: How to verify the fix is successful",
                "6. **Rollback Plan**: Steps to rollback if the fix causes issues",
                "7. **Risk Assessment**: Potential risks and mitigation strategies",
                "",
                "Format the response as JSON with the following structure:",
                "{",
                '  "problem_summary": "...",',
                '  "root_cause_analysis": "...",',
                '  "immediate_actions": ["step1", "step2", ...],',
                '  "long_term_solutions": ["solution1", "solution2", ...],',
                '  "verification_steps": ["step1", "step2", ...],',
                '  "rollback_plan": ["step1", "step2", ...],',
                '  "risk_assessment": "..."',
                "}",
                "",
                "Ensure the runbook is actionable, specific, and follows best practices.",
            ]
        )

        return "\n".join(prompt_parts)

    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM生成响应

        参数:
            prompt: 提示词

        返回:
            LLM响应
        """
        if self.llm_provider == "openai" and hasattr(self, "openai_client") and self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are an expert AIOps engineer."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                )
                return response.choices[0].message.content  # type: ignore
            except Exception as e:
                logger.error("OpenAI API call failed: %s", e)
                raise

        elif (
            self.llm_provider == "claude" and hasattr(self, "claude_client") and self.claude_client
        ):
            try:
                claude_response: Any = self.claude_client.messages.create(  # type: ignore[assignment]  # noqa: E501
                    model=self.llm_model,
                    max_tokens=2000,
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                )
                return claude_response.content[0].text  # type: ignore
            except Exception as e:
                logger.error("Claude API call failed: %s", e)
                raise

        else:
            # 降级：返回占位响应
            logger.warning("LLM client not available, using fallback response")
            return json.dumps(
                {
                    "problem_summary": "Fallback - LLM not available",
                    "root_cause_analysis": "Unable to analyze without LLM",
                    "immediate_actions": ["Check system logs", "Monitor metrics"],
                    "long_term_solutions": ["Implement monitoring", "Add alerts"],
                    "verification_steps": ["Verify metrics return to normal"],
                    "rollback_plan": ["Revert changes if issues occur"],
                    "risk_assessment": "Low risk - fallback runbook",
                }
            )

    def _parse_runbook(self, llm_response: str) -> Dict[str, Any]:
        """
        解析LLM响应为Runbook结构

        参数:
            llm_response: LLM响应

        返回:
            Runbook字典
        """
        try:
            # 尝试解析JSON
            runbook = json.loads(llm_response)

            # 验证必需字段
            required_fields = [
                "problem_summary",
                "root_cause_analysis",
                "immediate_actions",
                "long_term_solutions",
                "verification_steps",
                "rollback_plan",
                "risk_assessment",
            ]

            for field in required_fields:
                if field not in runbook:
                    runbook[field] = f"Missing field: {field}"

            return runbook  # type: ignore

        except json.JSONDecodeError:
            # 如果解析失败，尝试提取JSON部分
            try:
                # 查找JSON块
                start = llm_response.find("{")
                end = llm_response.rfind("}") + 1
                if start != -1 and end != -1:
                    json_str = llm_response[start:end]
                    runbook = json.loads(json_str)
                    return runbook  # type: ignore
            except BaseException:
                pass

            # 完全失败，返回原始响应
            logger.warning("Failed to parse LLM response as JSON")
            return {
                "problem_summary": llm_response[:500],
                "root_cause_analysis": "Unable to parse",
                "immediate_actions": [],
                "long_term_solutions": [],
                "verification_steps": [],
                "rollback_plan": [],
                "risk_assessment": "Unknown",
                "raw_response": llm_response,
            }

    def _generate_template_runbook(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成模板Runbook（降级方法）

        参数:
            alert: 告警信息

        返回:
            模板Runbook
        """
        return {
            "problem_summary": (  # noqa: E501
                f"Alert: {alert.get('title', 'Unknown')} -"
                f" {alert.get('description', 'No description')}"
            ),
            "root_cause_analysis": "Root cause analysis requires LLM - using template",
            "immediate_actions": [
                "Check service status",
                "Review recent logs",
                "Monitor key metrics",
                "Verify system resources",
            ],
            "long_term_solutions": [
                "Implement automated monitoring",
                "Add alerting thresholds",
                "Document common issues",
                "Create standard procedures",
            ],
            "verification_steps": [
                "Verify service is running",
                "Check metrics return to normal",
                "Confirm no errors in logs",
            ],
            "rollback_plan": [
                "Restart service if needed",
                "Revert recent changes",
                "Escalate to team if unresolved",
            ],
            "risk_assessment": "Template runbook - actual risk assessment requires LLM analysis",
        }

    def index_historical_cases(self, cases: List[Dict[str, Any]]) -> int:
        """
        索引历史案例到向量存储

        参数:
            cases: 历史案例列表，每个案例包含id、content、metadata

        返回:
            成功索引的数量
        """
        logger.info("Indexing %d historical cases", len(cases))

        documents: List[Dict[str, Any]] = []
        for case in cases:
            doc = {
                "id": case.get("id", f"case_{len(documents)}"),
                "content": case.get("content", ""),
                "metadata": case.get("metadata", {}),
            }
            documents.append(doc)

        count = self.vector_store.add_documents_batch(documents)
        logger.info("Indexed %d historical cases", count)

        return count  # type: ignore

    def evaluate_runbook_quality(
        self, runbook: Dict[str, Any], alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估Runbook质量

        参数:
            runbook: Runbook
            alert: 告警信息

        返回:
            质量评估结果
        """
        quality_score = 0.0
        issues = []

        # 检查必需字段
        required_fields = [
            "problem_summary",
            "root_cause_analysis",
            "immediate_actions",
            "long_term_solutions",
            "verification_steps",
            "rollback_plan",
            "risk_assessment",
        ]

        for field in required_fields:
            if field in runbook and runbook[field]:
                quality_score += 1.0 / len(required_fields)
            else:
                issues.append(f"Missing or empty field: {field}")

        # 检查动作列表
        action_fields = [
            "immediate_actions",
            "long_term_solutions",
            "verification_steps",
            "rollback_plan",
        ]
        for field in action_fields:
            if field in runbook:
                if isinstance(runbook[field], list) and len(runbook[field]) > 0:
                    quality_score += 0.05
                else:
                    issues.append(f"Field {field} should be a non-empty list")

        # 检查问题摘要相关性
        if "problem_summary" in runbook:
            summary = runbook["problem_summary"].lower()
            alert_title = alert.get("title", "").lower()
            if alert_title in summary or any(word in summary for word in alert_title.split()):
                quality_score += 0.1
            else:
                issues.append("Problem summary does not mention the alert title")

        return {
            "quality_score": min(quality_score, 1.0),
            "issues": issues,
            "passed": len(issues) == 0,
        }
