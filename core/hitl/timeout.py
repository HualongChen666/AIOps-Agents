# -*- coding: utf-8 -*-
"""
Approval Timeout Handler
Handles approval timeout scenarios
"""

import asyncio
from typing import Dict

from loguru import logger

from .approval import ApprovalRequest, ApprovalStatus, ApprovalWorkflow


class ApprovalTimeoutHandler:
    """
    Approval timeout handler

    Manages timeout scenarios for approval requests
    """

    def __init__(self, workflow: ApprovalWorkflow):
        """
        Initialize timeout handler

        Args:
            workflow: Approval workflow
        """
        self.workflow = workflow
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
                # Handle timeout
                self._handle_timeout(request, current_step)

        except asyncio.CancelledError:
            logger.info(f"Timeout monitoring cancelled for {request_id}")

    def _handle_timeout(self, request: ApprovalRequest, step) -> None:
        """
        Handle timeout scenario

        Args:
            request: Approval request
            step: Step that timed out
        """
        step.status = ApprovalStatus.TIMEOUT

        # If step is required, reject the request
        if step.required:
            request.status = ApprovalStatus.REJECTED

            # Move to completed
            self.workflow.completed_requests[request.request_id] = request
            if request.request_id in self.workflow.active_requests:
                del self.workflow.active_requests[request.request_id]

            logger.warning(f"Approval request {request.request_id} rejected due to timeout")
        else:
            # Skip this step and move to next
            logger.info(f"Optional step {step.step_id} timed out, skipping")
            self.workflow._advance_workflow(request)

    def start_monitoring(self, request_id: str) -> None:
        """
        Start timeout monitoring for request

        Args:
            request_id: Request identifier
        """
        if request_id in self.timeout_tasks:
            return

        task = asyncio.create_task(self.monitor_timeout(request_id))
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
