# -*- coding: utf-8 -*-
"""
LangGraph Workflow Visualizer
Generates visualizations for workflows using Graphviz and Mermaid
"""

from typing import Optional

from loguru import logger

from .workflow import Workflow


class WorkflowVisualizer:
    """
    Workflow visualization generator
    """

    @staticmethod
    def to_mermaid(workflow: Workflow) -> str:
        """
        Generate Mermaid diagram for workflow

        Args:
            workflow: Workflow to visualize

        Returns:
            Mermaid diagram string
        """
        return workflow.to_mermaid()

    @staticmethod
    def to_graphviz(workflow: Workflow) -> str:
        """
        Generate Graphviz DOT format for workflow

        Args:
            workflow: Workflow to visualize

        Returns:
            Graphviz DOT string
        """
        lines = ["digraph workflow {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box];")

        # Add nodes
        for node_name, node in workflow.nodes.items():
            safe_name = node_name.replace(" ", "_").replace("-", "_")
            label = f"{node_name}\\n({node.node_type})"
            lines.append(f'  {safe_name} [label="{label}"];')

        # Add edges
        for edge in workflow.edges:
            from_safe = edge.from_node.replace(" ", "_").replace("-", "_")
            to_safe = edge.to_node.replace(" ", "_").replace("-", "_")
            lines.append(f"  {from_safe} -> {to_safe};")

        # Mark start and end nodes
        if workflow.start_node:
            start_safe = workflow.start_node.replace(" ", "_").replace("-", "_")
            lines.append(f"  {start_safe} [style=filled, fillcolor=lightgreen];")

        for end_node in workflow.end_nodes:
            end_safe = end_node.replace(" ", "_").replace("-", "_")
            lines.append(f"  {end_safe} [style=filled, fillcolor=lightblue];")

        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def to_ascii(workflow: Workflow) -> str:
        """
        Generate ASCII art visualization

        Args:
            workflow: Workflow to visualize

        Returns:
            ASCII art string
        """
        lines = []
        lines.append(f"Workflow: {workflow.name}")
        lines.append("=" * 50)

        for node_name, node in workflow.nodes.items():
            lines.append(f"  [{node.node_type}] {node_name}")

        lines.append("\nEdges:")
        for edge in workflow.edges:
            lines.append(f"  {edge.from_node} -> {edge.to_node}")

        lines.append(f"\nStart: {workflow.start_node}")
        lines.append(f"End: {', '.join(workflow.end_nodes)}")

        return "\n".join(lines)

    @staticmethod
    async def render_mermaid(workflow: Workflow, output_path: Optional[str] = None) -> str:
        """
        Render Mermaid diagram to image (requires mermaid-cli)

        Args:
            workflow: Workflow to render
            output_path: Output file path

        Returns:
            Mermaid diagram string
        """
        mermaid = WorkflowVisualizer.to_mermaid(workflow)

        if output_path:
            try:
                # Write mermaid to file
                with open(output_path, "w") as f:
                    f.write(mermaid)
                logger.info(f"Mermaid diagram saved to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save mermaid diagram: {e}")

        return mermaid

    @staticmethod
    async def render_graphviz(workflow: Workflow, output_path: Optional[str] = None) -> str:
        """
        Render Graphviz diagram to image (requires graphviz)

        Args:
            workflow: Workflow to render
            output_path: Output file path

        Returns:
            Graphviz DOT string
        """
        dot = WorkflowVisualizer.to_graphviz(workflow)

        if output_path:
            try:
                # Write dot to file
                with open(output_path, "w") as f:
                    f.write(dot)
                logger.info(f"Graphviz DOT saved to {output_path}")

                # Try to render to PNG if graphviz is available
                try:
                    import shutil
                    import subprocess  # nosec B404

                    dot_path = shutil.which("dot") or "dot"
                    subprocess.run(
                        [dot_path, "-Tpng", output_path, "-o", output_path.replace(".dot", ".png")],
                        shell=False,  # nosec B603
                        check=True,
                    )
                    logger.info("Graphviz PNG saved")
                except Exception as e:
                    logger.warning(f"Graphviz render failed: {e}")

            except Exception as e:
                logger.error(f"Failed to save graphviz diagram: {e}")

        return dot


__all__ = ["WorkflowVisualizer"]
