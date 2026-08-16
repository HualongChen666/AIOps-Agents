# -*- coding: utf-8 -*-
"""Real branch-coverage tests for modules/optimization/storage_optimizer.

These tests exercise the real StorageOptimizer, StorageManager, DataCompressor and
DataLifecycleManager with in-memory data. No mocks are used.
"""

from datetime import datetime, timedelta

import pytest

from modules.optimization.storage_optimizer import (
    DataCompressor,
    DataLifecycleManager,
    DataObject,
    StorageManager,
    StorageOptimizer,
    StorageStatistics,
    StorageType,
    create_data_compressor,
    create_data_lifecycle_manager,
    create_storage_manager,
    create_storage_optimizer,
)


def _make_object(
    obj_id,
    name,
    size,
    storage_type=StorageType.HOT,
    age_days=1,
    last_access_days=0,
    access_count=0,
):
    """Create a DataObject with deterministic dates."""
    now = datetime.now()
    return DataObject(
        id=obj_id,
        name=name,
        size=size,
        storage_type=storage_type,
        created_at=now - timedelta(days=age_days),
        last_accessed=now - timedelta(days=last_access_days),
        access_count=access_count,
    )


class TestStorageManagerRealData:
    """Real tests for StorageManager with in-memory objects."""

    def test_storage_manager_basic_operations_and_branches(self):
        manager = create_storage_manager()

        # get / remove / access non-existent objects (false branches)
        assert manager.get_object("missing") is None
        manager.remove_object("missing")  # no exception
        manager.access_object("missing")  # no exception

        hot = _make_object("hot-1", "hot-1.bin", 10 * 1024**3, StorageType.HOT, 5, 2, 10)
        warm = _make_object("warm-1", "warm-1.bin", 5 * 1024**3, StorageType.WARM, 10, 5, 3)
        cold = _make_object("cold-1", "cold-1.bin", 20 * 1024**3, StorageType.COLD, 50, 20, 1)
        archive = _make_object(
            "archive-1", "archive-1.bin", 50 * 1024**3, StorageType.ARCHIVE, 200, 100, 0
        )

        for obj in (hot, warm, cold, archive):
            manager.add_object(obj)

        # exercise DataObject.to_dict()
        assert hot.to_dict()["id"] == "hot-1"

        # existing object access / get
        manager.access_object(hot.id)
        assert manager.get_object(hot.id) is hot
        assert manager.get_object(hot.id).access_count == hot.access_count

        # remove an existing object (true branch)
        manager.remove_object(warm.id)
        assert manager.get_object(warm.id) is None

        stats = manager.get_statistics()
        assert isinstance(stats, StorageStatistics)
        assert stats.to_dict()["total_objects"] == 3
        assert stats.by_type["hot"]["count"] == 1
        assert stats.by_type["archive"]["count"] == 1

        cost = manager.estimate_monthly_cost()
        assert cost > 0

    def test_storage_manager_empty_statistics(self):
        manager = create_storage_manager()
        stats = manager.get_statistics()
        assert stats.to_dict()["total_objects"] == 0
        assert stats.total_size == 0
        assert manager.estimate_monthly_cost() == 0.0


class TestStorageOptimizerTiersAndSavings:
    """Real tests for tier analysis, application and savings estimation."""

    def test_analyze_and_apply_tiering_covers_all_recommendation_branches(self):
        manager = create_storage_manager()
        optimizer = create_storage_optimizer(manager)

        # HOT recommendation already current => no recommendation change
        manager.add_object(
            _make_object("stay-hot", "stay-hot.bin", 1024**3, StorageType.HOT, 5, 2, 10)
        )

        # HOT current but recommended WARM => change
        manager.add_object(
            _make_object("to-warm", "to-warm.bin", 1024**3, StorageType.HOT, 10, 8, 30)
        )

        # COLD recommendation
        manager.add_object(
            _make_object("to-cold", "to-cold.bin", 1024**3, StorageType.HOT, 40, 35, 10)
        )

        # ARCHIVE recommendation
        manager.add_object(
            _make_object("to-archive", "to-archive.bin", 1024**3, StorageType.HOT, 100, 95, 3)
        )

        recommendations = optimizer.analyze_storage_tiering()
        assert "warm" in recommendations and "to-warm" in recommendations["warm"]
        assert "cold" in recommendations and "to-cold" in recommendations["cold"]
        assert "archive" in recommendations and "to-archive" in recommendations["archive"]
        # stay-hot should not appear because it already matches
        assert "stay-hot" not in [oid for ids in recommendations.values() for oid in ids]

        results = optimizer.apply_tiering(recommendations)
        assert results["warm"] == 1
        assert results["cold"] == 1
        assert results["archive"] == 1
        assert manager.get_object("to-warm").storage_type == StorageType.WARM
        assert manager.get_object("to-cold").storage_type == StorageType.COLD
        assert manager.get_object("to-archive").storage_type == StorageType.ARCHIVE

    def test_apply_tiering_missing_object(self):
        manager = create_storage_manager()
        optimizer = create_storage_optimizer(manager)
        manager.add_object(_make_object("real", "real.bin", 1024**3, StorageType.HOT, 100, 95, 0))

        # recommendation for a missing id exercises the `if obj:` false branch
        results = optimizer.apply_tiering({"archive": ["real", "missing"]})
        assert results["archive"] == 1

    def test_recommend_storage_type_all_conditional_branches(self):
        optimizer = create_storage_optimizer(create_storage_manager())

        # each _recommend_storage_type return branch
        assert optimizer._recommend_storage_type(
            _make_object("a", "a.bin", 1, StorageType.HOT, 5, 2, 10)
        ) == StorageType.HOT

        # if first condition true, second false => falls through to WARM
        assert optimizer._recommend_storage_type(
            _make_object("b", "b.bin", 1, StorageType.HOT, 10, 8, 30)
        ) == StorageType.WARM

        # WARM second condition false (days too large), COLD true
        assert optimizer._recommend_storage_type(
            _make_object("c", "c.bin", 1, StorageType.HOT, 40, 35, 10)
        ) == StorageType.COLD

        # WARM first condition false (frequency too low), COLD true
        assert optimizer._recommend_storage_type(
            _make_object("d", "d.bin", 1, StorageType.HOT, 50, 45, 1)
        ) == StorageType.COLD

        # COLD second condition false => ARCHIVE
        assert optimizer._recommend_storage_type(
            _make_object("e", "e.bin", 1, StorageType.HOT, 100, 95, 3)
        ) == StorageType.ARCHIVE

        # COLD first condition false => ARCHIVE
        assert optimizer._recommend_storage_type(
            _make_object("f", "f.bin", 1, StorageType.HOT, 200, 100, 0)
        ) == StorageType.ARCHIVE

    def test_estimate_savings_branches(self):
        manager = create_storage_manager()
        optimizer = create_storage_optimizer(manager)

        # positive saving: HOT -> COLD
        hot = _make_object("save-hot", "save-hot.bin", 10 * 1024**3, StorageType.HOT, 100, 100, 0)
        manager.add_object(hot)
        positive = optimizer.estimate_savings({"cold": ["save-hot"]})
        assert "save-hot" in positive
        assert positive["save-hot"] > 0

        # negative saving (more expensive target) => not included
        cold = _make_object("cost-cold", "cost-cold.bin", 10 * 1024**3, StorageType.COLD, 1, 1, 10)
        manager.add_object(cold)
        negative = optimizer.estimate_savings({"hot": ["cost-cold"]})
        assert "cost-cold" not in negative

        # same type recommendation => no saving
        warm = _make_object("same-warm", "same-warm.bin", 10 * 1024**3, StorageType.WARM, 10, 5, 3)
        manager.add_object(warm)
        same = optimizer.estimate_savings({"warm": ["same-warm"]})
        assert "same-warm" not in same

        # object not in any recommendation list => new_type is None
        alone = _make_object("alone", "alone.bin", 1024**3, StorageType.HOT, 1, 1, 0)
        manager.add_object(alone)
        none_savings = optimizer.estimate_savings({"archive": []})
        assert "alone" not in none_savings


class TestUnusedAndDeletion:
    """Real tests for unused data and deletion suggestions."""

    @pytest.mark.parametrize(
        "last_access,threshold,expected",
        [
            (100, 90, True),  # clearly unused
            (10, 90, False),  # recently used
            (90, 90, False),  # exactly threshold, not >
            (5, 30, False),  # below custom threshold
            (31, 30, True),  # above custom threshold
        ],
    )
    def test_identify_unused_data_thresholds(self, last_access, threshold, expected):
        manager = create_storage_manager()
        optimizer = create_storage_optimizer(manager)
        manager.add_object(
            _make_object("u-1", "u-1.bin", 1024**3, StorageType.HOT, last_access, last_access, 0)
        )
        unused = optimizer.identify_unused_data(days_threshold=threshold)
        assert ("u-1" in [o.id for o in unused]) is expected

    @pytest.mark.parametrize(
        "size,last_access,expected",
        [
            (2 * 1024**3, 200, True),   # large and old
            (1024, 200, False),          # small and old
            (2 * 1024**3, 10, False),    # large and recent
            (1024, 10, False),           # small and recent
        ],
    )
    def test_suggest_deletion_combinations(self, size, last_access, expected):
        manager = create_storage_manager()
        optimizer = create_storage_optimizer(manager)
        manager.add_object(
            _make_object("d-1", "d-1.bin", size, StorageType.HOT, last_access, last_access, 0)
        )
        candidates = optimizer.suggest_deletion(
            size_threshold=1024 * 1024 * 1024, days_threshold=180
        )
        assert ("d-1" in [o.id for o in candidates]) is expected


class TestDataCompressorRealData:
    """Real tests for DataCompressor with real bytes."""

    @pytest.mark.parametrize("algorithm", ["gzip", "zlib", "unknown"])
    def test_compress_data_all_algorithms(self, algorithm):
        compressor = create_data_compressor()
        data = b"x" * 1000
        compressed, ratio = compressor.compress_data(data, algorithm=algorithm)
        assert isinstance(compressed, bytes)
        assert isinstance(ratio, float)
        if algorithm in ("gzip", "zlib"):
            assert len(compressed) < len(data)
            assert ratio > 1.0
        else:
            # unknown algorithm returns original data
            assert compressed == data

    def test_compress_empty_data_unknown_algorithm(self):
        compressor = DataCompressor()
        compressed, ratio = compressor.compress_data(b"", algorithm="raw")
        assert compressed == b""
        assert ratio == 1.0

    def test_estimate_compression_savings(self):
        compressor = DataCompressor()
        objects = [
            _make_object("c-1", "c-1.bin", 10 * 1024**3),
            _make_object("c-2", "c-2.bin", 5 * 1024**3),
        ]
        result = compressor.estimate_compression_savings(objects, estimated_ratio=2.0)
        assert result["total_size"] == sum(o.size for o in objects)
        assert result["savings"] > 0
        assert result["compression_ratio"] == 2.0


class TestDataLifecycleManagerRealData:
    """Real tests for DataLifecycleManager with in-memory policies."""

    def test_lifecycle_transition_and_delete_branches(self):
        manager = create_storage_manager()
        lifecycle = create_data_lifecycle_manager(manager)

        # matching pattern, should transition
        hot_old = _make_object("log-1", "app-1.log", 1024**3, StorageType.HOT, 20, 20, 0)
        # matching pattern but already target type => storage_type != new_type false
        cold_old = _make_object("log-2", "app-2.log", 1024**3, StorageType.ARCHIVE, 20, 20, 0)
        # matching pattern and old => delete
        del_old = _make_object("log-3", "app-3.log", 1024**3, StorageType.HOT, 30, 30, 0)
        # non-matching pattern
        other = _make_object("text-1", "notes.txt", 1024**3, StorageType.HOT, 30, 30, 0)
        # matching but too young for either rule
        young = _make_object("log-4", "app-4.log", 1024**3, StorageType.HOT, 1, 1, 0)

        for obj in (hot_old, cold_old, del_old, other, young):
            manager.add_object(obj)

        lifecycle.add_lifecycle_policy(
            "p1", ".log", {"transition_after_days": 10, "transition_to": "archive"}
        )
        lifecycle.add_lifecycle_policy("p2", ".log", {"delete_after_days": 15})

        actions = lifecycle.apply_lifecycle_policies()

        transition_ids = {
            a["object_id"] for a in actions if a["action"] == "transition"
        }
        delete_ids = {a["object_id"] for a in actions if a["action"] == "delete"}

        assert "log-1" in transition_ids
        assert "log-2" not in transition_ids  # already archive
        assert "log-3" in delete_ids
        assert "log-4" not in transition_ids  # too young
        assert "text-1" not in transition_ids  # no pattern match

        assert manager.get_object("log-3") is None

    def test_lifecycle_empty_and_no_rules(self):
        manager = create_storage_manager()
        lifecycle = create_data_lifecycle_manager(manager)
        manager.add_object(_make_object("x", "x.log", 1, StorageType.HOT, 100, 100, 0))

        # policy with neither transition nor delete rules; pattern matches but no action
        lifecycle.add_lifecycle_policy("noop", ".log", {})
        assert lifecycle.apply_lifecycle_policies() == []

        # no policies at all
        empty = create_data_lifecycle_manager(create_storage_manager())
        assert empty.apply_lifecycle_policies() == []
