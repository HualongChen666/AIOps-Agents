# -*- coding: utf-8 -*-
"""测试工作流DSL模块"""

import pytest


class TestWorkflowDSLModule:
    """测试工作流DSL模块"""

    def test_dsl_module_exists(self):
        """测试DSL模块存在"""
        from core.workflow.engine import dsl

        assert dsl is not None

    def test_dsl_has_classes(self):
        """测试DSL模块有类"""
        from core.workflow.engine import dsl

        # 检查模块有类
        assert hasattr(dsl, "WorkflowDSL")

    def test_dsl_has_functions(self):
        """测试DSL模块有函数"""
        from core.workflow.engine import dsl

        # 检查模块有函数
        assert hasattr(dsl, "parse_yaml_workflow")
        assert hasattr(dsl, "parse_json_workflow")


class TestWorkflowDSL:
    """测试工作流DSL类"""

    def test_dsl_initialization(self):
        """测试DSL初始化"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        assert dsl._templates == {}

    def test_load_template(self):
        """测试加载模板"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        template = {"name": "test", "nodes": []}

        dsl.load_template("test_template", template)

        assert "test_template" in dsl._templates

    def test_parse_yaml(self):
        """测试解析YAML"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        yaml_content = """
name: test_workflow
nodes:
  - id: node_1
    name: Task 1
    type: task
  - id: node_2
    name: Task 2
    type: task
edges:
  - from: node_1
    to: node_2
"""

        dag = dsl.parse_yaml(yaml_content)

        assert dag.name == "test_workflow"
        assert "node_1" in dag.nodes
        assert "node_2" in dag.nodes

    def test_parse_yaml_invalid(self):
        """测试解析YAML（无效）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        yaml_content = "invalid: yaml: content: ["

        with pytest.raises(ValueError, match="YAML parsing failed"):
            dsl.parse_yaml(yaml_content)

    def test_parse_yaml_missing_name(self):
        """测试解析YAML（缺少名称）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        yaml_content = """
nodes:
  - id: node_1
"""

        with pytest.raises(ValueError, match="Workflow must have 'name' field"):
            dsl.parse_yaml(yaml_content)

    def test_parse_yaml_missing_nodes(self):
        """测试解析YAML（缺少节点）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        yaml_content = """
name: test_workflow
"""

        with pytest.raises(ValueError, match="Workflow must have 'nodes' field"):
            dsl.parse_yaml(yaml_content)

    def test_parse_yaml_with_cycle(self):
        """测试解析YAML（有循环）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        yaml_content = """
name: test_workflow
nodes:
  - id: node_1
  - id: node_2
edges:
  - from: node_1
    to: node_2
  - from: node_2
    to: node_1
"""

        with pytest.raises(ValueError, match="Workflow contains cycles"):
            dsl.parse_yaml(yaml_content)

    def test_parse_json(self):
        """测试解析JSON"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        json_content = '{"name": "test_workflow", "nodes": [{"id": "node_1", "name": "Task 1"}]}'

        dag = dsl.parse_json(json_content)

        assert dag.name == "test_workflow"
        assert "node_1" in dag.nodes

    def test_parse_json_invalid(self):
        """测试解析JSON（无效）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        json_content = "{invalid json"

        with pytest.raises(ValueError, match="JSON parsing failed"):
            dsl.parse_json(json_content)

    def test_parse_node(self):
        """测试解析节点"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        node_data = {"id": "node_1", "name": "Task 1", "type": "task", "config": {"param": "value"}}

        node = dsl._parse_node(node_data)

        assert node.id == "node_1"
        assert node.name == "Task 1"
        assert node.type == "task"
        assert node.config == {"param": "value"}

    def test_parse_node_missing_id(self):
        """测试解析节点（缺少ID）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        node_data = {"name": "Task 1"}

        with pytest.raises(ValueError, match="Node must have 'id' field"):
            dsl._parse_node(node_data)

    def test_parse_edge(self):
        """测试解析边"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        edge_data = {"from": "node_1", "to": "node_2", "condition": "success"}

        edge = dsl._parse_edge(edge_data)

        assert edge.from_node == "node_1"
        assert edge.to_node == "node_2"
        assert edge.condition == "success"

    def test_parse_edge_missing_fields(self):
        """测试解析边（缺少字段）"""
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        edge_data = {"from": "node_1"}

        with pytest.raises(ValueError, match="Edge must have 'from' and 'to' fields"):
            dsl._parse_edge(edge_data)

    def test_validate_valid_dag(self):
        """测试验证DAG（有效）"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        edge = Edge(from_node="node_1", to_node="node_2")

        dag.add_edge(edge)

        is_valid = dsl.validate(dag)

        assert is_valid is True

    def test_validate_with_cycle(self):
        """测试验证DAG（有循环）"""
        from core.workflow.engine.dag import DAG, DAGNode, Edge
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1")
        node2 = DAGNode(id="node_2", name="Task 2")

        dag.add_node(node1)
        dag.add_node(node2)

        dag.add_edge(Edge(from_node="node_1", to_node="node_2"))
        dag.add_edge(Edge(from_node="node_2", to_node="node_1"))

        is_valid = dsl.validate(dag)

        assert is_valid is False

    def test_validate_missing_dependency(self):
        """测试验证DAG（缺少依赖）"""
        from core.workflow.engine.dag import DAG, DAGNode
        from core.workflow.engine.dsl import WorkflowDSL

        dsl = WorkflowDSL()

        dag = DAG("test_workflow")

        node1 = DAGNode(id="node_1", name="Task 1", dependencies=["missing_node"])

        dag.add_node(node1)

        is_valid = dsl.validate(dag)

        assert is_valid is False


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_parse_yaml_workflow(self):
        """测试解析YAML工作流（便捷函数）"""
        from core.workflow.engine.dsl import parse_yaml_workflow

        yaml_content = """
name: test_workflow
nodes:
  - id: node_1
    name: Task 1
"""

        dag = parse_yaml_workflow(yaml_content)

        assert dag.name == "test_workflow"
        assert "node_1" in dag.nodes

    def test_parse_json_workflow(self):
        """测试解析JSON工作流（便捷函数）"""
        from core.workflow.engine.dsl import parse_json_workflow

        json_content = '{"name": "test_workflow", "nodes": [{"id": "node_1", "name": "Task 1"}]}'

        dag = parse_json_workflow(json_content)

        assert dag.name == "test_workflow"
        assert "node_1" in dag.nodes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
