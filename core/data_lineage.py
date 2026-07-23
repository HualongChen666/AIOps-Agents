# -*- coding: utf-8 -*-
"""
Data Lineage System for AIOps Platform
Provides data lineage tracking and metadata management using DataHub/Amundsen integration
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Entity type enumeration"""

    DATASET = "dataset"
    JOB = "job"
    PIPELINE = "pipeline"
    SERVICE = "service"
    MODEL = "model"
    METRIC = "metric"


class RelationshipType(Enum):
    """Relationship type enumeration"""

    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    DEPENDS_ON = "depends_on"
    OWNS = "owns"


@dataclass
class Entity:
    """Represents a data entity"""

    id: str
    name: str
    entity_type: EntityType
    description: str
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    owner: Optional[str] = None
    tags: Optional[Set[str]] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = set()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "owner": self.owner,
            "tags": list(self.tags or []),
        }


@dataclass
class Relationship:
    """Represents a relationship between entities"""

    id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    properties: Dict[str, Any]
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class LineageEvent:
    """Represents a lineage event"""

    id: str
    entity_id: str
    event_type: str
    timestamp: datetime
    properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "properties": self.properties,
        }


class DataLineageManager:
    """
    Data Lineage Manager

    Provides:
    - Entity registration and management
    - Relationship tracking
    - Lineage event logging
    - Impact analysis
    - Data provenance tracking
    - Integration with DataHub/Amundsen
    """

    def __init__(self, storage=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Data Lineage Manager

        Args:
            storage: Storage backend for persistence
            config: Configuration dictionary
        """
        self.storage = storage
        self.config = config or {}
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._events: List[LineageEvent] = []
        self._is_initialized = False

        logger.info("Data Lineage Manager initialized")

    def initialize(self) -> bool:
        """
        Initialize data lineage manager

        Returns:
            True if initialization successful
        """
        try:
            if self.storage:
                self._load_from_storage()

            self._is_initialized = True
            logger.info("Data Lineage Manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize data lineage manager: {e}")
            return False

    def _load_from_storage(self) -> None:
        """Load entities and relationships from storage"""
        if self.storage:
            try:
                # Load entities from storage
                entities_data = self.storage.load("data_lineage_entities", {})
                for entity_id, entity_dict in entities_data.items():
                    self._entities[entity_id] = Entity(
                        id=entity_dict["id"],
                        name=entity_dict["name"],
                        entity_type=EntityType(entity_dict["entity_type"]),
                        description=entity_dict["description"],
                        properties=entity_dict["properties"],
                        created_at=datetime.fromisoformat(entity_dict["created_at"]),
                        updated_at=datetime.fromisoformat(entity_dict["updated_at"]),
                        owner=entity_dict.get("owner"),
                        tags=set(entity_dict.get("tags", [])),
                    )

                # Load relationships from storage
                relationships_data = self.storage.load("data_lineage_relationships", {})
                for rel_id, rel_dict in relationships_data.items():
                    self._relationships[rel_id] = Relationship(
                        id=rel_dict["id"],
                        source_id=rel_dict["source_id"],
                        target_id=rel_dict["target_id"],
                        relationship_type=RelationshipType(rel_dict["relationship_type"]),
                        properties=rel_dict["properties"],
                        created_at=datetime.fromisoformat(rel_dict["created_at"]),
                    )

                logger.info(
                    f"Loaded {len(self._entities)} entities and "
                    f"{len(self._relationships)} relationships from storage"
                )
            except Exception as e:
                logger.error(f"Failed to load from storage: {e}")

    def _save_to_storage(self) -> None:
        """Save entities and relationships to storage"""
        if self.storage:
            try:
                # Save entities to storage
                entities_data = {
                    entity_id: entity.to_dict() for entity_id, entity in self._entities.items()
                }
                self.storage.save("data_lineage_entities", entities_data)

                # Save relationships to storage
                relationships_data = {
                    rel_id: rel.to_dict() for rel_id, rel in self._relationships.items()
                }
                self.storage.save("data_lineage_relationships", relationships_data)

                logger.info(
                    f"Saved {len(self._entities)} entities and "
                    f"{len(self._relationships)} relationships to storage"
                )
            except Exception as e:
                logger.error(f"Failed to save to storage: {e}")

    def register_entity(
        self,
        name: str,
        entity_type: EntityType,
        description: str,
        properties: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> Entity:
        """
        Register a new entity

        Args:
            name: Entity name
            entity_type: Entity type
            description: Entity description
            properties: Entity properties
            owner: Entity owner
            tags: Entity tags

        Returns:
            Entity object
        """
        entity_id = str(uuid.uuid4())

        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            description=description,
            properties=properties or {},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            owner=owner,
            tags=tags or set(),
        )

        self._entities[entity_id] = entity

        # Log event
        self._log_event(entity_id, "entity_registered", {"name": name, "type": entity_type.value})

        if self.storage:
            self._save_to_storage()

        logger.info(f"Registered entity: {name} ({entity_type.value})")
        return entity

    def update_entity(
        self,
        entity_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> bool:
        """
        Update an existing entity

        Args:
            entity_id: Entity ID
            name: New name
            description: New description
            properties: New properties
            owner: New owner
            tags: New tags

        Returns:
            True if successful
        """
        if entity_id not in self._entities:
            logger.error(f"Entity not found: {entity_id}")
            return False

        entity = self._entities[entity_id]

        if name is not None:
            entity.name = name
        if description is not None:
            entity.description = description
        if properties is not None:
            entity.properties = properties
        if owner is not None:
            entity.owner = owner
        if tags is not None:
            entity.tags = tags

        entity.updated_at = datetime.now()

        # Log event
        self._log_event(entity_id, "entity_updated", {"name": entity.name})

        if self.storage:
            self._save_to_storage()

        logger.info(f"Updated entity: {entity_id}")
        return True

    def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity

        Args:
            entity_id: Entity ID

        Returns:
            True if successful
        """
        if entity_id not in self._entities:
            logger.error(f"Entity not found: {entity_id}")
            return False

        # Remove entity
        del self._entities[entity_id]

        # Remove relationships
        to_remove = [
            rel_id
            for rel_id, rel in self._relationships.items()
            if rel.source_id == entity_id or rel.target_id == entity_id
        ]

        for rel_id in to_remove:
            del self._relationships[rel_id]

        # Log event
        self._log_event(entity_id, "entity_deleted", {})

        if self.storage:
            self._save_to_storage()

        logger.info(f"Deleted entity: {entity_id}")
        return True

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Relationship:
        """
        Add a relationship between entities

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Relationship type
            properties: Relationship properties

        Returns:
            Relationship object
        """
        if source_id not in self._entities:
            raise ValueError(f"Source entity not found: {source_id}")
        if target_id not in self._entities:
            raise ValueError(f"Target entity not found: {target_id}")

        relationship_id = str(uuid.uuid4())

        relationship = Relationship(
            id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {},
            created_at=datetime.now(),
        )

        self._relationships[relationship_id] = relationship

        # Log event
        self._log_event(
            source_id,
            "relationship_added",
            {"target_id": target_id, "type": relationship_type.value},
        )

        if self.storage:
            self._save_to_storage()

        logger.info(f"Added relationship: {source_id} -> {target_id} ({relationship_type.value})")
        return relationship

    def remove_relationship(self, relationship_id: str) -> bool:
        """
        Remove a relationship

        Args:
            relationship_id: Relationship ID

        Returns:
            True if successful
        """
        if relationship_id not in self._relationships:
            logger.error(f"Relationship not found: {relationship_id}")
            return False

        relationship = self._relationships[relationship_id]

        del self._relationships[relationship_id]

        # Log event
        self._log_event(
            relationship.source_id, "relationship_removed", {"target_id": relationship.target_id}
        )

        if self.storage:
            self._save_to_storage()

        logger.info(f"Removed relationship: {relationship_id}")
        return True

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entity details

        Args:
            entity_id: Entity ID

        Returns:
            Entity dictionary or None
        """
        if entity_id in self._entities:
            return self._entities[entity_id].to_dict()
        return None

    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get entity by name

        Args:
            name: Entity name

        Returns:
            Entity dictionary or None
        """
        for entity in self._entities.values():
            if entity.name == name:
                return entity.to_dict()
        return None

    def list_entities(
        self,
        entity_type: Optional[EntityType] = None,
        owner: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List entities with optional filters

        Args:
            entity_type: Filter by entity type
            owner: Filter by owner
            tags: Filter by tags

        Returns:
            List of entity dictionaries
        """
        entities = list(self._entities.values())

        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        if owner:
            entities = [e for e in entities if e.owner == owner]
        if tags is not None:
            entities = [e for e in entities if tags.issubset(e.tags or [])]

        return [entity.to_dict() for entity in entities]

    def get_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get relationships for an entity

        Args:
            entity_id: Entity ID

        Returns:
            List of relationship dictionaries
        """
        relationships = [
            rel
            for rel in self._relationships.values()
            if rel.source_id == entity_id or rel.target_id == entity_id
        ]

        return [rel.to_dict() for rel in relationships]

    def get_upstream(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get upstream entities

        Args:
            entity_id: Entity ID

        Returns:
            List of upstream entity dictionaries
        """
        upstream_ids = [
            rel.source_id for rel in self._relationships.values() if rel.target_id == entity_id
        ]

        return [self._entities[eid].to_dict() for eid in upstream_ids if eid in self._entities]

    def get_downstream(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get downstream entities

        Args:
            entity_id: Entity ID

        Returns:
            List of downstream entity dictionaries
        """
        downstream_ids = [
            rel.target_id for rel in self._relationships.values() if rel.source_id == entity_id
        ]

        return [self._entities[eid].to_dict() for eid in downstream_ids if eid in self._entities]

    def analyze_impact(self, entity_id: str) -> Dict[str, Any]:
        """
        Analyze impact of entity changes

        Args:
            entity_id: Entity ID

        Returns:
            Impact analysis dictionary
        """
        downstream = self.get_downstream(entity_id)

        impact = {
            "entity_id": entity_id,
            "direct_impact": len(downstream),
            "affected_entities": downstream,
            "total_impact": len(downstream),  # Could be extended with recursive analysis
        }

        return impact

    def get_lineage(self, entity_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        Get lineage graph for an entity

        Args:
            entity_id: Entity ID
            depth: Traversal depth

        Returns:
            Lineage graph dictionary
        """
        lineage = {
            "entity": self.get_entity(entity_id),
            "upstream": self._get_lineage_recursive(entity_id, "upstream", depth),
            "downstream": self._get_lineage_recursive(entity_id, "downstream", depth),
        }

        return lineage

    def _get_lineage_recursive(
        self, entity_id: str, direction: str, depth: int, visited: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recursively get lineage

        Args:
            entity_id: Entity ID
            direction: Direction (upstream/downstream)
            depth: Remaining depth
            visited: Visited entity IDs

        Returns:
            List of entity dictionaries
        """
        if visited is None:
            visited = set()

        if depth == 0 or entity_id in visited:
            return []

        visited.add(entity_id)

        if direction == "upstream":
            entities = self.get_upstream(entity_id)
        else:
            entities = self.get_downstream(entity_id)

        result = []
        for entity in entities:
            result.append(
                {
                    "entity": entity,
                    "children": self._get_lineage_recursive(
                        entity["id"], direction, depth - 1, visited
                    ),
                }
            )

        return result

    def _log_event(self, entity_id: str, event_type: str, properties: Dict[str, Any]) -> None:
        """
        Log a lineage event

        Args:
            entity_id: Entity ID
            event_type: Event type
            properties: Event properties
        """
        event = LineageEvent(
            id=str(uuid.uuid4()),
            entity_id=entity_id,
            event_type=event_type,
            timestamp=datetime.now(),
            properties=properties,
        )

        self._events.append(event)

        # Keep only last 1000 events
        if len(self._events) > 1000:
            self._events = self._events[-1000:]

    def get_events(self, entity_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events for an entity

        Args:
            entity_id: Entity ID
            limit: Maximum number of events

        Returns:
            List of event dictionaries
        """
        events = [event for event in self._events if event.entity_id == entity_id]

        events = events[-limit:]
        return [event.to_dict() for event in events]

    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Search entities by name or description

        Args:
            query: Search query

        Returns:
            List of matching entity dictionaries
        """
        query_lower = query.lower()

        results = [
            entity
            for entity in self._entities.values()
            if query_lower in entity.name.lower() or query_lower in entity.description.lower()
        ]

        return [entity.to_dict() for entity in results]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lineage statistics

        Returns:
            Statistics dictionary
        """
        entity_counts: Dict[str, int] = {}
        for entity in self._entities.values():
            entity_type = entity.entity_type.value
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        relationship_counts: Dict[str, int] = {}
        for rel in self._relationships.values():
            rel_type = rel.relationship_type.value
            relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1

        return {
            "total_entities": len(self._entities),
            "total_relationships": len(self._relationships),
            "total_events": len(self._events),
            "entity_counts": entity_counts,
            "relationship_counts": relationship_counts,
        }


def create_data_lineage_manager(
    storage=None, config: Optional[Dict[str, Any]] = None
) -> Optional[DataLineageManager]:
    """
    Factory function to create Data Lineage Manager

    Args:
        storage: Storage backend
        config: Configuration dictionary

    Returns:
        DataLineageManager instance or None if failed
    """
    try:
        manager = DataLineageManager(storage, config)
        if manager.initialize():
            return manager
        return None
    except Exception as e:
        logger.error(f"Failed to create data lineage manager: {e}")
        return None
