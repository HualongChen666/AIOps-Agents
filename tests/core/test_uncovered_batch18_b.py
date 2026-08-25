# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.documentation_manager,
core.cicd_pipeline_manager, core.base.analyzer, core.base.executor and
 core.causal.graph.
"""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.base.analyzer as analyzer_module
import core.base.executor as executor_module
import core.causal.graph as causal_graph_module
import core.cicd_pipeline_manager as cicd_module
import core.documentation_manager as doc_module

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.documentation_manager
# -----------------------------------------------------------------------------


def test_documentation_manager_full_lifecycle(tmp_path, monkeypatch):
    """Exercise document creation, generation, update, listing and summary."""
    manager = doc_module.DocumentationManager({"default_author": "AIOps"})

    # Create documents
    assert manager.create_document("doc-1", "First Doc", doc_module.DocType.USER_MANUAL, "body")
    assert not manager.create_document("doc-1", "Duplicate", doc_module.DocType.USER_MANUAL, "body")
    manager.create_document(
        "doc-2",
        "Second Doc",
        doc_module.DocType.API_DOCUMENTATION,
        "api body",
        author="other",
        version="2.0",
    )

    # Get / list
    doc = manager.get_document("doc-1")
    assert doc is not None
    assert doc.title == "First Doc"
    assert manager.get_document("missing") is None

    all_docs = manager.list_documents()
    assert len(all_docs) == 2
    filtered = manager.list_documents(
        doc_type=doc_module.DocType.USER_MANUAL,
        status=doc_module.DocStatus.DRAFT,
    )
    assert len(filtered) == 1
    assert filtered[0]["doc_id"] == "doc-1"

    # Update
    assert manager.update_document("doc-1", content="new body")
    assert manager.update_document("doc-2", status=doc_module.DocStatus.PUBLISHED)
    assert manager.published_documents == 1
    assert not manager.update_document("missing")

    # Generate from template (success)
    out_file = tmp_path / "manual.md"
    content_vars = {
        "quick_start_content": "qs",
        "features_content": "ft",
        "configuration_content": "cfg",
        "usage_content": "use",
        "troubleshooting_content": "trbl",
        "best_practices_content": "bp",
    }
    assert manager.generate_document_from_template(
        "user_manual", "My Manual", content_vars, str(out_file)
    )
    assert out_file.exists()

    # Generate from missing template
    assert not manager.generate_document_from_template(
        "no-such", "Title", {}, str(tmp_path / "x.md")
    )

    # Generate with formatting error (missing vars)
    assert not manager.generate_document_from_template(
        "api_documentation", "API", {}, str(tmp_path / "api.md")
    )

    # Templates / summary
    templates = manager.get_available_templates()
    assert any(t["template_id"] == "user_manual" for t in templates)
    summary = manager.get_doc_summary()
    assert summary["total_documents"] == 2
    assert summary["published_documents"] == 1
    assert summary["total_templates"] == 5
    assert "user_manual" in summary["documents_by_type"]


def test_documentation_manager_global_singleton():
    """Global factory should return a consistent singleton instance."""
    a = doc_module.get_documentation_manager()
    b = doc_module.get_documentation_manager()
    assert a is b
    assert isinstance(a, doc_module.DocumentationManager)


# -----------------------------------------------------------------------------
# core.cicd_pipeline_manager
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cicd_success_and_status(tmp_path, monkeypatch):
    """Run a pipeline end-to-end and verify status/statistics."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    manager = cicd_module.get_cicd_pipeline_manager(
        {
            "artifacts_dir": str(tmp_path / "artifacts"),
            "logs_dir": str(tmp_path / "logs"),
        }
    )

    build_stage = cicd_module.PipelineStageConfig(
        stage_name="build",
        stage_type=cicd_module.PipelineStage.BUILD,
        commands=["make build"],
    )
    test_stage = cicd_module.PipelineStageConfig(
        stage_name="unit-tests",
        stage_type=cicd_module.PipelineStage.TEST,
        commands=["pytest"],
    )
    pipeline = cicd_module.PipelineConfig(
        pipeline_id="pipe-1",
        pipeline_name="Main Pipeline",
        stages=[build_stage, test_stage],
        trigger_type=cicd_module.TriggerType.PUSH,
    )
    manager.register_pipeline(pipeline)

    exec_id = await manager.trigger_pipeline("pipe-1")

    # Wait for the background task created by trigger_pipeline
    current_task = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
    await asyncio.gather(*tasks, return_exceptions=True)

    status = manager.get_execution_status(exec_id)
    assert status is not None
    assert status["status"] == cicd_module.PipelineStatus.SUCCESS.value
    assert status["artifacts"]

    assert manager.get_execution_status("missing") is None

    listed = manager.list_executions(pipeline_id="pipe-1")
    assert len(listed) == 1
    assert manager.list_executions(status=cicd_module.PipelineStatus.FAILED) == []

    stats = manager.get_statistics()
    assert stats["total_executions"] == 1
    assert stats["successful_executions"] == 1
    assert stats["failed_executions"] == 0
    assert stats["success_rate"] == 1.0

    config = manager.get_pipeline_config("pipe-1")
    assert config is not None
    assert config["pipeline_id"] == "pipe-1"
    assert manager.get_pipeline_config("missing") is None


@pytest.mark.asyncio
async def test_cicd_pipeline_failure_and_continue(tmp_path, monkeypatch):
    """Verify a failed stage fails the pipeline unless continue_on_failure."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    manager = cicd_module.get_cicd_pipeline_manager(
        {
            "artifacts_dir": str(tmp_path / "artifacts"),
            "logs_dir": str(tmp_path / "logs"),
        }
    )

    async def fake_failing_stage(execution_id, stage_config):
        return {
            "success": False,
            "stage_name": stage_config.stage_name,
            "duration": 0.0,
            "error": "simulated",
        }

    pipeline = cicd_module.PipelineConfig(
        pipeline_id="fail-pipe",
        pipeline_name="Fail Pipe",
        stages=[
            cicd_module.PipelineStageConfig(
                stage_name="bad",
                stage_type=cicd_module.PipelineStage.TEST,
                continue_on_failure=False,
            )
        ],
    )
    manager.register_pipeline(pipeline)
    monkeypatch.setattr(manager, "_execute_stage", fake_failing_stage)

    exec_id = await manager.trigger_pipeline("fail-pipe")
    current_task = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
    await asyncio.gather(*tasks, return_exceptions=True)

    status = manager.get_execution_status(exec_id)
    assert status["status"] == cicd_module.PipelineStatus.FAILED.value
    assert "Stage bad failed" in status["error_message"]
    assert status["results"]["stage_0"]["error"] == "simulated"

    # Continue on failure
    pipeline2 = cicd_module.PipelineConfig(
        pipeline_id="continue-pipe",
        pipeline_name="Continue Pipe",
        stages=[
            cicd_module.PipelineStageConfig(
                stage_name="bad",
                stage_type=cicd_module.PipelineStage.TEST,
                continue_on_failure=True,
            )
        ],
    )
    manager.register_pipeline(pipeline2)
    exec_id2 = await manager.trigger_pipeline("continue-pipe")
    tasks = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
    await asyncio.gather(*tasks, return_exceptions=True)

    status2 = manager.get_execution_status(exec_id2)
    assert status2["status"] == cicd_module.PipelineStatus.SUCCESS.value


@pytest.mark.asyncio
async def test_cicd_stage_retry_and_artifact(tmp_path, monkeypatch):
    """Verify _execute_stage retries on transient failures and artifact collection."""
    call_count = 0

    async def fake_sleep(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            raise RuntimeError("transient")

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    manager = cicd_module.get_cicd_pipeline_manager(
        {
            "artifacts_dir": str(tmp_path / "artifacts"),
            "logs_dir": str(tmp_path / "logs"),
        }
    )

    exec_id = "exec_retry_1"
    execution = cicd_module.PipelineExecution(
        execution_id=exec_id,
        pipeline_id="p",
        status=cicd_module.PipelineStatus.RUNNING,
    )
    manager.executions[exec_id] = execution

    # Stage with 2 retries should fail after exhausting them
    stage = cicd_module.PipelineStageConfig(
        stage_name="flaky",
        stage_type=cicd_module.PipelineStage.TEST,
        retry_count=2,
    )
    result = await manager._execute_stage(
        exec_id, stage
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert call_count == 3
    assert execution.metadata.get("retry_count") == 2

    # Collect build artifacts directly
    build_exec = cicd_module.PipelineExecution(
        execution_id="exec_build_1",
        pipeline_id="p2",
        status=cicd_module.PipelineStatus.RUNNING,
    )
    manager.executions[build_exec.execution_id] = build_exec
    await manager._collect_build_artifacts(build_exec.execution_id)
    assert build_exec.artifacts
    assert Path(build_exec.artifacts[0]).exists()


@pytest.mark.asyncio
async def test_cicd_cancel_and_trigger_validation(tmp_path, monkeypatch):
    """Exercise cancel_execution and missing-pipeline validation."""
    manager = cicd_module.get_cicd_pipeline_manager(
        {
            "artifacts_dir": str(tmp_path / "artifacts"),
            "logs_dir": str(tmp_path / "logs"),
        }
    )

    # Missing pipeline
    with pytest.raises(ValueError, match="Pipeline not found"):
        await manager.trigger_pipeline("missing")

    # Manual execution record for cancel
    exec_id = "exec_cancel_1"
    manager.executions[exec_id] = cicd_module.PipelineExecution(
        execution_id=exec_id,
        pipeline_id="p",
        status=cicd_module.PipelineStatus.RUNNING,
    )
    assert await manager.cancel_execution(exec_id)
    assert manager.executions[exec_id].status == cicd_module.PipelineStatus.CANCELLED
    assert not await manager.cancel_execution("missing")
    # Already not running
    assert not await manager.cancel_execution(exec_id)


@pytest.mark.asyncio
async def test_cicd_pipeline_cancelled_during_run(tmp_path, monkeypatch):
    """Cover the CANCELLED check inside _execute_pipeline."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    manager = cicd_module.get_cicd_pipeline_manager(
        {
            "artifacts_dir": str(tmp_path / "artifacts"),
            "logs_dir": str(tmp_path / "logs"),
        }
    )

    call_count = 0

    async def fake_stage(execution_id, stage_config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            manager.executions[execution_id].status = cicd_module.PipelineStatus.CANCELLED
        return {
            "success": True,
            "stage_name": stage_config.stage_name,
            "duration": 0.0,
            "output": "ok",
        }

    pipeline = cicd_module.PipelineConfig(
        pipeline_id="cancel-pipe",
        pipeline_name="Cancel Pipe",
        stages=[
            cicd_module.PipelineStageConfig(
                stage_name="s1",
                stage_type=cicd_module.PipelineStage.TEST,
            ),
            cicd_module.PipelineStageConfig(
                stage_name="s2",
                stage_type=cicd_module.PipelineStage.TEST,
            ),
        ],
    )
    manager.register_pipeline(pipeline)
    monkeypatch.setattr(manager, "_execute_stage", fake_stage)

    exec_id = await manager.trigger_pipeline("cancel-pipe")
    current_task = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
    await asyncio.gather(*tasks, return_exceptions=True)

    execution = manager.executions[exec_id]
    # _execute_pipeline broke early after the first stage saw CANCELLED
    assert execution.current_stage == 0
    assert "stage_0" in execution.results
    assert "stage_1" not in execution.results


# -----------------------------------------------------------------------------
# core.base.analyzer
# -----------------------------------------------------------------------------


def test_base_analyzer_concrete_usage():
    """Cover the non-abstract methods of BaseAnalyzer."""

    class FakeAnalyzer(analyzer_module.BaseAnalyzer):
        def initialize(self):
            self._is_initialized = True
            return True

        async def analyze(self, data):
            return {"ok": True}

        def close(self):
            self._is_initialized = False

    with FakeAnalyzer("fake", {"threshold": 0.5}) as a:
        assert a._is_initialized
        assert a.validate_config(["threshold"])
        assert not a.validate_config(["missing"])
        status = a.get_status()
        assert status["name"] == "fake"
        assert status["initialized"]
        assert not a._is_fitted

    assert not a._is_initialized


# -----------------------------------------------------------------------------
# core.base.executor
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_base_executor_concrete_usage():
    """Cover the non-abstract methods of BaseExecutor."""

    class FakeExecutor(executor_module.BaseExecutor):
        def initialize(self):
            self._is_initialized = True
            return True

        async def execute(self, action, params):
            return {"action": action, "valid": self.validate_config(["path"])}

        def close(self):
            self._is_initialized = False

    with FakeExecutor("fake-exec", {"path": "/tmp"}) as e:
        assert e._is_initialized
        assert e.validate_config(["path"])
        assert not e.validate_config(["missing"])
        status = e.get_status()
        assert status["name"] == "fake-exec"
        assert status["initialized"]
        assert not e._is_running

        result = await e.execute("run", {})  # noqa: F841  # Variable for test verification
        assert result["action"] == "run"
        assert result["valid"]

    assert not e._is_initialized


# -----------------------------------------------------------------------------
# core.causal.graph
# -----------------------------------------------------------------------------


def test_causal_graph_relationships_and_serialization():
    """Cover CausalGraph and CausalEdge operations plus serialization."""
    graph = causal_graph_module.CausalGraph("service-graph")

    graph.add_node("db")
    graph.add_node("api")
    graph.add_node("web")

    e1 = causal_graph_module.CausalEdge(
        "db", "api", causal_graph_module.CausalStrength.STRONG, 0.9, lag=1
    )
    e2 = causal_graph_module.CausalEdge(
        "api", "web", causal_graph_module.CausalStrength.MODERATE, 0.8
    )
    graph.add_edge(e1)
    graph.add_edge(e2)

    assert graph.get_children("db") == ["api"]
    assert graph.get_parents("web") == ["api"]

    assert graph.get_ancestors("web") == {"db", "api"}
    assert graph.get_descendants("db") == {"api", "web"}

    paths = graph.find_causal_paths("db", "web")
    assert ["db", "api", "web"] in paths

    assert graph.get_causal_strength("db", "api") == causal_graph_module.CausalStrength.STRONG
    assert graph.get_causal_strength("web", "db") is None

    d = graph.to_dict()
    assert d["name"] == "service-graph"
    assert set(d["nodes"]) == {"db", "api", "web"}
    assert len(d["edges"]) == 2

    js = graph.to_json()
    parsed = json.loads(js)
    assert parsed["name"] == graph.name
    assert "edges" in parsed
    assert e1.to_dict()["strength"] == "strong"
