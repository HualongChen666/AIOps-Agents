# -*- coding: utf-8 -*-
"""Entity and relation modeling for the Knowledge Graph service."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict

from .schemas import (
    EntityModelingRequest,
    EntityModelingResponse,
    GraphEdge,
    GraphNode,
    RelationModelingRequest,
    RelationModelingResponse,
)


class EntityModeler:
    """Build graph nodes from entity descriptions."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize an entity name to a node ID-friendly string."""
        normalized = re.sub(r"[^\w\s-]", "", name).strip().lower()
        normalized = re.sub(r"[-\s]+", "_", normalized)
        return normalized or str(uuid.uuid4())[:8]

    def model_entity(self, request: EntityModelingRequest) -> EntityModelingResponse:
        """Create a GraphNode from an entity modeling request."""
        node_id = self.normalize_name(request.entity_name)
        properties: Dict[str, Any] = {"display_name": request.entity_name}
        properties.update(request.properties)
        return EntityModelingResponse(
            node_id=node_id,
            entity_name=request.entity_name,
            entity_type=request.entity_type,
            modeled=True,
        )

    def build_node(self, request: EntityModelingRequest) -> GraphNode:
        """Build a GraphNode instance."""
        node_id = self.normalize_name(request.entity_name)
        properties: Dict[str, Any] = {"display_name": request.entity_name}
        properties.update(request.properties)
        return GraphNode(
            node_id=node_id,
            label=request.entity_name,
            node_type=request.entity_type,
            properties=properties,
        )


class RelationModeler:
    """Build graph edges from relation descriptions."""

    def __init__(self, entity_modeler: EntityModeler) -> None:
        self.entity_modeler = entity_modeler

    def model_relation(self, request: RelationModelingRequest) -> RelationModelingResponse:
        """Create a GraphEdge from a relation modeling request."""
        source_id = self.entity_modeler.normalize_name(request.source_name)
        target_id = self.entity_modeler.normalize_name(request.target_name)
        edge_id = f"{source_id}__{request.relation_type}__{target_id}"
        return RelationModelingResponse(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=request.relation_type,
            modeled=True,
        )

    def build_edge(self, request: RelationModelingRequest) -> GraphEdge:
        """Build a GraphEdge instance."""
        source_id = self.entity_modeler.normalize_name(request.source_name)
        target_id = self.entity_modeler.normalize_name(request.target_name)
        edge_id = f"{source_id}__{request.relation_type}__{target_id}"
        return GraphEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=request.relation_type,
            properties=request.properties,
        )
