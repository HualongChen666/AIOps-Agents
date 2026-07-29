# -*- coding: utf-8 -*-
"""Structured diagnostic state for the AIOps agent.

This module provides a ``DiagnosticState`` model that tracks what the agent has
learned during a troubleshooting session: confirmed findings, ruled-out
hypotheses, the current hypothesis, pending verification items, collected data,
and confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DiagnosticState:
    """Structured state for a single diagnostic session.

    Unlike raw conversation history, this object is updated by code after each
    tool execution and can be passed to the LLM so it does not have to infer the
    current situation from a long transcript.
    """

    confirmed_findings: List[Dict[str, Any]] = field(default_factory=list)
    ruled_out: List[Dict[str, Any]] = field(default_factory=list)
    current_hypothesis: Optional[str] = None
    pending_verification: List[str] = field(default_factory=list)
    data_collected: List[Dict[str, Any]] = field(default_factory=list)
    steps_taken: List[str] = field(default_factory=list)
    confidence: float = 0.0
    recommended_action: Optional[str] = None

    def update_from_task(
        self, task_description: str, result: Any, error: Optional[str] = None
    ) -> "DiagnosticState":
        """Update state based on a completed/failed task.

        The task description is matched against Chinese/English keywords to
        decide whether this step collected data, verified a hypothesis, executed
        a repair, etc.
        """
        desc = (task_description or "").lower()

        self.steps_taken.append(task_description)

        if error:
            self.ruled_out.append({"description": task_description, "reason": f"failed: {error}"})
            return self

        result_summary = self._summarize_result(result)

        # Collection / data gathering
        if any(k in desc for k in ("收集", "采集", "获取", "collect", "gather", "fetch")):
            self.data_collected.append({"step": task_description, "summary": result_summary})

        # Analysis / identification -> current hypothesis / candidates
        elif any(
            k in desc for k in ("分析", "识别", "定位", "analyze", "identify", "locate", "diagnose")
        ):
            self.current_hypothesis = result_summary
            self.pending_verification.append(result_summary)

        # Validation / verification -> confirm or rule out
        elif any(
            k in desc for k in ("验证", "检查", "确认", "validate", "verify", "check", "confirm")
        ):
            if self.pending_verification:
                verified = self.pending_verification.pop(0)
                self.confirmed_findings.append(
                    {
                        "hypothesis": verified,
                        "evidence": result_summary,
                        "confidence": 0.8,
                    }
                )
            else:
                self.confirmed_findings.append(
                    {
                        "hypothesis": task_description,
                        "evidence": result_summary,
                        "confidence": 0.6,
                    }
                )

        # Execution / repair -> action taken
        elif any(
            k in desc
            for k in ("执行", "修复", "重启", "execute", "repair", "fix", "restart", "remediate")
        ):
            self.recommended_action = result_summary
            self.confidence = max(self.confidence, 0.75)

        # Reporting / summary
        elif any(k in desc for k in ("生成", "报告", "总结", "generate", "report", "summarize")):
            self.recommended_action = result_summary

        else:
            # Generic information update
            self.data_collected.append({"step": task_description, "summary": result_summary})

        return self

    def rule_out(self, hypothesis: str, reason: str) -> "DiagnosticState":
        """Explicitly rule out a hypothesis."""
        self.ruled_out.append({"hypothesis": hypothesis, "reason": reason})
        if self.current_hypothesis == hypothesis:
            self.current_hypothesis = None
        return self

    def confirm(self, finding: str, evidence: str, confidence: float = 0.9) -> "DiagnosticState":
        """Confirm a finding with evidence and confidence."""
        self.confirmed_findings.append(
            {"finding": finding, "evidence": evidence, "confidence": confidence}
        )
        if self.current_hypothesis == finding:
            self.pending_verification = [h for h in self.pending_verification if h != finding]
        self.confidence = max(self.confidence, confidence)
        return self

    def set_hypothesis(self, hypothesis: str) -> "DiagnosticState":
        """Set the current working hypothesis."""
        self.current_hypothesis = hypothesis
        if hypothesis not in self.pending_verification:
            self.pending_verification.append(hypothesis)
        return self

    def add_data(self, key: str, value: Any) -> "DiagnosticState":
        """Add a piece of collected data."""
        self.data_collected.append({"key": key, "value": value})
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary for inclusion in ``context``."""
        return {
            "confirmed_findings": self.confirmed_findings,
            "ruled_out": self.ruled_out,
            "current_hypothesis": self.current_hypothesis,
            "pending_verification": self.pending_verification,
            "data_collected": self.data_collected,
            "steps_taken": self.steps_taken,
            "confidence": round(self.confidence, 4),
            "recommended_action": self.recommended_action,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiagnosticState":
        """Restore from a dictionary."""
        return cls(
            confirmed_findings=list(data.get("confirmed_findings", [])),
            ruled_out=list(data.get("ruled_out", [])),
            current_hypothesis=data.get("current_hypothesis"),
            pending_verification=list(data.get("pending_verification", [])),
            data_collected=list(data.get("data_collected", [])),
            steps_taken=list(data.get("steps_taken", [])),
            confidence=float(data.get("confidence", 0.0)),
            recommended_action=data.get("recommended_action"),
        )

    @staticmethod
    def _summarize_result(result: Any, max_len: int = 200) -> str:
        """Extract a short string summary from a tool result."""
        if result is None:
            return "no result"
        if isinstance(result, dict):
            if "summary" in result:
                return str(result["summary"])[:max_len]
            if "status" in result and "result" in result:
                return f"status={result['status']}; result={str(result['result'])[:max_len]}"
            return str(result)[:max_len]
        if isinstance(result, list):
            return f"list[{len(result)}]: {str(result[0])[:100] if result else 'empty'}"
        return str(result)[:max_len]
