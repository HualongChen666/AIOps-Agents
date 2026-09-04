# -*- coding: utf-8 -*-
"""
Workflow DSL (Domain Specific Language)
Parse workflow definitions from YAML and JSON
"""

import json
from typing import Any, Dict, Optional

import yaml
from loguru import logger

from .dag import DAG, DAGNode, Edge

# Try to import intelligent task decomposer
INTELLIGENT_DECOMPOSER_AVAILABLE = False
_get_intelligent_decomposer = None
try:
    from core.intelligent_task_decomposer import get_intelligent_decomposer as _get_decomposer_impl
    INTELLIGENT_DECOMPOSER_AVAILABLE = True
    _get_intelligent_decomposer = _get_decomposer_impl
    logger.info("Intelligent task decomposer available for workflow automation")
except (ImportError, AttributeError):
    logger.warning("Intelligent task decomposer not available, using manual workflow construction")


class WorkflowDSL:
    """
    Workflow DSL parser and validator

    Supports:
    - YAML format
    - JSON format
    - Schema validation
    - Template variables
    """

    def __init__(self):
        """Initialize DSL parser"""
        self._templates: Dict[str, Any] = {}

    def load_template(self, name: str, template: Dict[str, Any]) -> None:
        """
        Load workflow template

        Args:
            name: Template name
            template: Template definition
        """
        self._templates[name] = template
        logger.info(f"Loaded workflow template: {name}")

    def parse_yaml(self, yaml_content: str) -> DAG:
        """
        Parse workflow from YAML

        Args:
            yaml_content: YAML string

        Returns:
            DAG object

        Raises:
            ValueError: If parsing fails
        """
        try:
            data = yaml.safe_load(yaml_content)
            return self._parse_workflow_data(data)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing failed: {e}")

    def parse_json(self, json_content: str) -> DAG:
        """
        Parse workflow from JSON

        Args:
            json_content: JSON string

        Returns:
            DAG object

        Raises:
            ValueError: If parsing fails
        """
        try:
            data = json.loads(json_content)
            return self._parse_workflow_data(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parsing failed: {e}")

    def _parse_workflow_data(self, data: Dict[str, Any]) -> DAG:
        """
        Parse workflow data dictionary

        Args:
            data: Workflow data dictionary

        Returns:
            DAG object
        """
        # Validate required fields
        if "name" not in data:
            raise ValueError("Workflow must have 'name' field")

        if "nodes" not in data:
            raise ValueError("Workflow must have 'nodes' field")

        dag = DAG(data["name"])

        # Parse nodes
        for node_data in data["nodes"]:
            node = self._parse_node(node_data)
            dag.add_node(node)

        # Parse edges
        if "edges" in data:
            for edge_data in data["edges"]:
                edge = self._parse_edge(edge_data)
                dag.add_edge(edge)

        # Validate DAG
        cycles = dag.detect_cycles()
        if cycles:
            raise ValueError(f"Workflow contains cycles: {cycles}")

        logger.info(f"Parsed workflow '{data['name']}' with {len(dag.nodes)} nodes")

        return dag

    def _parse_node(self, node_data: Dict[str, Any]) -> DAGNode:
        """
        Parse node data

        Args:
            node_data: Node data dictionary

        Returns:
            DAGNode object
        """
        if "id" not in node_data:
            raise ValueError("Node must have 'id' field")

        return DAGNode(
            id=node_data["id"],
            name=node_data.get("name", node_data["id"]),
            type=node_data.get("type", "task"),
            config=node_data.get("config", {}),
            dependencies=node_data.get("dependencies", []),
        )

    def _parse_edge(self, edge_data: Dict[str, Any]) -> Edge:
        """
        Parse edge data

        Args:
            edge_data: Edge data dictionary

        Returns:
            Edge object
        """
        if "from" not in edge_data or "to" not in edge_data:
            raise ValueError("Edge must have 'from' and 'to' fields")

        return Edge(
            from_node=edge_data["from"],
            to_node=edge_data["to"],
            condition=edge_data.get("condition"),
        )

    def validate(self, dag: DAG) -> bool:
        """
        Validate DAG structure

        Args:
            dag: DAG to validate

        Returns:
            True if valid
        """
        # Check for cycles
        cycles = dag.detect_cycles()
        if cycles:
            logger.error(f"Validation failed: cycles detected {cycles}")
            return False

        # Check for orphan nodes
        all_referenced = set()
        for edge in dag.edges:
            all_referenced.add(edge.from_node)
            all_referenced.add(edge.to_node)

        orphans = set(dag.nodes.keys()) - all_referenced
        if orphans:
            logger.warning(f"Orphan nodes detected: {orphans}")

        # Check for missing dependencies
        for node in dag.nodes.values():
            for dep in node.dependencies:
                if dep not in dag.nodes:
                    logger.error(f"Node {node.id} depends on missing node {dep}")
                    return False

        return True


# Convenience functions
def parse_yaml_workflow(yaml_content: str) -> DAG:
    """Parse workflow from YAML"""
    dsl = WorkflowDSL()
    return dsl.parse_yaml(yaml_content)


def parse_json_workflow(json_content: str) -> DAG:
    """Parse workflow from JSON"""
    dsl = WorkflowDSL()
    return dsl.parse_json(json_content)


async def decompose_workflow_from_description(
    task_description: str,
    context: Optional[Dict[str, Any]] = None
) -> DAG:
    """
    Decompose a task description into a workflow DAG using intelligent decomposition.
    
    Args:
        task_description: Natural language description of the task
        context: Additional context for decomposition
        
    Returns:
        DAG object with decomposed tasks
    """
    if not INTELLIGENT_DECOMPOSER_AVAILABLE or not _get_intelligent_decomposer:
        logger.warning("Intelligent decomposer not available, creating fallback workflow")
        return _create_fallback_workflow(task_description)
    
    try:
        decomposer = _get_intelligent_decomposer()
        decomposition_result = await decomposer.decompose_task(task_description, context)
        
        # Convert decomposition result to DAG
        dag = DAG(f"auto_decomposed_{task_description[:20]}")
        
        # Add nodes from decomposition result
        for task in decomposition_result.tasks:
            node = DAGNode(
                id=task.id,
                name=task.name,
                type="task",
                config={
                    "description": task.description,
                    "estimated_duration": task.estimated_duration,
                    "risk_level": task.risk_level,
                    **task.parameters
                },
                dependencies=task.dependencies
            )
            dag.add_node(node)
        
        # Add edges based on dependencies
        for task in decomposition_result.tasks:
            for dep in task.dependencies:
                if dep in dag.nodes:
                    edge = Edge(from_node=dep, to_node=task.id)
                    dag.add_edge(edge)
        
        logger.info(f"Created workflow from decomposition with {len(dag.nodes)} nodes")
        return dag
        
    except Exception as e:
        logger.warning(f"Intelligent decomposition failed: {e}, creating fallback workflow")
        return _create_fallback_workflow(task_description)


def _create_fallback_workflow(task_description: str) -> DAG:
    """Create a simple fallback workflow when intelligent decomposition is unavailable"""
    dag = DAG(f"fallback_{task_description[:20]}")
    
    # Create simple three-step workflow
    task1 = DAGNode(
        id="analyze",
        name="Task Analysis",
        type="task",
        config={"description": f"Analyze: {task_description}"},
        dependencies=[]
    )
    dag.add_node(task1)
    
    task2 = DAGNode(
        id="execute",
        name="Task Execution",
        type="task",
        config={"description": f"Execute: {task_description}"},
        dependencies=["analyze"]
    )
    dag.add_node(task2)
    
    task3 = DAGNode(
        id="verify",
        name="Task Verification",
        type="task",
        config={"description": f"Verify: {task_description}"},
        dependencies=["execute"]
    )
    dag.add_node(task3)
    
    # Add edges
    dag.add_edge(Edge(from_node="analyze", to_node="execute"))
    dag.add_edge(Edge(from_node="execute", to_node="verify"))
    
    logger.info("Created fallback workflow with 3 nodes")
    return dag


# Export availability flag
__all__ = [
    "WorkflowDSL",
    "parse_yaml_workflow",
    "parse_json_workflow",
    "decompose_workflow_from_description",
    "INTELLIGENT_DECOMPOSER_AVAILABLE",
]
