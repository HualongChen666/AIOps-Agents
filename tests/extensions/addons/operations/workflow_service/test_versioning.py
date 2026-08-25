# -*- coding: utf-8 -*-
"""Tests for workflow_service versioning module."""

import json

import pytest
from schemas import WorkflowDefinition
from versioning import (
    WorkflowVersionManager,
)


class TestWorkflowVersionManager:
    """Test cases for WorkflowVersionManager class."""

    def test_version_manager_initialization(self):
        """Test that WorkflowVersionManager initializes correctly."""
        manager = WorkflowVersionManager()
        assert len(manager._versions) == 0

    @pytest.mark.asyncio
    async def test_commit_version(self, version_manager, workflow_definition):
        """Test committing a workflow version."""
        version = await version_manager.commit(workflow_definition, "Initial commit")

        assert version is not None
        assert version.workflow_id == workflow_definition.workflow_id
        assert version.message == "Initial commit"
        assert version.version == "v1.0.0"
        assert len(version.commit_hash) == 16
        assert workflow_definition.workflow_id in manager._versions

    @pytest.mark.asyncio
    async def test_commit_generates_unique_hash(self, version_manager, workflow_definition):
        """Test that commit generates unique commit hashes."""
        version1 = await version_manager.commit(workflow_definition, "Commit 1")
        version2 = await version_manager.commit(workflow_definition, "Commit 2")

        assert version1.commit_hash != version2.commit_hash

    @pytest.mark.asyncio
    async def test_commit_increments_version_number(self, version_manager, workflow_definition):
        """Test that commit increments version number correctly."""
        version1 = await version_manager.commit(workflow_definition, "First")
        version2 = await version_manager.commit(workflow_definition, "Second")
        version3 = await version_manager.commit(workflow_definition, "Third")

        assert version1.version == "v1.0.0"
        assert version2.version == "v2.0.0"
        assert version3.version == "v3.0.0"

    @pytest.mark.asyncio
    async def test_commit_different_workflows(self, version_manager):
        """Test committing versions for different workflows."""
        def1 = WorkflowDefinition(workflow_id="workflow-1", name="Workflow 1")
        def2 = WorkflowDefinition(workflow_id="workflow-2", name="Workflow 2")

        version1 = await version_manager.commit(def1, "Commit for workflow 1")
        version2 = await version_manager.commit(def2, "Commit for workflow 2")

        assert version1.workflow_id == "workflow-1"
        assert version2.workflow_id == "workflow-2"
        assert version1.version == "v1.0.0"
        assert version2.version == "v1.0.0"  # Different workflow, starts at v1.0.0

    @pytest.mark.asyncio
    async def test_commit_with_default_message(self, version_manager, workflow_definition):
        """Test commit with default message."""
        version = await version_manager.commit(workflow_definition)

        assert version.message == "Workflow snapshot"

    @pytest.mark.asyncio
    async def test_commit_with_custom_message(self, version_manager, workflow_definition):
        """Test commit with custom message."""
        custom_message = "Added new node for data processing"
        version = await version_manager.commit(workflow_definition, custom_message)

        assert version.message == custom_message

    @pytest.mark.asyncio
    async def test_commit_hash_based_on_content(self, version_manager, workflow_definition):
        """Test that commit hash is based on workflow content."""
        version1 = await version_manager.commit(workflow_definition, "First")

        # Modify the definition
        workflow_definition.name = "Updated Name"
        version2 = await version_manager.commit(workflow_definition, "Second")

        # Hashes should be different because content changed
        assert version1.commit_hash != version2.commit_hash

    @pytest.mark.asyncio
    async def test_commit_same_content_same_hash(self, version_manager, workflow_definition):
        """Test that same content produces same hash."""
        version1 = await version_manager.commit(workflow_definition, "First")
        version2 = await version_manager.commit(workflow_definition, "Second")

        # Same content should produce same hash (though this might not be the case
        # depending on implementation, testing the behavior)
        # In current implementation, hash is based on content only
        assert version1.commit_hash == version2.commit_hash

    @pytest.mark.asyncio
    async def test_commit_with_complex_definition(self, version_manager):
        """Test commit with complex workflow definition."""
        from extensions.addons.operations.workflow_service.schemas import WorkflowNode

        complex_def = WorkflowDefinition(
            workflow_id="complex-workflow",
            name="Complex Workflow",
            description="A complex workflow",
            nodes=[
                WorkflowNode(
                    node_id="node1",
                    name="Node 1",
                    command="echo test",
                    dependencies=[],
                ),
                WorkflowNode(
                    node_id="node2",
                    name="Node 2",
                    command="echo test2",
                    dependencies=["node1"],
                ),
            ],
            metadata={"key": "value", "number": 42},
        )

        version = await version_manager.commit(complex_def, "Complex commit")

        assert version is not None
        assert version.workflow_id == "complex-workflow"

    @pytest.mark.asyncio
    async def test_list_versions_empty(self, version_manager):
        """Test listing versions when none exist."""
        versions = await version_manager.list_versions("workflow-1")
        assert versions == []

    @pytest.mark.asyncio
    async def test_list_versions_with_data(self, version_manager, workflow_definition):
        """Test listing versions with data."""
        await version_manager.commit(workflow_definition, "First")
        await version_manager.commit(workflow_definition, "Second")

        versions = await version_manager.list_versions(workflow_definition.workflow_id)

        assert len(versions) == 2
        assert versions[0].version == "v1.0.0"
        assert versions[1].version == "v2.0.0"

    @pytest.mark.asyncio
    async def test_list_versions_with_limit(self, version_manager, workflow_definition):
        """Test listing versions with limit parameter."""
        for i in range(10):
            await version_manager.commit(workflow_definition, f"Commit {i}")

        versions = await version_manager.list_versions(workflow_definition.workflow_id, limit=5)

        assert len(versions) == 5
        # Should return the most recent 5 versions
        assert versions[0].version == "v6.0.0"
        assert versions[4].version == "v10.0.0"

    @pytest.mark.asyncio
    async def test_list_versions_limit_zero(self, version_manager, workflow_definition):
        """Test listing versions with limit=0."""
        await version_manager.commit(workflow_definition, "First")

        versions = await version_manager.list_versions(workflow_definition.workflow_id, limit=0)

        assert versions == []

    @pytest.mark.asyncio
    async def test_list_versions_limit_exceeds_total(self, version_manager, workflow_definition):
        """Test listing versions when limit exceeds total count."""
        await version_manager.commit(workflow_definition, "First")
        await version_manager.commit(workflow_definition, "Second")

        versions = await version_manager.list_versions(workflow_definition.workflow_id, limit=100)

        assert len(versions) == 2

    @pytest.mark.asyncio
    async def test_list_versions_non_existent_workflow(self, version_manager):
        """Test listing versions for non-existent workflow."""
        versions = await version_manager.list_versions("non-existent")
        assert versions == []

    @pytest.mark.asyncio
    async def test_list_versions_order(self, version_manager, workflow_definition):
        """Test that list_versions returns versions in chronological order."""
        for i in range(5):
            await version_manager.commit(workflow_definition, f"Commit {i}")

        versions = await version_manager.list_versions(workflow_definition.workflow_id)

        version_numbers = [v.version for v in versions]
        assert version_numbers == ["v1.0.0", "v2.0.0", "v3.0.0", "v4.0.0", "v5.0.0"]

    @pytest.mark.asyncio
    async def test_compare_versions(self, version_manager, workflow_definition):
        """Test comparing two workflow versions."""
        await version_manager.commit(workflow_definition, "First")
        await version_manager.commit(workflow_definition, "Second")

        comparison = await version_manager.compare(
            workflow_definition.workflow_id, "v1.0.0", "v2.0.0"
        )

        assert comparison["workflow_id"] == workflow_definition.workflow_id
        assert comparison["from_version"] == "v1.0.0"
        assert comparison["to_version"] == "v2.0.0"
        assert comparison["version_count"] == 2
        assert comparison["from_index"] == 0
        assert comparison["to_index"] == 1
        assert comparison["diff"] == "versions-differ"

    @pytest.mark.asyncio
    async def test_compare_same_version(self, version_manager, workflow_definition):
        """Test comparing a version to itself."""
        await version_manager.commit(workflow_definition, "First")

        comparison = await version_manager.compare(
            workflow_definition.workflow_id, "v1.0.0", "v1.0.0"
        )

        assert comparison["from_index"] == comparison["to_index"]
        assert comparison["diff"] == "compared-by-index"

    @pytest.mark.asyncio
    async def test_compare_non_existent_from_version(self, version_manager, workflow_definition):
        """Test comparing with non-existent from version."""
        await version_manager.commit(workflow_definition, "First")

        comparison = await version_manager.compare(
            workflow_definition.workflow_id, "v99.0.0", "v1.0.0"
        )

        assert comparison["from_index"] == -1

    @pytest.mark.asyncio
    async def test_compare_non_existent_to_version(self, version_manager, workflow_definition):
        """Test comparing with non-existent to version."""
        await version_manager.commit(workflow_definition, "First")

        comparison = await version_manager.compare(
            workflow_definition.workflow_id, "v1.0.0", "v99.0.0"
        )

        assert comparison["to_index"] == -1

    @pytest.mark.asyncio
    async def test_compare_non_existent_workflow(self, version_manager):
        """Test comparing versions for non-existent workflow."""
        comparison = await version_manager.compare("non-existent", "v1.0.0", "v2.0.0")

        assert comparison["workflow_id"] == "non-existent"
        assert comparison["version_count"] == 0
        assert comparison["from_index"] == -1
        assert comparison["to_index"] == -1

    @pytest.mark.asyncio
    async def test_rollback_success(self, version_manager, workflow_definition):
        """Test successful rollback to a version."""
        await version_manager.commit(workflow_definition, "First")
        await version_manager.commit(workflow_definition, "Second")

        result = await version_manager.rollback(workflow_definition.workflow_id, "v1.0.0")

        assert result is True

    @pytest.mark.asyncio
    async def test_rollback_non_existent_version(self, version_manager, workflow_definition):
        """Test rollback to non-existent version."""
        await version_manager.commit(workflow_definition, "First")

        result = await version_manager.rollback(workflow_definition.workflow_id, "v99.0.0")

        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_non_existent_workflow(self, version_manager):
        """Test rollback for non-existent workflow."""
        result = await version_manager.rollback("non-existent", "v1.0.0")

        assert result is False

    @pytest.mark.asyncio
    async def test_rollback_to_latest_version(self, version_manager, workflow_definition):
        """Test rollback to the latest version."""
        await version_manager.commit(workflow_definition, "First")
        await version_manager.commit(workflow_definition, "Second")

        versions = await version_manager.list_versions(workflow_definition.workflow_id)
        latest_version = versions[-1].version

        result = await version_manager.rollback(workflow_definition.workflow_id, latest_version)

        assert result is True

    @pytest.mark.asyncio
    async def test_commit_preserves_definition_fields(self, version_manager):
        """Test that commit preserves all definition fields."""
        from extensions.addons.operations.workflow_service.schemas import WorkflowNode

        definition = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test Workflow",
            description="Test Description",
            nodes=[
                WorkflowNode(
                    node_id="node1",
                    name="Node 1",
                    command="echo test",
                    dependencies=[],
                    retries=3,
                    timeout_seconds=60,
                )
            ],
            schedule="0 * * * *",
            metadata={"key": "value", "number": 42},
        )

        version = await version_manager.commit(definition, "Test commit")

        assert version is not None
        # The commit hash should be based on all these fields
        assert len(version.commit_hash) == 16

    @pytest.mark.asyncio
    async def test_commit_with_datetime_fields(self, version_manager, workflow_definition):
        """Test commit with datetime fields in definition."""
        from datetime import datetime

        # Add a datetime to metadata
        workflow_definition.metadata["created_at"] = datetime.utcnow().isoformat()

        version = await version_manager.commit(workflow_definition, "With datetime")

        assert version is not None
        assert len(version.commit_hash) == 16

    @pytest.mark.asyncio
    async def test_commit_with_special_characters_in_message(
        self, version_manager, workflow_definition
    ):
        """Test commit with special characters in message."""
        special_message = "Commit with @#$%^&*() special chars! 测试中文"
        version = await version_manager.commit(workflow_definition, special_message)

        assert version.message == special_message

    @pytest.mark.asyncio
    async def test_commit_with_very_long_message(self, version_manager, workflow_definition):
        """Test commit with very long message."""
        long_message = "a" * 1000
        version = await version_manager.commit(workflow_definition, long_message)

        assert version.message == long_message

    @pytest.mark.asyncio
    async def test_version_manager_isolation(self):
        """Test that different version manager instances are isolated."""
        manager1 = WorkflowVersionManager()
        manager2 = WorkflowVersionManager()

        definition = WorkflowDefinition(workflow_id="test", name="Test")
        await manager1.commit(definition, "Commit 1")

        assert "test" in manager1._versions
        assert "test" not in manager2._versions

    @pytest.mark.asyncio
    async def test_commit_creates_version_object(self, version_manager, workflow_definition):
        """Test that commit creates a proper WorkflowVersion object."""
        version = await version_manager.commit(workflow_definition, "Test")

        assert hasattr(version, "version")
        assert hasattr(version, "workflow_id")
        assert hasattr(version, "commit_hash")
        assert hasattr(version, "message")
        assert hasattr(version, "created_at")

    @pytest.mark.asyncio
    async def test_commit_version_format(self, version_manager, workflow_definition):
        """Test that version numbers follow expected format."""
        version = await version_manager.commit(workflow_definition, "Test")

        assert version.version.startswith("v")
        assert version.version.endswith(".0.0")

    @pytest.mark.asyncio
    async def test_commit_hash_length(self, version_manager, workflow_definition):
        """Test that commit hash has expected length."""
        version = await version_manager.commit(workflow_definition, "Test")

        assert len(version.commit_hash) == 16  # SHA256 truncated to 16 chars

    @pytest.mark.asyncio
    async def test_commit_hash_is_hexadecimal(self, version_manager, workflow_definition):
        """Test that commit hash is hexadecimal."""
        version = await version_manager.commit(workflow_definition, "Test")

        try:
            int(version.commit_hash, 16)
        except ValueError:
            pytest.fail("Commit hash is not hexadecimal")

    @pytest.mark.asyncio
    async def test_list_versions_returns_workflow_version_objects(
        self, version_manager, workflow_definition
    ):
        """Test that list_versions returns proper WorkflowVersion objects."""
        await version_manager.commit(workflow_definition, "Test")

        versions = await version_manager.list_versions(workflow_definition.workflow_id)

        assert len(versions) == 1
        assert hasattr(versions[0], "version")
        assert hasattr(versions[0], "workflow_id")
        assert hasattr(versions[0], "commit_hash")

    @pytest.mark.asyncio
    async def test_compare_returns_dict(self, version_manager, workflow_definition):
        """Test that compare returns a dictionary."""
        await version_manager.commit(workflow_definition, "First")

        comparison = await version_manager.compare(
            workflow_definition.workflow_id, "v1.0.0", "v1.0.0"
        )

        assert isinstance(comparison, dict)

    @pytest.mark.asyncio
    async def test_compare_dict_structure(self, version_manager, workflow_definition):
        """Test that compare dict has correct structure."""
        await version_manager.commit(workflow_definition, "First")

        comparison = await version_manager.compare(
            workflow_definition.workflow_id, "v1.0.0", "v1.0.0"
        )

        required_keys = [
            "workflow_id",
            "from_version",
            "to_version",
            "version_count",
            "from_index",
            "to_index",
            "diff",
        ]
        for key in required_keys:
            assert key in comparison

    @pytest.mark.asyncio
    async def test_multiple_workflow_versioning(self, version_manager):
        """Test versioning multiple workflows independently."""
        def1 = WorkflowDefinition(workflow_id="workflow-1", name="Workflow 1")
        def2 = WorkflowDefinition(workflow_id="workflow-2", name="Workflow 2")

        await version_manager.commit(def1, "W1 Commit 1")
        await version_manager.commit(def2, "W2 Commit 1")
        await version_manager.commit(def1, "W1 Commit 2")

        w1_versions = await version_manager.list_versions("workflow-1")
        w2_versions = await version_manager.list_versions("workflow-2")

        assert len(w1_versions) == 2
        assert len(w2_versions) == 1
        assert w1_versions[0].version == "v1.0.0"
        assert w1_versions[1].version == "v2.0.0"
        assert w2_versions[0].version == "v1.0.0"
