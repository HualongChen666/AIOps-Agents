# -*- coding: utf-8 -*-
"""Test scheduler for managing scheduled test executions."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


@dataclass
class TestSchedule:
    """Represents a test schedule."""

    id: str = field(default_factory=lambda: str(uuid4()))
    suite_id: str = ""
    schedule_type: str = "once"  # once, interval, cron
    schedule_expression: str = ""
    next_run: int = field(default_factory=lambda: int(time.time() * 1000))
    active: bool = True
    last_run: Optional[int] = None
    run_count: int = 0


class TestScheduler:
    """Scheduler for managing test execution schedules."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize the test scheduler.

        Args:
            config: Configuration object. If None, uses default Config.
        """
        self.config = config or Config()
        self.schedules: Dict[str, TestSchedule] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, Callable[[str], None]] = {}

    def add_schedule(
        self,
        suite_id: str,
        schedule_type: str,
        schedule_expression: str,
        callback: Optional[Callable[[str], None]] = None,
    ) -> TestSchedule:
        """Add a new test schedule.

        Args:
            suite_id: ID of the test suite
            schedule_type: Type of schedule (once, interval, cron)
            schedule_expression: Schedule expression (seconds for interval, cron for cron)
            callback: Optional callback function to execute when schedule triggers

        Returns:
            TestSchedule object

        Raises:
            ValueError: If schedule parameters are invalid
        """
        if schedule_type not in ["once", "interval", "cron"]:
            raise ValueError(f"Invalid schedule type: {schedule_type}")

        schedule = TestSchedule(
            suite_id=suite_id,
            schedule_type=schedule_type,
            schedule_expression=schedule_expression,
            next_run=self._calculate_next_run(schedule_type, schedule_expression),
        )

        self.schedules[schedule.id] = schedule

        if callback:
            self._callbacks[schedule.id] = callback

        logger.info(
            f"Added schedule {schedule.id} for suite {suite_id}: "
            f"{schedule_type}({schedule_expression})"
        )

        return schedule

    def get_schedule(self, schedule_id: str) -> Optional[TestSchedule]:
        """Get a schedule by ID.

        Args:
            schedule_id: ID of the schedule

        Returns:
            TestSchedule object or None if not found
        """
        return self.schedules.get(schedule_id)

    def list_schedules(
        self, suite_id: Optional[str] = None, active_only: bool = False
    ) -> List[TestSchedule]:
        """List schedules.

        Args:
            suite_id: Optional filter by suite ID
            active_only: Only return active schedules

        Returns:
            List of TestSchedule objects
        """
        schedules = list(self.schedules.values())

        if suite_id:
            schedules = [s for s in schedules if s.suite_id == suite_id]

        if active_only:
            schedules = [s for s in schedules if s.active]

        return schedules

    def update_schedule(
        self,
        schedule_id: str,
        active: Optional[bool] = None,
        schedule_expression: Optional[str] = None,
    ) -> Optional[TestSchedule]:
        """Update a schedule.

        Args:
            schedule_id: ID of the schedule
            active: New active status
            schedule_expression: New schedule expression

        Returns:
            Updated TestSchedule or None if not found
        """
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None

        if active is not None:
            schedule.active = active

        if schedule_expression is not None:
            schedule.schedule_expression = schedule_expression
            schedule.next_run = self._calculate_next_run(
                schedule.schedule_type, schedule_expression
            )

        logger.info(f"Updated schedule {schedule_id}")
        return schedule

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule.

        Args:
            schedule_id: ID of the schedule

        Returns:
            True if deleted, False if not found
        """
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            if schedule_id in self._callbacks:
                del self._callbacks[schedule_id]
            logger.info(f"Deleted schedule {schedule_id}")
            return True
        return False

    def _calculate_next_run(self, schedule_type: str, expression: str) -> int:
        """Calculate the next run time for a schedule.

        Args:
            schedule_type: Type of schedule
            expression: Schedule expression

        Returns:
            Next run timestamp in milliseconds
        """
        now = int(time.time() * 1000)

        if schedule_type == "once":
            # Expression is timestamp in milliseconds
            try:
                return int(expression)
            except ValueError:
                logger.warning(f"Invalid once schedule expression: {expression}")
                return now + 60000  # Default to 1 minute from now

        elif schedule_type == "interval":
            # Expression is interval in seconds
            try:
                interval_seconds = int(expression)
                return now + (interval_seconds * 1000)
            except ValueError:
                logger.warning(f"Invalid interval schedule expression: {expression}")
                return now + 60000  # Default to 1 minute from now

        elif schedule_type == "cron":
            # Simple cron parsing (supports: * * * * *)
            # For now, just default to 1 hour
            logger.warning(f"Cron scheduling not fully implemented, using default 1 hour")
            return now + 3600000

        return now + 60000

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Test scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Test scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = int(time.time() * 1000)

                for schedule in list(self.schedules.values()):
                    if not schedule.active:
                        continue

                    if now >= schedule.next_run:
                        await self._execute_schedule(schedule)

                await asyncio.sleep(self.config.SCHEDULER_CHECK_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
                await asyncio.sleep(self.config.SCHEDULER_CHECK_INTERVAL)

    async def _execute_schedule(self, schedule: TestSchedule) -> None:
        """Execute a scheduled test run.

        Args:
            schedule: Schedule to execute
        """
        logger.info(f"Executing schedule {schedule.id} for suite {schedule.suite_id}")

        # Update schedule
        schedule.last_run = int(time.time() * 1000)
        schedule.run_count += 1

        # Calculate next run
        if schedule.schedule_type == "interval":
            try:
                interval_seconds = int(schedule.schedule_expression)
                schedule.next_run = schedule.last_run + (interval_seconds * 1000)
            except ValueError:
                schedule.active = False
                logger.error(f"Invalid interval expression, deactivating schedule {schedule.id}")
                return
        elif schedule.schedule_type == "once":
            schedule.active = False
        elif schedule.schedule_type == "cron":
            # Re-calculate based on cron expression
            schedule.next_run = self._calculate_next_run(
                schedule.schedule_type, schedule.schedule_expression
            )

        # Execute callback if registered
        callback = self._callbacks.get(schedule.id)
        if callback:
            try:
                callback(schedule.suite_id)
            except Exception as e:
                logger.error(f"Schedule callback error: {e}", exc_info=True)

    def register_callback(self, schedule_id: str, callback: Callable[[str], None]) -> None:
        """Register a callback for a schedule.

        Args:
            schedule_id: ID of the schedule
            callback: Callback function
        """
        self._callbacks[schedule_id] = callback

    def unregister_callback(self, schedule_id: str) -> None:
        """Unregister a callback for a schedule.

        Args:
            schedule_id: ID of the schedule
        """
        if schedule_id in self._callbacks:
            del self._callbacks[schedule_id]
