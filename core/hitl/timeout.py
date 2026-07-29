# -*- coding: utf-8 -*-
import logging

"""
Approval Timeout Handler
Handles approval timeout scenarios
"""

import asyncio
from typing import Dict, Optional

from loguru import logger

from .approval import ApprovalRequest, ApprovalStatus, ApprovalWorkflow

try:
    from .notification import ApprovalNotifier

    NOTIFIER_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    ApprovalNotifier = None  # type: ignore[misc,assignment]
    NOTIFIER_AVAILABLE = False


class ApprovalTimeoutHandler:
    """
    Approval timeout handler

    Manages timeout scenarios for approval requests
    """

    def __init__(
        self,
        workflow: ApprovalWorkflow,
        notifier: Optional["ApprovalNotifier"] = None,
    ):
        """
        Initialize timeout handler

        Args:
            workflow: Approval workflow
            notifier: Optional approval notifier used to notify the next approver.
        """
        self.workflow = workflow
        self.notifier = notifier
        self.timeout_tasks: Dict[str, asyncio.Task] = {}

    async def monitor_timeout(self, request_id: str) -> None:
        """
        Monitor approval request for timeout

        Args:
            request_id: Request identifier
        """
        request = self.workflow.active_requests.get(request_id)
        if not request:
            return

        # Get current step
        if request.current_step >= len(request.steps):
            return

        current_step = request.steps[request.current_step]
        timeout_seconds = current_step.timeout_minutes * 60

        # Wait for timeout
        try:
            await asyncio.sleep(timeout_seconds)

            # Check if still pending
            request = self.workflow.active_requests.get(request_id)
            if request and current_step.status == ApprovalStatus.PENDING:
                # Handle timeout (escalate or reject)
                await self._handle_timeout(request, current_step)

        except asyncio.CancelledError:
            logger.info(f"Timeout monitoring cancelled for {request_id}")

    async def _handle_timeout(self, request: ApprovalRequest, step) -> None:
        """
        Handle timeout scenario.

        Escalates to the next pending approval level if one exists; otherwise
        rejects the request and interrupts any associated agent.

        Args:
            request: Approval request
            step: Step that timed out
        """
        step.status = ApprovalStatus.TIMEOUT

        next_index = self._find_next_pending_step(request, step)
        if next_index is not None:
            request.current_step = next_index
            next_step = request.steps[next_index]
            logger.warning(
                f"Approval request {request.request_id} step {step.step_id} timed out; "
                f"escalating to {next_step.approver} ({next_step.step_id})"
            )
            self.workflow.history.record_action(
                request_id=request.request_id,
                workflow_id=request.workflow_id,
                action="escalated",
                actor="system",
                details={
                    "timed_out_step": step.step_id,
                    "next_step": next_step.step_id,
                    "next_approver": next_step.approver,
                },
            )
            await self._notify_step(request, next_step)
            # Re-arm monitoring for the escalated step.
            self.start_monitoring(request.request_id)
            return

        # No further approver available: reject and stop the agent.
        request.status = ApprovalStatus.REJECTED
        self.workflow.completed_requests[request.request_id] = request
        if request.request_id in self.workflow.active_requests:
            del self.workflow.active_requests[request.request_id]

        self.workflow.history.record_action(
            request_id=request.request_id,
            workflow_id=request.workflow_id,
            action="timeout_rejected",
            actor="system",
            details={"step_id": step.step_id},
        )
        self.workflow._interrupt_associated_agent(request)

        logger.warning(f"Approval request {request.request_id} rejected due to timeout")

    def _find_next_pending_step(self, request: ApprovalRequest, timed_out_step) -> Optional[int]:
        """Return the index of the next pending step after the timed-out step, if any."""
        try:
            start_index = request.steps.index(timed_out_step)
        except ValueError:
            return None

        for i in range(start_index + 1, len(request.steps)):
            if request.steps[i].status == ApprovalStatus.PENDING:
                return i
        return None

    async def _notify_step(self, request: ApprovalRequest, step) -> None:
        """Notify the next approver that an approval is pending."""
        if not self.notifier:
            return
        try:
            await self.notifier.send_approval_request(
                step.approver,
                request.to_dict(),
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Failed to notify next approver {step.approver}: {exc}")

    def start_monitoring(self, request_id: str) -> None:
        """
        Start timeout monitoring for request

        Args:
            request_id: Request identifier
        """
        if request_id in self.timeout_tasks:
            return

        try:
            task = asyncio.create_task(self.monitor_timeout(request_id))
        except RuntimeError:  # pragma: no cover
            logger.warning(
                f"No running event loop; cannot start timeout monitoring for {request_id}"
            )
            return
        self.timeout_tasks[request_id] = task

        logger.info(f"Started timeout monitoring for {request_id}")

    def stop_monitoring(self, request_id: str) -> None:
        """
        Stop timeout monitoring for request

        Args:
            request_id: Request identifier
        """
        if request_id in self.timeout_tasks:
            self.timeout_tasks[request_id].cancel()
            del self.timeout_tasks[request_id]

            logger.info(f"Stopped timeout monitoring for {request_id}")
