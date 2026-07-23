# LangGraph AI Orchestration Framework

## Overview
This module implements LangGraph framework for building complex AI workflows in AIOps Agent.

## Architecture
- **State Machine**: Manages workflow state transitions
- **Node Types**: LLM nodes, tool nodes, conditional nodes
- **Execution Engine**: Orchestrates workflow execution
- **Visualization**: Graphviz/Mermaid diagram generation

## Components
- `workflow.py`: Core workflow state machine
- `nodes.py`: Base node types and implementations
- `executor.py`: Workflow execution engine
- `dsl.py`: Workflow definition DSL
- `visualizer.py`: Workflow visualization

## Usage
```python
from aiops_core.ai.langgraph import Workflow, LLMNode, ToolNode

# Define workflow
workflow = Workflow("incident_analysis")
workflow.add_node(LLMNode("analyze"))
workflow.add_node(ToolNode("execute_repair"))
workflow.add_edge("analyze", "execute_repair")

# Execute
result = workflow.execute(context)
```
