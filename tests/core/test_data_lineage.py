# -*- coding: utf-8 -*-
"""Tests for core/data_lineage.py."""

from unittest.mock import MagicMock

from core.data_lineage import DataLineageManager, EntityType, RelationshipType


def _manager():
    storage = MagicMock()
    storage.load.return_value = {}
    return DataLineageManager(storage=storage)


def test_initialize_and_storage():
    manager = _manager()
    assert manager.initialize() is True
    assert manager._is_initialized is True


def test_register_and_get_entity():
    manager = _manager()
    entity = manager.register_entity("Entity 1", EntityType.DATASET, "desc")
    fetched = manager.get_entity(entity.id)
    assert fetched["name"] == "Entity 1"
    assert manager.get_entity("missing") is None


def test_update_and_delete_entity():
    manager = _manager()
    entity = manager.register_entity("Entity 1", EntityType.DATASET, "desc")
    assert manager.update_entity(entity.id, tags={"a"}) is True
    assert manager.delete_entity(entity.id) is True
    assert manager.delete_entity(entity.id) is False


def test_relationships_and_lineage():
    manager = _manager()
    a = manager.register_entity("A", EntityType.DATASET, "desc")
    b = manager.register_entity("B", EntityType.DATASET, "desc")
    rel = manager.add_relationship(a.id, b.id, RelationshipType.PRODUCES)
    assert rel is not None

    rels = manager.get_relationships(a.id)
    assert len(rels) == 1
    assert manager.get_upstream(b.id)[0]["id"] == a.id
    assert manager.get_downstream(a.id)[0]["id"] == b.id

    lineage = manager.get_lineage(a.id, depth=2)
    assert lineage["entity"]["id"] == a.id

    impact = manager.analyze_impact(a.id)
    assert impact["entity_id"] == a.id
    assert impact["direct_impact"] == 1

    assert manager.remove_relationship(rel.id) is True


def test_events_search_and_stats():
    manager = _manager()
    entity = manager.register_entity("Entity 1", EntityType.DATASET, "desc")
    manager._log_event(entity.id, "created", {"by": "test"})
    events = manager.get_events(entity.id)
    assert any(e["event_type"] == "created" for e in events)
    assert manager.search_entities("Entity")[0]["name"] == "Entity 1"
    stats = manager.get_statistics()
    assert "total_entities" in stats
