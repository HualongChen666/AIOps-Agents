# -*- coding: utf-8 -*-
"""Tests for EntityModeler and RelationModeler modules."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.modeler import (
    EntityModeler,
    RelationModeler,
)
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    EntityModelingRequest,
    EntityModelingResponse,
    RelationModelingRequest,
    RelationModelingResponse,
    GraphNode,
    GraphEdge,
)


class TestEntityModeler:
    """Test cases for EntityModeler class."""

    def test_normalize_name_basic(self):
        """Test basic name normalization."""
        assert EntityModeler.normalize_name("Test Entity") == "test_entity"
        assert EntityModeler.normalize_name("Test-Entity") == "test_entity"
        assert EntityModeler.normalize_name("  Test Entity  ") == "test_entity"

    def test_normalize_name_with_special_chars(self):
        """Test normalization with special characters."""
        assert EntityModeler.normalize_name("Test@Entity!") == "testentity"
        assert EntityModeler.normalize_name("Test#Entity$") == "testentity"

    def test_normalize_name_with_numbers(self):
        """Test normalization with numbers."""
        assert EntityModeler.normalize_name("Test123") == "test123"
        assert EntityModeler.normalize_name("Test 123") == "test_123"

    def test_normalize_name_empty(self):
        """Test normalization with empty string."""
        result = EntityModeler.normalize_name("")
        assert result is not None
        assert len(result) == 8  # UUID prefix

    def test_normalize_name_special_only(self):
        """Test normalization with only special characters."""
        result = EntityModeler.normalize_name("@#$%")
        assert result is not None
        assert len(result) == 8  # UUID prefix

    def test_normalize_name_multiple_spaces(self):
        """Test normalization with multiple spaces."""
        assert EntityModeler.normalize_name("Test   Entity") == "test_entity"
        assert EntityModeler.normalize_name("Test    Entity   Name") == "test_entity_name"

    def test_normalize_name_mixed_case(self):
        """Test normalization preserves lowercase."""
        assert EntityModeler.normalize_name("TEST ENTITY") == "test_entity"
        assert EntityModeler.normalize_name("TeSt EnTiTy") == "test_entity"

    def test_model_entity_basic(self):
        """Test basic entity modeling."""
        modeler = EntityModeler()
        request = EntityModelingRequest(
            entity_name="Test Entity", entity_type="generic"
        )

        response = modeler.model_entity(request)

        assert isinstance(response, EntityModelingResponse)
        assert response.entity_name == "Test Entity"
        assert response.entity_type == "generic"
        assert response.node_id == "test_entity"
        assert response.modeled is True

    def test_model_entity_with_properties(self):
        """Test entity modeling with properties."""
        modeler = EntityModeler()
        request = EntityModelingRequest(
            entity_name="Test Entity",
            entity_type="custom",
            properties={"key": "value", "number": 123},
        )

        response = modeler.model_entity(request)

        assert response.entity_type == "custom"
        assert response.node_id == "test_entity"

    def test_model_entity_with_special_chars(self):
        """Test entity modeling with special characters in name."""
        modeler = EntityModeler()
        request = EntityModelingRequest(
            entity_name="Test@Entity!", entity_type="generic"
        )

        response = modeler.model_entity(request)

        assert response.node_id == "testentity"

    def test_build_node_basic(self):
        """Test basic node building."""
        modeler = EntityModeler()
        request = EntityModelingRequest(
            entity_name="Test Entity", entity_type="generic"
        )

        node = modeler.build_node(request)

        assert isinstance(node, GraphNode)
        assert node.node_id == "test_entity"
        assert node.label == "Test Entity"
        assert node.node_type == "generic"
        assert node.properties["display_name"] == "Test Entity"

    def test_build_node_with_properties(self):
        """Test node building with custom properties."""
        modeler = EntityModeler()
        request = EntityModelingRequest(
            entity_name="Test Entity",
            entity_type="custom",
            properties={"custom_key": "custom_value"},
        )

        node = modeler.build_node(request)

        assert node.properties["display_name"] == "Test Entity"
        assert node.properties["custom_key"] == "custom_value"

    def test_build_node_properties_merge(self):
        """Test that custom properties are merged with display_name."""
        modeler = EntityModeler()
        request = EntityModelingRequest(
            entity_name="Test Entity",
            entity_type="generic",
            properties={"existing_key": "existing_value"},
        )

        node = modeler.build_node(request)

        assert "display_name" in node.properties
        assert "existing_key" in node.properties
        assert node.properties["display_name"] == "Test Entity"
        assert node.properties["existing_key"] == "existing_value"


class TestRelationModeler:
    """Test cases for RelationModeler class."""

    def test_initialization(self):
        """Test RelationModeler initialization."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        assert relation_modeler.entity_modeler == entity_modeler

    def test_model_relation_basic(self):
        """Test basic relation modeling."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Source Entity",
            target_name="Target Entity",
            relation_type="CONNECTS_TO",
        )

        response = relation_modeler.model_relation(request)

        assert isinstance(response, RelationModelingResponse)
        assert response.source_id == "source_entity"
        assert response.target_id == "target_entity"
        assert response.relation_type == "CONNECTS_TO"
        assert response.edge_id == "source_entity__CONNECTS_TO__target_entity"
        assert response.modeled is True

    def test_model_relation_with_properties(self):
        """Test relation modeling with properties."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Source",
            target_name="Target",
            relation_type="DEPENDS_ON",
            properties={"weight": 1.0},
        )

        response = relation_modeler.model_relation(request)

        assert response.relation_type == "DEPENDS_ON"

    def test_model_relation_with_special_chars(self):
        """Test relation modeling with special characters."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Source@Entity",
            target_name="Target#Entity",
            relation_type="CONNECTS_TO",
        )

        response = relation_modeler.model_relation(request)

        assert response.source_id == "sourceentity"
        assert response.target_id == "targetentity"

    def test_build_edge_basic(self):
        """Test basic edge building."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Source Entity",
            target_name="Target Entity",
            relation_type="CONNECTS_TO",
        )

        edge = relation_modeler.build_edge(request)

        assert isinstance(edge, GraphEdge)
        assert edge.source_id == "source_entity"
        assert edge.target_id == "target_entity"
        assert edge.relation == "CONNECTS_TO"
        assert edge.edge_id == "source_entity__CONNECTS_TO__target_entity"

    def test_build_edge_with_properties(self):
        """Test edge building with custom properties."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Source",
            target_name="Target",
            relation_type="DEPENDS_ON",
            properties={"weight": 2.5, "type": "strong"},
        )

        edge = relation_modeler.build_edge(request)

        assert edge.properties == {"weight": 2.5, "type": "strong"}

    def test_build_edge_id_format(self):
        """Test edge ID format."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Service A",
            target_name="Service B",
            relation_type="CALLS",
        )

        edge = relation_modeler.build_edge(request)

        assert edge.edge_id == "service_a__CALLS__service_b"

    def test_model_relation_uses_entity_modeler(self):
        """Test that relation modeler uses entity modeler for normalization."""
        entity_modeler = EntityModeler()
        relation_modeler = RelationModeler(entity_modeler)
        request = RelationModelingRequest(
            source_name="Test Source",
            target_name="Test Target",
            relation_type="CONNECTS_TO",
        )

        response = relation_modeler.model_relation(request)

        # Verify the same normalization is applied
        assert response.source_id == entity_modeler.normalize_name("Test Source")
        assert response.target_id == entity_modeler.normalize_name("Test Target")
