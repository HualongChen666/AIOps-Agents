# -*- coding: utf-8 -*-
"""
Intelligent Task Decomposition Module
=====================================

Based on existing LLM router infrastructure for AI-powered task decomposition.
Extends manual DAG construction in workflow/engine/dag.py with intelligent decomposition.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import LLM router for intelligent task decomposition
LLM_ROUTER_AVAILABLE = False
_get_llm_router = None
try:
    from core.ai.llm_router import get_llm_router as _get_llm_router_impl
    LLM_ROUTER_AVAILABLE = True
    _get_llm_router = _get_llm_router_impl
    logger.info("LLM router available for intelligent task decomposition")
except (ImportError, AttributeError):
    logger.warning("LLM router not available, using rule-based decomposition")


@dataclass
class TaskNode:
    """Task node in decomposition tree"""
    id: str
    name: str
    description: str
    dependencies: List[str]
    estimated_duration: int  # in seconds
    risk_level: str  # low, medium, high
    parameters: Dict[str, Any]


@dataclass
class DecompositionResult:
    """Result of task decomposition"""
    tasks: List[TaskNode]
    execution_order: List[str]
    total_estimated_duration: int
    decomposition_method: str  # llm, rule_based, hybrid


class IntelligentTaskDecomposer:
    """
    Intelligent task decomposer using LLM for complex task analysis.

    Falls back to rule-based decomposition when LLM is unavailable.
    """

    def __init__(self):
        """Initialize intelligent task decomposer"""
        self._llm_router = None
        if LLM_ROUTER_AVAILABLE and _get_llm_router:
            try:
                self._llm_router = _get_llm_router()
                logger.info("Intelligent task decomposer initialized with LLM router")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM router: {e}")
                self._llm_router = None

    async def decompose_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> DecompositionResult:
        """
        Decompose a complex task into executable subtasks.

        Args:
            task_description: Natural language description of the task
            context: Additional context (resources, constraints, etc.)

        Returns:
            DecompositionResult with task nodes and execution order
        """
        context = context or {}

        if self._llm_router:
            try:
                return await self._llm_decompose(task_description, context)
            except Exception as e:
                logger.warning(f"LLM decomposition failed: {e}, falling back to rule-based")
                return self._rule_based_decompose(task_description, context)
        else:
            return self._rule_based_decompose(task_description, context)

    async def _llm_decompose(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> DecompositionResult:
        """
        Use LLM to decompose task intelligently.

        Args:
            task_description: Task description
            context: Task context

        Returns:
            DecompositionResult from LLM analysis
        """
        # Construct prompt for LLM
        prompt = self._build_decomposition_prompt(task_description, context)

        try:
            # Call LLM router for decomposition
            response = await self._llm_router.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3  # Lower temperature for more deterministic output
            )

            # Parse LLM response into task nodes
            tasks = self._parse_llm_response(response, task_description)

            # Calculate execution order (topological sort)
            execution_order = self._calculate_execution_order(tasks)

            total_duration = sum(task.estimated_duration for task in tasks)

            return DecompositionResult(
                tasks=tasks,
                execution_order=execution_order,
                total_estimated_duration=total_duration,
                decomposition_method="llm"
            )

        except Exception as e:
            logger.error(f"LLM decomposition error: {e}")
            raise

    def _build_decomposition_prompt(self, task_description: str, context: Dict[str, Any]) -> str:
        """Build prompt for LLM task decomposition"""
        prompt = f"""
You are an AIOps task decomposition expert. Break down the following task into executable subtasks.

Task: {task_description}

Context:
{self._format_context(context)}

Requirements:
1. Break down into 3-7 executable subtasks
2. Each subtask should be atomic and testable
3. Specify dependencies between subtasks
4. Estimate duration for each subtask (in seconds)
5. Assess risk level (low/medium/high)
6. Provide parameters for each subtask

Output format (JSON):
{{
    "tasks": [
        {{
            "id": "task1",
            "name": "Task 1 Name",
            "description": "Detailed description",
            "dependencies": [],
            "estimated_duration": 30,
            "risk_level": "low",
            "parameters": {{}}
        }}
    ]
}}
"""
        return prompt

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for prompt"""
        if not context:
            return "No additional context provided"

        context_str = ""
        for key, value in context.items():
            context_str += f"{key}: {value}\n"
        return context_str

    def _parse_llm_response(self, response: str, original_task: str) -> List[TaskNode]:
        """Parse LLM response into TaskNode objects"""
        import json
        import re

        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                tasks = []
                for i, task_data in enumerate(data.get("tasks", [])):
                    task = TaskNode(
                        id=task_data.get("id", f"task_{i+1}"),
                        name=task_data.get("name", f"Task {i+1}"),
                        description=task_data.get("description", ""),
                        dependencies=task_data.get("dependencies", []),
                        estimated_duration=task_data.get("estimated_duration", 30),
                        risk_level=task_data.get("risk_level", "medium"),
                        parameters=task_data.get("parameters", {})
                    )
                    tasks.append(task)

                return tasks
            else:
                logger.warning("No JSON found in LLM response, using fallback")
                return self._create_fallback_tasks(original_task)

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}, using fallback")
            return self._create_fallback_tasks(original_task)

    def _create_fallback_tasks(self, task_description: str) -> List[TaskNode]:
        """Create fallback task nodes when parsing fails"""
        return [
            TaskNode(
                id="task_1",
                name="Initial Analysis",
                description=f"Analyze requirements for: {task_description}",
                dependencies=[],
                estimated_duration=30,
                risk_level="low",
                parameters={"description": task_description}
            ),
            TaskNode(
                id="task_2",
                name="Execution",
                description="Execute the main task",
                dependencies=["task_1"],
                estimated_duration=60,
                risk_level="medium",
                parameters={}
            ),
            TaskNode(
                id="task_3",
                name="Verification",
                description="Verify task completion",
                dependencies=["task_2"],
                estimated_duration=30,
                risk_level="low",
                parameters={}
            )
        ]

    def _rule_based_decompose(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> DecompositionResult:
        """
        Rule-based task decomposition as fallback.

        Args:
            task_description: Task description
            context: Task context

        Returns:
            DecompositionResult from rule-based analysis
        """
        # Simple rule-based decomposition based on keywords
        task_lower = task_description.lower()

        if "restart" in task_lower or "重启" in task_lower:
            tasks = self._decompose_restart_task(task_description, context)
        elif "deploy" in task_lower or "部署" in task_lower:
            tasks = self._decompose_deploy_task(task_description, context)
        elif "backup" in task_lower or "备份" in task_lower:
            tasks = self._decompose_backup_task(task_description, context)
        else:
            tasks = self._create_fallback_tasks(task_description)

        execution_order = self._calculate_execution_order(tasks)
        total_duration = sum(task.estimated_duration for task in tasks)

        return DecompositionResult(
            tasks=tasks,
            execution_order=execution_order,
            total_estimated_duration=total_duration,
            decomposition_method="rule_based"
        )

    def _decompose_restart_task(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> List[TaskNode]:
        """Decompose restart task"""
        return [
            TaskNode(
                id="pre_check",
                name="Pre-Restart Check",
                description="Check service status and dependencies",
                dependencies=[],
                estimated_duration=15,
                risk_level="low",
                parameters=context
            ),
            TaskNode(
                id="stop_service",
                name="Stop Service",
                description="Gracefully stop the service",
                dependencies=["pre_check"],
                estimated_duration=30,
                risk_level="medium",
                parameters=context
            ),
            TaskNode(
                id="start_service",
                name="Start Service",
                description="Start the service",
                dependencies=["stop_service"],
                estimated_duration=30,
                risk_level="medium",
                parameters=context
            ),
            TaskNode(
                id="post_check",
                name="Post-Restart Verification",
                description="Verify service is running correctly",
                dependencies=["start_service"],
                estimated_duration=20,
                risk_level="low",
                parameters=context
            )
        ]

    def _decompose_deploy_task(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> List[TaskNode]:
        """Decompose deployment task"""
        return [
            TaskNode(
                id="build",
                name="Build Application",
                description="Build the application",
                dependencies=[],
                estimated_duration=120,
                risk_level="low",
                parameters=context
            ),
            TaskNode(
                id="test",
                name="Run Tests",
                description="Run automated tests",
                dependencies=["build"],
                estimated_duration=60,
                risk_level="medium",
                parameters=context
            ),
            TaskNode(
                id="deploy",
                name="Deploy to Production",
                description="Deploy to production environment",
                dependencies=["test"],
                estimated_duration=90,
                risk_level="high",
                parameters=context
            ),
            TaskNode(
                id="verify",
                name="Deployment Verification",
                description="Verify deployment success",
                dependencies=["deploy"],
                estimated_duration=30,
                risk_level="medium",
                parameters=context
            )
        ]

    def _decompose_backup_task(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> List[TaskNode]:
        """Decompose backup task"""
        return [
            TaskNode(
                id="pre_backup",
                name="Pre-Backup Check",
                description="Check backup prerequisites",
                dependencies=[],
                estimated_duration=15,
                risk_level="low",
                parameters=context
            ),
            TaskNode(
                id="create_backup",
                name="Create Backup",
                description="Create backup snapshot",
                dependencies=["pre_backup"],
                estimated_duration=60,
                risk_level="medium",
                parameters=context
            ),
            TaskNode(
                id="verify_backup",
                name="Verify Backup",
                description="Verify backup integrity",
                dependencies=["create_backup"],
                estimated_duration=30,
                risk_level="low",
                parameters=context
            )
        ]

    def _calculate_execution_order(self, tasks: List[TaskNode]) -> List[str]:
        """
        Calculate execution order using topological sort.

        Args:
            tasks: List of task nodes

        Returns:
            List of task IDs in execution order
        """
        # Build dependency graph
        in_degree = {task.id: 0 for task in tasks}
        adjacency = {task.id: [] for task in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep in adjacency:
                    adjacency[dep].append(task.id)
                    in_degree[task.id] += 1

        # Topological sort (Kahn's algorithm)
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        execution_order = []

        while queue:
            current = queue.pop(0)
            execution_order.append(current)

            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return execution_order


# Global instance for reuse
_intelligent_decomposer: Optional[IntelligentTaskDecomposer] = None


def get_intelligent_decomposer() -> IntelligentTaskDecomposer:
    """Get or create global intelligent task decomposer instance"""
    global _intelligent_decomposer
    if _intelligent_decomposer is None:
        _intelligent_decomposer = IntelligentTaskDecomposer()
    return _intelligent_decomposer


# Batch Processor for multiple task decompositions
class TaskDecompositionBatchProcessor:
    """Batch processor for multiple task decompositions to avoid system overload"""

    def __init__(self, batch_size: int = 10, batch_timeout: int = 30):
        """
        Initialize batch processor.

        Args:
            batch_size: Maximum number of tasks per batch
            batch_timeout: Maximum time to wait for batch completion (seconds)
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._decomposer = None

    async def decompose_batch(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[DecompositionResult]:
        """
        Decompose multiple tasks in batches.

        Args:
            tasks: List of task descriptions with context

        Returns:
            List of decomposition results
        """
        if self._decomposer is None:
            self._decomposer = get_intelligent_decomposer()

        results = []

        # Process in batches
        for i in range(0, len(tasks), self.batch_size):
            batch = tasks[i:i + self.batch_size]

            # Process batch with timeout
            try:
                batch_results = await asyncio.wait_for(
                    self._process_batch(batch),
                    timeout=self.batch_timeout
                )
                results.extend(batch_results)
            except asyncio.TimeoutError:
                logger.warning(f"Batch {i//self.batch_size} timed out, using fallback")
                # Use fallback for timed out batch
                for task in batch:
                    fallback_result = self._decomposer._rule_based_decompose(
                        task.get("description", ""),
                        task.get("context", {})
                    )
                    results.append(fallback_result)

        return results

    async def _process_batch(self, batch: List[Dict[str, Any]]) -> List[DecompositionResult]:
        """
        Process a single batch of tasks concurrently.

        Args:
            batch: Batch of tasks

        Returns:
            List of decomposition results
        """
        tasks_coroutines = []
        for task in batch:
            coro = self._decomposer.decompose_task(
                task.get("description", ""),
                task.get("context", {})
            )
            tasks_coroutines.append(coro)

        # Execute concurrently
        results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Task {i} failed: {result}, using fallback")
                fallback_result = self._decomposer._rule_based_decompose(
                    batch[i].get("description", ""),
                    batch[i].get("context", {})
                )
                processed_results.append(fallback_result)
            else:
                processed_results.append(result)

        return processed_results


# Global batch processor instance
_batch_processor: Optional[TaskDecompositionBatchProcessor] = None


def get_batch_processor() -> TaskDecompositionBatchProcessor:
    """Get or create global batch processor instance"""
    global _batch_processor
    if _batch_processor is None:
        from core.model_inference_config import get_inference_config
        config = get_inference_config()
        _batch_processor = TaskDecompositionBatchProcessor(
            batch_size=config.batch_size,
            batch_timeout=config.batch_timeout_seconds
        )
    return _batch_processor
