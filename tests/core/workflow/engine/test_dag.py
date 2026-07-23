# -*- coding: utf-8 -*-
"""测试DAG工作流引擎模块"""

import pytest


class TestDAGModule:
    """测试DAG模块"""

    def test_dag_module_exists(self):
        """测试DAG模块存在"""
        from core.workflow.engine import dag

        assert dag is not None

    def test_dag_has_enums(self):
        """测试DAG模块有枚举"""
        from core.workflow.engine import dag

        # 检查模块有枚举
        assert hasattr(dag, "NodeStatus")

    def test_dag_has_dataclasses(self):
        """测试DAG模块有数据类"""
        from core.workflow.engine import dag

        # 检查模块有数据类
        assert hasattr(dag, "DAGNode")
        assert hasattr(dag, "Edge")

    def test_dag_has_classes(self):
        """测试DAG模块有类"""
        from core.workflow.engine import dag

        # 检查模块有类
        assert hasattr(dag, "DAG")


class TestNodeStatus:
    """测试节点状态枚举"""

    def test_node_status_values(self):
        """测试节点状态值"""
        from core.workflow.engine.dag import NodeStatus

        assert NodeStatus.PENDING.value == "pending"
        assert NodeStatus.RUNNING.value == "running"
        assert NodeStatus.SUCCESS.value == "success"
        assert NodeStatus.FAILED.value == "failed"
        assert NodeStatus.SKIPPED.value == "skipped"


class TestDAGNode:
    """测试DAG节点数据类"""

    def test_dag_node_creation(self):
        """测试DAG节点创建"""
        from core.workflow.engine.dag import DAGNode, NodeStatus

        node = DAGNode(
            id="node_1",
            name="Task 1",
            type="task",
            config={"param": "value"},
            dependencies=[],
            status=NodeStatus.PENDING,
        )

        assert node.id == "node_1"
        assert node.name == "Task 1"
        assert node.type == "task"
        assert node.status == NodeStatus.PENDING

    def test_dag_node_to_dict(self):
        """测试DAG节点转字典"""
        from core.workflow.engine.dag import DAGNode, NodeStatus

        node = DAGNode(
            id="node_1",
            name="Task 1",
            type="task",
            config={"param": "value"},
            dependencies=[],
            status=NodeStatus.SUCCESS,
            result="done",
        )

        node_dict = node.to_dict()

        assert node_dict["id"] == "node_1"
        assert node_dict["name"] == "Task 1"
        assert node_dict["status"] == "success"
        assert node_dict["result"] == "done"


class TestEdge:
    """测试边数据类"""

    def test_edge_creation(self):
        """测试边创建"""
        from core.workflow.engine.dag import Edge

        edge = Edge(
            from_node="node_1",
            to_node="node_2",
            condition="success",
        )

        assert edge.from_node == "node_1"
        assert edge.to_node == "node_2"
        assert edge.condition == "success"

    def test_edge_creation_without_condition(self):
        """测试边创建（无条件）"""
        from core.workflow.engine.dag import Edge

        edge = Edge(
            from_node="node_1",
            to_node="node_2",
        )

        assert edge.from_node == "node_1"
        assert edge.to_node == "node_2"
        assert edge.condition is None


class TestDAG:
    """测试DAG类"""

    def test_dag_initialization(self):
        """测试DAG初始化"""
        from core.workflow.engine.dag import DAG

        dag = DAG(name="test_workflow")

        assert dag.name == "test_workflow"
        assert dag.nodes == {}
        assert dag.edges == []

    def test_add_node(self):
        """测试添加节点"""
        from core.workflow.engine.dag import DAG, DAGNode

        dag = DAG(name="test_workflow")

        node = DAGNode(id="node_1", name="Task 1")

        dag.add_node(node)

        assert "node_1" in dag.nodes
        assert dag.nodes["node_1"].name == "Task 1"

    def test_add_edge(self):
        """测试添加边"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        assert len(dag.edges) == 1
        assert dag.edges[0].from_node == "node_1"
        assert dag.edges[0].to_node == "node_2"

    def test_add_edge_updates_dependencies(self):
        """测试添加边更新依赖"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        assert "node_1" in dag.nodes["node_2"].dependencies

    def test_remove_node(self):
        """测试移除节点"""
        from core.workflow.engine.dag import DAG, DAGNode

        dag = DAG(name="test_workflow")

        node = DAGNode(id="node_1", name="Task 1")

        dag.add_node(node)

        assert "node_1" in dag.nodes

        dag.remove_node("node_1")

        assert "node_1" not in dag.nodes

    def test_remove_node_with_edges(self):
        """测试移除节点（带边）"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        dag.remove_node("node_1")

        assert "node_1" not in dag.nodes
        assert len(dag.edges) == 0

    def test_get_dependencies(self):
        """测试获取依赖"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        deps = dag.get_dependencies("node_2")

        assert "node_1" in deps

    def test_get_dependencies_invalid_node(self):
        """测试获取依赖（无效节点）"""
        from core.workflow.engine.dag import DAG

        dag = DAG(name="test_workflow")

        deps = dag.get_dependencies("invalid_node")

        assert deps == []

    def test_get_dependents(self):
        """测试获取依赖者"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        # get_dependents returns nodes that have edges TO the given node
        # Since node_1 -> node_2, node_2 has an incoming edge from node_1
        # So get_dependents("node_2") should return ["node_1"]
        dependents = dag.get_dependents("node_2")

        assert "node_1" in dependents

    def test_topological_sort(self):
        """测试拓扑排序"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")
        node3 = DAGNode(id="node_3", name="Task 3")

        dag.add_node(node1)
        dag.add_node(node2)
        dag.add_node(node3)

        dag.add_edge(Edge(from_node="node_1", to_node="node_2"))
        dag.add_edge(Edge(from_node="node_2", to_node="node_3"))

        sorted_nodes = dag.topological_sort()

        assert sorted_nodes.index("node_1") < sorted_nodes.index("node_2")
        assert sorted_nodes.index("node_2") < sorted_nodes.index("node_3")

    def test_topological_sort_cycle(self):
        """测试拓扑排序（循环）"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        dag.add_edge(Edge(from_node="node_1", to_node="node_2"))
        dag.add_edge(Edge(from_node="node_2", to_node="node_1"))

        with pytest.raises(ValueError, match="Cycle detected"):
            dag.topological_sort()

    def test_detect_cycles_no_cycle(self):
        """测试检测循环（无循环）"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        dag.add_edge(Edge(from_node="node_1", to_node="node_2"))

        cycles = dag.detect_cycles()

        assert len(cycles) == 0

    def test_detect_cycles_with_cycle(self):
        """测试检测循环（有循环）"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        dag.add_edge(Edge(from_node="node_1", to_node="node_2"))
        dag.add_edge(Edge(from_node="node_2", to_node="node_1"))

        cycles = dag.detect_cycles()

        assert len(cycles) > 0

    def test_get_ready_nodes(self):
        """测试获取就绪节点"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge, NodeStatus

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", status=NodeStatus.SUCCESS)
        node2 = DAGNode(id="node_2", name="Task 2", status=NodeStatus.PENDING)
        node3 = DAGNode(id="node_3", name="Task 3", status=NodeStatus.PENDING)

        dag.add_node(node1)
        dag.add_node(node2)
        dag.add_node(node3)

        dag.add_edge(Edge(from_node="node_1", to_node="node_2"))
        dag.add_edge(Edge(from_node="node_1", to_node="node_3"))

        ready = dag.get_ready_nodes()

        assert "node_2" in ready
        assert "node_3" in ready

    def test_get_ready_nodes_no_dependencies(self):
        """测试获取就绪节点（无依赖）"""
        from core.workflow.engine.dag import DAG, DAGNode, NodeStatus

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", status=NodeStatus.PENDING)

        dag.add_node(node1)

        ready = dag.get_ready_nodes()

        assert "node_1" in ready

    def test_to_dict(self):
        """测试转字典"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        dag_dict = dag.to_dict()

        assert dag_dict["name"] == "test_workflow"
        assert "node_1" in dag_dict["nodes"]
        assert len(dag_dict["edges"]) == 1

    def test_to_json(self):
        """测试转JSON"""
        from core.workflow.engine.dag import DAG, DAGNode

        dag = DAG(name="test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")

        dag.add_node(node1)

        dag_json = dag.to_json()

        assert "test_workflow" in dag_json
        assert "node_1" in dag_json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
