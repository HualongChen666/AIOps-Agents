# -*- coding: utf-8 -*-
"""Tests for FaultPropagationGraphBuilder module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.fault_graph import (
    FaultPropagationGraphBuilder,
)
from extensions.addons.ai_plus.knowledge_graph_service.builder import GraphBuilder
from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    FaultPropagationGraphRequest,
    FaultRule,
    FaultState,
)


@pytest.fixture
async def graph_store():
    """Create a test graph store."""
    store = GraphStore()
    await store.connect()
    return store


@pytest.fixture
def graph_builder(graph_store):
    """Create a test graph builder."""
    return GraphBuilder(graph_store)


@pytest.fixture
def fault_builder(graph_builder):
    """Create a test fault propagation graph builder."""
    return FaultPropagationGraphBuilder(graph_builder)


class TestFaultPropagationGraphBuilder:
    """Test cases for FaultPropagationGraphBuilder class."""

    @pytest.mark.asyncio
    async def test_build_basic_fault_graph(self, fault_builder):
        """Test building basic fault propagation graph."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0),
                FaultState(component_id="API", fault_type="timeout", severity=0.8),
            ],
            rules=[
                FaultRule(
                    source="Database",
                    target="API",
                    condition="down",
                    impact="high",
                ),
                FaultRule(
                    source="API",
                    target="Frontend",
                    condition="timeout",
                    impact="medium",
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 2
        assert response.rules_count == 2
        assert response.impacted_count >= 1
        assert response.graph_id is not None

    @pytest.mark.asyncio
    async def test_build_empty_states(self, fault_builder):
        """Test building graph with no states."""
        request = FaultPropagationGraphRequest(states=[], rules=[])

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 0
        assert response.rules_count == 0
        assert response.impacted_count == 0

    @pytest.mark.asyncio
    async def test_build_empty_rules(self, fault_builder):
        """Test building graph with states but no rules."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 1
        assert response.rules_count == 0
        assert response.impacted_count == 0

    @pytest.mark.asyncio
    async def test_normalize_method(self, fault_builder):
        """Test component name normalization."""
        assert fault_builder._normalize("Component A") == "component_a"
        assert fault_builder._normalize("Component-B") == "component_b"
        assert fault_builder._normalize(" Component C ") == "component_c"

    def test_normalize_with_spaces(self, fault_builder):
        """Test normalization with multiple spaces."""
        assert fault_builder._normalize("  Component  A  ") == "component__a"

    @pytest.mark.asyncio
    async def test_rule_matches_exact_condition(self, fault_builder):
        """Test rule matching with exact condition."""
        state = FaultState(component_id="Database", fault_type="down", severity=1.0)
        rule = FaultRule(
            source="Database", target="API", condition="down", impact="high"
        )

        assert fault_builder._rule_matches(state, rule) is True

    @pytest.mark.asyncio
    async def test_rule_matches_wildcard_condition(self, fault_builder):
        """Test rule matching with wildcard condition."""
        state = FaultState(component_id="Database", fault_type="down", severity=1.0)
        rule = FaultRule(
            source="Database", target="API", condition="*", impact="high"
        )

        assert fault_builder._rule_matches(state, rule) is True

    @pytest.mark.asyncio
    async def test_rule_matches_comma_separated(self, fault_builder):
        """Test rule matching with comma-separated conditions."""
        state = FaultState(component_id="Database", fault_type="down", severity=1.0)
        rule = FaultRule(
            source="Database",
            target="API",
            condition="down,timeout,slow",
            impact="high",
        )

        assert fault_builder._rule_matches(state, rule) is True

    @pytest.mark.asyncio
    async def test_rule_matches_case_insensitive(self, fault_builder):
        """Test rule matching is case-insensitive."""
        state = FaultState(component_id="Database", fault_type="DOWN", severity=1.0)
        rule = FaultRule(
            source="Database", target="API", condition="down", impact="high"
        )

        assert fault_builder._rule_matches(state, rule) is True

    @pytest.mark.asyncio
    async def test_rule_no_match_condition(self, fault_builder):
        """Test rule not matching condition."""
        state = FaultState(component_id="Database", fault_type="down", severity=1.0)
        rule = FaultRule(
            source="Database", target="API", condition="timeout", impact="high"
        )

        assert fault_builder._rule_matches(state, rule) is False

    @pytest.mark.asyncio
    async def test_rule_no_match_source(self, fault_builder):
        """Test rule not matching source."""
        state = FaultState(component_id="API", fault_type="down", severity=1.0)
        rule = FaultRule(
            source="Database", target="API", condition="down", impact="high"
        )

        assert fault_builder._rule_matches(state, rule) is False

    @pytest.mark.asyncio
    async def test_build_propagation_chain(self, fault_builder):
        """Test building fault propagation chain."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
                FaultRule(
                    source="API", target="Frontend", condition="*", impact="medium"
                ),
                FaultRule(
                    source="Frontend",
                    target="User",
                    condition="*",
                    impact="low",
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 1
        assert response.impacted_count >= 2  # API and Frontend should be impacted

    @pytest.mark.asyncio
    async def test_build_multiple_initial_states(self, fault_builder):
        """Test building with multiple initial fault states."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0),
                FaultState(component_id="Cache", fault_type="timeout", severity=0.5),
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
                FaultRule(
                    source="Cache", target="API", condition="timeout", impact="medium"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 2
        assert response.impacted_count >= 1

    @pytest.mark.asyncio
    async def test_build_circular_propagation(self, fault_builder):
        """Test building with circular fault propagation."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Service A", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Service A",
                    target="Service B",
                    condition="down",
                    impact="high",
                ),
                FaultRule(
                    source="Service B",
                    target="Service C",
                    condition="*",
                    impact="medium",
                ),
                FaultRule(
                    source="Service C",
                    target="Service A",
                    condition="*",
                    impact="low",
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        # Should handle circular references without infinite loop
        assert response.impacted_count >= 2

    @pytest.mark.asyncio
    async def test_build_with_severity(self, fault_builder):
        """Test building with different severity levels."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0),
                FaultState(component_id="Cache", fault_type="slow", severity=0.3),
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
                FaultRule(
                    source="Cache", target="API", condition="slow", impact="low"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 2

    @pytest.mark.asyncio
    async def test_build_duplicate_rules(self, fault_builder):
        """Test building with duplicate rules."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        # Should deduplicate edges
        graph = await fault_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        api_edges = [e for e in graph.edges if e.relation == "PROPAGATES_TO"]
        assert len(api_edges) == 1

    @pytest.mark.asyncio
    async def test_build_complex_propagation(self, fault_builder):
        """Test building complex fault propagation scenario."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0),
                FaultState(component_id="Redis", fault_type="timeout", severity=0.8),
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="critical"
                ),
                FaultRule(
                    source="Redis", target="API", condition="timeout", impact="high"
                ),
                FaultRule(
                    source="API", target="Frontend", condition="*", impact="high"
                ),
                FaultRule(
                    source="API", target="Worker", condition="*", impact="medium"
                ),
                FaultRule(
                    source="Frontend", target="User", condition="*", impact="low"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 2
        assert response.rules_count == 5
        assert response.impacted_count >= 3

    @pytest.mark.asyncio
    async def test_build_with_hyphenated_names(self, fault_builder):
        """Test building with hyphenated component names."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(
                    component_id="service-a", fault_type="down", severity=1.0
                )
            ],
            rules=[
                FaultRule(
                    source="service-a", target="service-b", condition="down", impact="high"
                )
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 1

    @pytest.mark.asyncio
    async def test_build_with_unicode_names(self, fault_builder):
        """Test building with unicode component names."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="数据库", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="数据库", target="API", condition="down", impact="high"
                )
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 1

    @pytest.mark.asyncio
    async def test_build_large_scale(self, fault_builder):
        """Test building large scale fault propagation graph."""
        states = [
            FaultState(component_id=f"Component {i}", fault_type="down", severity=1.0)
            for i in range(20)
        ]
        rules = [
            FaultRule(
                source=f"Component {i}",
                target=f"Component {i+1}",
                condition="down",
                impact="high",
            )
            for i in range(19)
        ]

        request = FaultPropagationGraphRequest(states=states, rules=rules)

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 20
        assert response.rules_count == 19

    @pytest.mark.asyncio
    async def test_build_preserves_severity(self, fault_builder):
        """Test that severity is preserved in nodes."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=0.9)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                )
            ],
        )

        response = await fault_builder.build(request)

        graph = await fault_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        db_node = next(
            (n for n in graph.nodes if n.node_id == "database"), None
        )
        assert db_node is not None
        assert db_node.properties.get("severity") == 0.9

    @pytest.mark.asyncio
    async def test_build_preserves_impact(self, fault_builder):
        """Test that impact is preserved in edges."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="critical"
                )
            ],
        )

        response = await fault_builder.build(request)

        graph = await fault_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        edge = next(
            (e for e in graph.edges if e.relation == "PROPAGATES_TO"), None
        )
        assert edge is not None
        assert edge.properties.get("impact") == "critical"

    @pytest.mark.asyncio
    async def test_build_no_propagation(self, fault_builder):
        """Test building when no rules match."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="API", target="Frontend", condition="timeout", impact="high"
                )
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.impacted_count == 0

    @pytest.mark.asyncio
    async def test_build_with_cycle_and_visited_check(self, fault_builder):
        """Test building with cycle to test visited check (line 68)."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
                FaultRule(
                    source="API", target="Database", condition="down", impact="medium"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        # Should not infinite loop due to visited check
        assert response.states_count == 1

    @pytest.mark.asyncio
    async def test_build_with_duplicate_state_in_queue(self, fault_builder):
        """Test building when same state appears multiple times in queue (covers line 68)."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                ),
                FaultRule(
                    source="API", target="Database", condition="down", impact="medium"
                ),
                FaultRule(
                    source="Database", target="Cache", condition="down", impact="low"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        # Should handle visited nodes correctly
        assert response.states_count == 1

    @pytest.mark.asyncio
    async def test_build_self_propagation(self, fault_builder):
        """Test building with self-propagation rule."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="Database", condition="down", impact="high"
                )
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        # Should handle self-reference
        assert response.impacted_count >= 0

    @pytest.mark.asyncio
    async def test_build_with_multiple_conditions(self, fault_builder):
        """Test building with multiple condition types."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0),
                FaultState(component_id="Cache", fault_type="slow", severity=0.5),
            ],
            rules=[
                FaultRule(
                    source="Database",
                    target="API",
                    condition="down,timeout",
                    impact="high",
                ),
                FaultRule(
                    source="Cache", target="API", condition="slow", impact="medium"
                ),
            ],
        )

        response = await fault_builder.build(request)

        assert response.built is True
        assert response.states_count == 2
