# Workflow Engine

## Overview

The Workflow Engine provides a DAG-based workflow execution system for complex business process orchestration in AIOps Agent.

## Features

- **DAG-based Workflows**: Directed Acyclic Graph for representing complex workflows
- **State Machine**: Workflow state management with valid transitions
- **Parallel Execution**: Execute nodes in parallel with configurable concurrency limits
- **Retry Mechanism**: Automatic retry with exponential backoff
- **Timeout Handling**: Per-node timeout configuration
- **DSL Support**: Define workflows in YAML or JSON
- **Template Library**: Pre-built templates for common AIOps scenarios

## Components

### DAG (Directed Acyclic Graph)
- Core data structure for workflow representation
- Topological sorting for execution order
- Cycle detection
- Dependency tracking

### State Machine
- Workflow execution state management
- Valid state transitions
- Transition history tracking
- State-based event handling

### Workflow Executor
- Parallel node execution
- Retry with exponential backoff
- Timeout handling
- Context management
- Progress tracking

### DSL (Domain Specific Language)
- YAML/JSON workflow definitions
- Schema validation
- Template variable support
- Template library

## Usage Example

```python
from aiops_core.workflow.engine import DAG, DAGNode, WorkflowExecutor

# Create DAG
dag = DAG("my_workflow")
dag.add_node(DAGNode(id="collect", name="Collect Data"))
dag.add_node(DAGNode(id="analyze", name="Analyze", dependencies=["collect"]))
dag.add_edge(Edge(from_node="collect", to_node="analyze"))

# Create executor
executor = WorkflowExecutor(max_parallel_nodes=5)

# Register handler
async def my_handler(node, context):
    # Your node execution logic
    return {"result": "success"}

executor.register_handler("task", my_handler)

# Execute workflow
context = await executor.execute(dag)
print(context.results)
```

## DSL Example

```yaml
name: alert_response
description: Automated alert response workflow

nodes:
  - id: collect_context
    name: Collect Alert Context
    type: task
    config:
      timeout: 30
    dependencies: []
  
  - id: analyze_severity
    name: Analyze Severity
    type: task
    config:
      timeout: 60
    dependencies: [collect_context]

edges:
  - from: collect_context
    to: analyze_severity
```

## Templates

Pre-built templates are available in `core/workflow/templates/`:

- `alert_response.yaml` - Alert response workflow
- `metric_analysis.yaml` - Metric analysis workflow
- `log_analysis.yaml` - Log analysis workflow
- `auto_remediation.yaml` - Auto-remediation workflow

## API Reference

### DAG
- `add_node(node)`: Add node to DAG
- `add_edge(edge)`: Add edge to DAG
- `topological_sort()`: Get execution order
- `detect_cycles()`: Detect cycles in DAG
- `get_ready_nodes()`: Get nodes ready for execution

### WorkflowExecutor
- `execute(dag, context)`: Execute workflow
- `register_handler(node_type, handler)`: Register node handler
- `pause_workflow(run_id)`: Pause running workflow
- `resume_workflow(run_id)`: Resume paused workflow
- `cancel_workflow(run_id)`: Cancel running workflow

### WorkflowDSL
- `parse_yaml(yaml_content)`: Parse YAML workflow
- `parse_json(json_content)`: Parse JSON workflow
- `validate(dag)`: Validate DAG structure
