# -*- coding: utf-8 -*-
"""
Test suite for AI Advanced Router
=================================

Comprehensive tests for AI analysis features including:
- Model Fine-tuning
- Runbook Generation
- Intelligent Analysis
- LangGraph (DSL, Executor, Visualizer, Workflow)
- Deep Learning
- Advanced AI Features
- Model Optimization
- AI Feedback
- Knowledge Retrieval
- Document Index
- Semantic Search
- Pattern Matching
- Cross-layer Tracking
- Topology Analysis
- Root Cause Analysis
- Knowledge Graph
- Fusion
- Reranker
- Vectorizer
- Retriever
- RAG Knowledge Base
- Load Balancer
- Capability Evaluator
- Cost Optimizer
- LLM Router
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api.ai_advanced_router import (
    AnalyzeRequest,
    CostSuggestionCreate,
    DeepLearningModelCreate,
    DocumentIndexCreate,
    DSLDefinitionCreate,
    EmbedRequest,
    EvaluateRequest,
    ExecutionCreate,
    FeedbackCreate,
    FineTuningJobCreate,
    FusionRequest,
    GraphNodeCreate,
    JobStatus,
    KnowledgeBaseCreate,
    LoadBalancerConfigCreate,
    ModelStatus,
    OptimizationRequest,
    PatternCreate,
    RerankRequest,
    RetrievalRequest,
    RetrieveRequest,
    RootCauseAnalysisRequest,
    RoutingRuleCreate,
    RunbookGenerateRequest,
    SearchRequest,
    TopologyAnalysisRequest,
    WorkflowCreate,
    router,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a test client for the AI router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    # Disable CORS for testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return TestClient(app)


@pytest.fixture
def sample_fine_tuning_job():
    """Sample fine-tuning job"""
    return FineTuningJobCreate(
        base_model="gpt-3.5-turbo",
        model_name="custom-model",
        dataset_id="dataset-123",
        learning_rate=0.0001,
        epochs=3,
    )


@pytest.fixture
def sample_runbook_request():
    """Sample runbook generation request"""
    return RunbookGenerateRequest(incident_type="CPU High Usage", context="Production environment")


@pytest.fixture
def sample_analyze_request():
    """Sample intelligent analysis request"""
    return AnalyzeRequest(
        name="Performance Analysis", type="performance", data_sources=["prometheus", "logs"]
    )


@pytest.fixture
def sample_dsl_definition():
    """Sample DSL definition"""
    return DSLDefinitionCreate(
        name="Test Workflow",
        version="1.0.0",
        description="Test workflow definition",
        content="workflow: test",
    )


@pytest.fixture
def sample_execution():
    """Sample execution request"""
    return ExecutionCreate(workflow_id="workflow-123", input={"param1": "value1"})


@pytest.fixture
def sample_workflow():
    """Sample workflow request"""
    return WorkflowCreate(name="Test Workflow", description="Test workflow")


@pytest.fixture
def sample_deep_learning_model():
    """Sample deep learning model"""
    return DeepLearningModelCreate(
        name="Test Model", architecture="Transformer", framework="PyTorch"
    )


@pytest.fixture
def sample_optimization_request():
    """Sample optimization request"""
    return OptimizationRequest(model_id="model-123", optimization_type="quantization")


@pytest.fixture
def sample_feedback():
    """Sample feedback"""
    return FeedbackCreate(type="positive", content="Great analysis", rating=5, category="accuracy")


@pytest.fixture
def sample_retrieval_request():
    """Sample retrieval request"""
    return RetrievalRequest(config_id="config-123", query="How to fix CPU high usage")


@pytest.fixture
def sample_document_index():
    """Sample document index"""
    return DocumentIndexCreate(name="Test Index", type="text")


@pytest.fixture
def sample_search_request():
    """Sample search request"""
    return SearchRequest(config_id="config-123", query="CPU optimization")


@pytest.fixture
def sample_pattern():
    """Sample pattern"""
    return PatternCreate(
        name="Test Pattern", type="anomaly", description="Test pattern", severity="high"
    )


@pytest.fixture
def sample_topology_request():
    """Sample topology analysis request"""
    return TopologyAnalysisRequest()


@pytest.fixture
def sample_root_cause_request():
    """Sample root cause analysis request"""
    return RootCauseAnalysisRequest(incident_id="incident-123")


@pytest.fixture
def sample_graph_node():
    """Sample graph node"""
    return GraphNodeCreate(label="Service A", type="service", properties={"port": 8080})


@pytest.fixture
def sample_fusion_request():
    """Sample fusion request"""
    return FusionRequest(config_id="config-123", query="System performance")


@pytest.fixture
def sample_rerank_request():
    """Sample rerank request"""
    return RerankRequest(
        config_id="config-123", query="CPU optimization", documents=["Doc 1", "Doc 2", "Doc 3"]
    )


@pytest.fixture
def sample_embed_request():
    """Sample embed request"""
    return EmbedRequest(config_id="config-123", text="This is a test text")


@pytest.fixture
def sample_retrieve_request():
    """Sample retrieve request"""
    return RetrieveRequest(config_id="config-123", query="Search query")


@pytest.fixture
def sample_knowledge_base():
    """Sample knowledge base"""
    return KnowledgeBaseCreate(
        name="Test KB", description="Test knowledge base", embedding_model="text-embedding-ada-002"
    )


@pytest.fixture
def sample_load_balancer_config():
    """Sample load balancer config"""
    return LoadBalancerConfigCreate(name="Test LB", strategy="round_robin")


@pytest.fixture
def sample_evaluate_request():
    """Sample evaluate request"""
    return EvaluateRequest(model_id="model-123")


@pytest.fixture
def sample_cost_suggestion():
    """Sample cost suggestion"""
    return CostSuggestionCreate(
        type="model_selection", description="Use smaller model", potential_savings=100.0
    )


@pytest.fixture
def sample_routing_rule():
    """Sample routing rule"""
    return RoutingRuleCreate(
        name="Test Rule", condition="query contains 'code'", target_model="gpt-4", priority=1
    )


# ============================================================================
# Model Fine-tuning Tests
# ============================================================================


class TestModelFineTuning:
    """Test suite for model fine-tuning endpoints"""

    def test_get_fine_tuning_jobs_empty(self, client):
        """Test getting fine-tuning jobs when empty"""
        response = client.get("/api/ai/model-fine-tuning/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_create_fine_tuning_job(self, client, sample_fine_tuning_job):
        """Test creating a fine-tuning job"""
        response = client.post("/api/ai/model-fine-tuning/jobs", json=sample_fine_tuning_job.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["base_model"] == "gpt-3.5-turbo"
        assert data["status"] == JobStatus.PENDING
        assert data["progress"] == 0.0

    def test_create_fine_tuning_job_invalid_learning_rate(self, client):
        """Test creating fine-tuning job with invalid learning rate"""
        invalid_job = {
            "base_model": "gpt-3.5-turbo",
            "model_name": "custom-model",
            "dataset_id": "dataset-123",
            "learning_rate": 1.0,  # Too high
            "epochs": 3,
        }
        response = client.post("/api/ai/model-fine-tuning/jobs", json=invalid_job)
        assert response.status_code == 422

    def test_create_fine_tuning_job_invalid_epochs(self, client):
        """Test creating fine-tuning job with invalid epochs"""
        invalid_job = {
            "base_model": "gpt-3.5-turbo",
            "model_name": "custom-model",
            "dataset_id": "dataset-123",
            "learning_rate": 0.0001,
            "epochs": 200,  # Too high
        }
        response = client.post("/api/ai/model-fine-tuning/jobs", json=invalid_job)
        assert response.status_code == 422

    def test_get_fine_tuned_models_empty(self, client):
        """Test getting fine-tuned models when empty"""
        response = client.get("/api/ai/model-fine-tuning/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)


# ============================================================================
# Runbook Generator Tests
# ============================================================================


class TestRunbookGenerator:
    """Test suite for runbook generator endpoints"""

    @patch("api.ai_advanced_router.analyze")
    async def test_generate_runbook_with_ai_engine(
        self, mock_analyze, client, sample_runbook_request
    ):
        """Test generating runbook with AI engine"""
        mock_analyze.return_value = "Generated runbook content"
        response = client.post(
            "/api/ai/runbook-generator/generate", json=sample_runbook_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "CPU High Usage Runbook"
        assert "steps" in data

    def test_generate_runbook_fallback(self, client, sample_runbook_request):
        """Test generating runbook with fallback (AI engine not available)"""
        response = client.post(
            "/api/ai/runbook-generator/generate", json=sample_runbook_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "steps" in data

    def test_generate_runbook_missing_incident_type(self, client):
        """Test generating runbook without incident type"""
        response = client.post("/api/ai/runbook-generator/generate", json={"context": "test"})
        assert response.status_code == 422


# ============================================================================
# Intelligent Analysis Tests
# ============================================================================


class TestIntelligentAnalysis:
    """Test suite for intelligent analysis endpoints"""

    @patch("api.ai_advanced_router.analyze")
    async def test_run_intelligent_analysis_with_ai(
        self, mock_analyze, client, sample_analyze_request
    ):
        """Test running intelligent analysis with AI engine"""
        mock_analyze.return_value = "Analysis result"
        response = client.post(
            "/api/ai/intelligent-analysis/analyze", json=sample_analyze_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Performance Analysis"
        assert data["status"] == JobStatus.COMPLETED

    @patch("api.ai_advanced_router.analyze")
    async def test_run_intelligent_analysis_ai_failure(
        self, mock_analyze, client, sample_analyze_request
    ):
        """Test intelligent analysis when AI engine fails"""
        mock_analyze.side_effect = Exception("AI engine error")
        response = client.post(
            "/api/ai/intelligent-analysis/analyze", json=sample_analyze_request.dict()
        )
        assert response.status_code == 500

    def test_run_intelligent_analysis_missing_name(self, client):
        """Test running analysis without name"""
        response = client.post(
            "/api/ai/intelligent-analysis/analyze", json={"type": "performance", "data_sources": []}
        )
        assert response.status_code == 422


# ============================================================================
# LangGraph DSL Tests
# ============================================================================


class TestLangGraphDSL:
    """Test suite for LangGraph DSL endpoints"""

    def test_get_dsl_definitions_empty(self, client):
        """Test getting DSL definitions when empty"""
        response = client.get("/api/ai/langgraph-dsl/definitions")
        assert response.status_code == 200
        data = response.json()
        assert "definitions" in data
        assert isinstance(data["definitions"], list)

    def test_create_dsl_definition(self, client, sample_dsl_definition):
        """Test creating a DSL definition"""
        response = client.post(
            "/api/ai/langgraph-dsl/definitions", json=sample_dsl_definition.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Workflow"
        assert data["status"] == "draft"

    def test_update_dsl_definition(self, client, sample_dsl_definition):
        """Test updating a DSL definition"""
        # First create a definition
        create_response = client.post(
            "/api/ai/langgraph-dsl/definitions", json=sample_dsl_definition.dict()
        )
        defn_id = create_response.json()["id"]

        # Update the definition
        update_data = {"name": "Updated Workflow", "status": "published"}
        response = client.patch(f"/api/ai/langgraph-dsl/definitions/{defn_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Workflow"

    def test_update_dsl_definition_not_found(self, client):
        """Test updating non-existent DSL definition"""
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/ai/langgraph-dsl/definitions/{fake_id}", json={"name": "Updated"}
        )
        assert response.status_code == 404


# ============================================================================
# LangGraph Executor Tests
# ============================================================================


class TestLangGraphExecutor:
    """Test suite for LangGraph executor endpoints"""

    @patch("api.ai_advanced_router.execute_workflow")
    async def test_create_execution_with_engine(self, mock_execute, client, sample_execution):
        """Test creating execution with actual engine"""
        mock_execute.return_value = {"result": "success"}
        response = client.post(
            "/api/ai/langgraph-executor/executions", json=sample_execution.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == JobStatus.COMPLETED

    def test_create_execution_fallback(self, client, sample_execution):
        """Test creating execution with fallback"""
        response = client.post(
            "/api/ai/langgraph-executor/executions", json=sample_execution.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == JobStatus.COMPLETED

    def test_get_executions_empty(self, client):
        """Test getting executions when empty"""
        response = client.get("/api/ai/langgraph-executor/executions")
        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
        assert isinstance(data["executions"], list)


# ============================================================================
# LangGraph Workflow Tests
# ============================================================================


class TestLangGraphWorkflow:
    """Test suite for LangGraph workflow endpoints"""

    @patch("api.ai_advanced_router.create_workflow")
    async def test_create_workflow_with_engine(self, mock_create, client, sample_workflow):
        """Test creating workflow with actual engine"""
        mock_create.return_value = {"node_count": 5}
        response = client.post("/api/ai/langgraph-workflow/workflows", json=sample_workflow.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Workflow"

    def test_create_workflow_fallback(self, client, sample_workflow):
        """Test creating workflow with fallback"""
        response = client.post("/api/ai/langgraph-workflow/workflows", json=sample_workflow.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "draft"

    def test_get_workflows_empty(self, client):
        """Test getting workflows when empty"""
        response = client.get("/api/ai/langgraph-workflow/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)

    def test_update_workflow(self, client, sample_workflow):
        """Test updating a workflow"""
        # First create a workflow
        create_response = client.post(
            "/api/ai/langgraph-workflow/workflows", json=sample_workflow.dict()
        )
        workflow_id = create_response.json()["id"]

        # Update the workflow
        update_data = {"name": "Updated Workflow", "status": "active"}
        response = client.patch(
            f"/api/ai/langgraph-workflow/workflows/{workflow_id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Workflow"

    def test_update_workflow_not_found(self, client):
        """Test updating non-existent workflow"""
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/ai/langgraph-workflow/workflows/{fake_id}", json={"name": "Updated"}
        )
        assert response.status_code == 404


# ============================================================================
# LangGraph Visualizer Tests
# ============================================================================


class TestLangGraphVisualizer:
    """Test suite for LangGraph visualizer endpoints"""

    @patch("api.ai_advanced_router.generate_graph_viz")
    async def test_generate_visualization_with_engine(self, mock_generate, client):
        """Test generating visualization with actual engine"""
        mock_generate.return_value = {"nodes": [], "edges": []}
        response = client.post(
            "/api/ai/langgraph-visualizer/generate", json={"workflow_id": "workflow-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "visualization_id" in data
        assert "data" in data

    def test_generate_visualization_fallback(self, client):
        """Test generating visualization with fallback"""
        response = client.post(
            "/api/ai/langgraph-visualizer/generate", json={"workflow_id": "workflow-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "visualization_id" in data
        assert "data" in data

    def test_generate_visualization_missing_workflow_id(self, client):
        """Test generating visualization without workflow_id"""
        response = client.post("/api/ai/langgraph-visualizer/generate", json={})
        assert response.status_code == 400


# ============================================================================
# Deep Learning Tests
# ============================================================================


class TestDeepLearning:
    """Test suite for deep learning endpoints"""

    def test_get_deep_learning_models_empty(self, client):
        """Test getting deep learning models when empty"""
        response = client.get("/api/ai/deep-learning/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_create_deep_learning_model(self, client, sample_deep_learning_model):
        """Test creating a deep learning model"""
        response = client.post(
            "/api/ai/deep-learning/models", json=sample_deep_learning_model.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Model"
        assert data["architecture"] == "Transformer"
        assert data["status"] == ModelStatus.READY


# ============================================================================
# Advanced AI Features Tests
# ============================================================================


class TestAdvancedAIFeatures:
    """Test suite for advanced AI features endpoints"""

    def test_get_advanced_features(self, client):
        """Test getting advanced AI features"""
        response = client.get("/api/ai/advanced-ai/features")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert isinstance(data["features"], list)
        # Should have default features
        assert len(data["features"]) > 0

    def test_update_advanced_feature(self, client):
        """Test updating an advanced feature"""
        # First get features
        get_response = client.get("/api/ai/advanced-ai/features")
        features = get_response.json()["features"]
        if len(features) > 0:
            feature_id = features[0]["id"]
            update_data = {"enabled": False}
            response = client.patch(f"/api/ai/advanced-ai/features/{feature_id}", json=update_data)
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] == False

    def test_update_advanced_feature_not_found(self, client):
        """Test updating non-existent feature"""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/api/ai/advanced-ai/features/{fake_id}", json={"enabled": False})
        assert response.status_code == 404


# ============================================================================
# Model Optimization Tests
# ============================================================================


class TestModelOptimization:
    """Test suite for model optimization endpoints"""

    @patch("api.ai_advanced_router.optimize_model_cost")
    async def test_optimize_model_with_engine(
        self, mock_optimize, client, sample_optimization_request
    ):
        """Test optimizing model with actual engine"""
        mock_optimize.return_value = {"original_size": 1000000, "optimized_size": 500000}
        response = client.post(
            "/api/ai/model-optimization/optimize", json=sample_optimization_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "optimization_id" in data
        assert data["status"] == "completed"

    def test_optimize_model_fallback(self, client, sample_optimization_request):
        """Test optimizing model with fallback"""
        response = client.post(
            "/api/ai/model-optimization/optimize", json=sample_optimization_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "optimization_id" in data
        assert data["status"] == "completed"


# ============================================================================
# AI Feedback Tests
# ============================================================================


class TestAIFeedback:
    """Test suite for AI feedback endpoints"""

    def test_get_feedbacks_empty(self, client):
        """Test getting feedbacks when empty"""
        response = client.get("/api/ai/ai-feedback/feedbacks")
        assert response.status_code == 200
        data = response.json()
        assert "feedbacks" in data
        assert isinstance(data["feedbacks"], list)

    def test_create_feedback(self, client, sample_feedback):
        """Test creating feedback"""
        response = client.post("/api/ai/ai-feedback/feedbacks", json=sample_feedback.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["type"] == "positive"
        assert data["rating"] == 5

    def test_create_feedback_invalid_rating(self, client):
        """Test creating feedback with invalid rating"""
        invalid_feedback = {"type": "positive", "content": "Test", "rating": 10}  # Too high
        response = client.post("/api/ai/ai-feedback/feedbacks", json=invalid_feedback)
        assert response.status_code == 422

    def test_update_feedback(self, client, sample_feedback):
        """Test updating feedback"""
        # First create feedback
        create_response = client.post("/api/ai/ai-feedback/feedbacks", json=sample_feedback.dict())
        feedback_id = create_response.json()["id"]

        # Update the feedback
        update_data = {"status": "reviewed"}
        response = client.patch(f"/api/ai/ai-feedback/feedbacks/{feedback_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reviewed"

    def test_update_feedback_not_found(self, client):
        """Test updating non-existent feedback"""
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/ai/ai-feedback/feedbacks/{fake_id}", json={"status": "reviewed"}
        )
        assert response.status_code == 404


# ============================================================================
# Knowledge Retrieval Tests
# ============================================================================


class TestKnowledgeRetrieval:
    """Test suite for knowledge retrieval endpoints"""

    @patch("api.ai_advanced_router.search_similar")
    async def test_retrieve_knowledge_with_engine(
        self, mock_search, client, sample_retrieval_request
    ):
        """Test retrieving knowledge with actual engine"""
        mock_search.return_value = [
            {"content": "Result 1", "source": "kb", "score": 0.9, "metadata": {}}
        ]
        response = client.post(
            "/api/ai/knowledge-retrieval/retrieve", json=sample_retrieval_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_retrieve_knowledge_fallback(self, client, sample_retrieval_request):
        """Test retrieving knowledge with fallback"""
        response = client.post(
            "/api/ai/knowledge-retrieval/retrieve", json=sample_retrieval_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# ============================================================================
# Document Index Tests
# ============================================================================


class TestDocumentIndex:
    """Test suite for document index endpoints"""

    def test_get_document_indexes_empty(self, client):
        """Test getting document indexes when empty"""
        response = client.get("/api/ai/document-index/indexes")
        assert response.status_code == 200
        data = response.json()
        assert "indexes" in data
        assert isinstance(data["indexes"], list)

    def test_create_document_index(self, client, sample_document_index):
        """Test creating a document index"""
        response = client.post("/api/ai/document-index/indexes", json=sample_document_index.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Index"
        assert data["type"] == "text"


# ============================================================================
# Semantic Search Tests
# ============================================================================


class TestSemanticSearch:
    """Test suite for semantic search endpoints"""

    @patch("api.ai_advanced_router.search_similar")
    async def test_semantic_search_with_engine(self, mock_search, client, sample_search_request):
        """Test semantic search with actual engine"""
        mock_search.return_value = [
            {"content": "Result 1", "source": "index", "score": 0.9, "metadata": {}}
        ]
        response = client.post("/api/ai/semantic-search/search", json=sample_search_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_semantic_search_fallback(self, client, sample_search_request):
        """Test semantic search with fallback"""
        response = client.post("/api/ai/semantic-search/search", json=sample_search_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# ============================================================================
# Pattern Matching Tests
# ============================================================================


class TestPatternMatching:
    """Test suite for pattern matching endpoints"""

    def test_get_patterns_empty(self, client):
        """Test getting patterns when empty"""
        response = client.get("/api/ai/pattern-matching/patterns")
        assert response.status_code == 200
        data = response.json()
        assert "patterns" in data
        assert isinstance(data["patterns"], list)

    def test_create_pattern(self, client, sample_pattern):
        """Test creating a pattern"""
        response = client.post("/api/ai/pattern-matching/patterns", json=sample_pattern.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Pattern"
        assert data["type"] == "anomaly"


# ============================================================================
# Cross-layer Tracking Tests
# ============================================================================


class TestCrossLayerTracking:
    """Test suite for cross-layer tracking endpoints"""

    def test_get_cross_layer_traces(self, client):
        """Test getting cross-layer traces"""
        response = client.get("/api/ai/cross-layer-tracking/traces")
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data
        assert isinstance(data["traces"], list)


# ============================================================================
# Topology Analysis Tests
# ============================================================================


class TestTopologyAnalysis:
    """Test suite for topology analysis endpoints"""

    @patch("api.ai_advanced_router.analyze_topology")
    async def test_analyze_topology_with_engine(
        self, mock_analyze, client, sample_topology_request
    ):
        """Test analyzing topology with actual engine"""
        mock_analyze.return_value = {
            "critical_path": ["service-a", "service-b"],
            "bottlenecks": ["database"],
            "risk_score": 0.7,
            "recommendations": ["Scale database"],
        }
        response = client.post(
            "/api/ai/topology-analysis/analyze", json=sample_topology_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "critical_path" in data
        assert "risk_score" in data

    def test_analyze_topology_fallback(self, client, sample_topology_request):
        """Test analyzing topology with fallback"""
        response = client.post(
            "/api/ai/topology-analysis/analyze", json=sample_topology_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "critical_path" in data


# ============================================================================
# Root Cause Analysis Tests
# ============================================================================


class TestRootCauseAnalysis:
    """Test suite for root cause analysis endpoints"""

    @patch("api.ai_advanced_router.analyze")
    async def test_analyze_root_cause_with_ai(
        self, mock_analyze, client, sample_root_cause_request
    ):
        """Test analyzing root cause with AI engine"""
        mock_analyze.return_value = "Root cause analysis result"
        response = client.post(
            "/api/ai/root-cause-analysis/analyze", json=sample_root_cause_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["incident_id"] == "incident-123"
        assert "root_cause" in data
        assert "confidence" in data

    @patch("api.ai_advanced_router.analyze")
    async def test_analyze_root_cause_ai_failure(
        self, mock_analyze, client, sample_root_cause_request
    ):
        """Test root cause analysis when AI engine fails"""
        mock_analyze.side_effect = Exception("AI engine error")
        response = client.post(
            "/api/ai/root-cause-analysis/analyze", json=sample_root_cause_request.dict()
        )
        assert response.status_code == 500

    def test_analyze_root_cause_missing_incident_id(self, client):
        """Test root cause analysis without incident_id"""
        response = client.post("/api/ai/root-cause-analysis/analyze", json={})
        assert response.status_code == 422


# ============================================================================
# Knowledge Graph Tests
# ============================================================================


class TestKnowledgeGraph:
    """Test suite for knowledge graph endpoints"""

    def test_get_knowledge_graph_nodes_empty(self, client):
        """Test getting knowledge graph nodes when empty"""
        response = client.get("/api/ai/knowledge-graph/nodes")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert isinstance(data["nodes"], list)

    def test_create_graph_node(self, client, sample_graph_node):
        """Test creating a graph node"""
        response = client.post("/api/ai/knowledge-graph/nodes", json=sample_graph_node.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["label"] == "Service A"
        assert data["type"] == "service"


# ============================================================================
# Fusion Tests
# ============================================================================


class TestFusion:
    """Test suite for fusion endpoints"""

    @patch("api.ai_advanced_router.fuse_results")
    async def test_fuse_results_with_engine(self, mock_fuse, client, sample_fusion_request):
        """Test fusing results with actual engine"""
        mock_fuse.return_value = [
            {"content": "Fused result", "fused_score": 0.9, "source_scores": {}}
        ]
        response = client.post("/api/ai/fusion/fuse", json=sample_fusion_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_fuse_results_fallback(self, client, sample_fusion_request):
        """Test fusing results with fallback"""
        response = client.post("/api/ai/fusion/fuse", json=sample_fusion_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# ============================================================================
# Reranker Tests
# ============================================================================


class TestReranker:
    """Test suite for reranker endpoints"""

    @patch("api.ai_advanced_router.rerank")
    async def test_rerank_results_with_engine(self, mock_rerank, client, sample_rerank_request):
        """Test reranking results with actual engine"""
        mock_rerank.return_value = [
            {"new_rank": 0, "score": 0.9},
            {"new_rank": 1, "score": 0.8},
            {"new_rank": 2, "score": 0.7},
        ]
        response = client.post("/api/ai/reranker/rerank", json=sample_rerank_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_rerank_results_fallback(self, client, sample_rerank_request):
        """Test reranking results with fallback"""
        response = client.post("/api/ai/reranker/rerank", json=sample_rerank_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# ============================================================================
# Vectorizer Tests
# ============================================================================


class TestVectorizer:
    """Test suite for vectorizer endpoints"""

    @patch("api.ai_advanced_router._get_model")
    async def test_embed_text_with_engine(self, mock_get_model, client, sample_embed_request):
        """Test embedding text with actual engine"""
        mock_model = Mock()
        mock_model.encode.return_value = [0.1, 0.2, 0.3]
        mock_get_model.return_value = mock_model

        response = client.post("/api/ai/vectorizer/embed", json=sample_embed_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "dimensions" in data

    def test_embed_text_fallback(self, client, sample_embed_request):
        """Test embedding text with fallback"""
        response = client.post("/api/ai/vectorizer/embed", json=sample_embed_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "dimensions" in data


# ============================================================================
# Retriever Tests
# ============================================================================


class TestRetriever:
    """Test suite for retriever endpoints"""

    @patch("api.ai_advanced_router.retrieve")
    async def test_retrieve_documents_with_engine(
        self, mock_retrieve, client, sample_retrieve_request
    ):
        """Test retrieving documents with actual engine"""
        mock_retrieve.return_value = [
            {"id": "1", "content": "Document 1", "score": 0.9, "metadata": {}}
        ]
        response = client.post("/api/ai/retriever/retrieve", json=sample_retrieve_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_retrieve_documents_fallback(self, client, sample_retrieve_request):
        """Test retrieving documents with fallback"""
        response = client.post("/api/ai/retriever/retrieve", json=sample_retrieve_request.dict())
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# ============================================================================
# RAG Knowledge Base Tests
# ============================================================================


class TestRAGKnowledgeBase:
    """Test suite for RAG knowledge base endpoints"""

    def test_get_knowledge_bases_empty(self, client):
        """Test getting knowledge bases when empty"""
        response = client.get("/api/ai/rag-knowledge-base/bases")
        assert response.status_code == 200
        data = response.json()
        assert "bases" in data
        assert isinstance(data["bases"], list)

    @patch("api.ai_advanced_router.create_knowledge_base")
    async def test_create_knowledge_base_with_engine(
        self, mock_create, client, sample_knowledge_base
    ):
        """Test creating knowledge base with actual engine"""
        mock_create.return_value = "kb-123"
        response = client.post(
            "/api/ai/rag-knowledge-base/bases", json=sample_knowledge_base.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test KB"

    def test_create_knowledge_base_fallback(self, client, sample_knowledge_base):
        """Test creating knowledge base with fallback"""
        response = client.post(
            "/api/ai/rag-knowledge-base/bases", json=sample_knowledge_base.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test KB"

    def test_delete_knowledge_base(self, client, sample_knowledge_base):
        """Test deleting a knowledge base"""
        # First create a knowledge base
        create_response = client.post(
            "/api/ai/rag-knowledge-base/bases", json=sample_knowledge_base.dict()
        )
        kb_id = create_response.json()["id"]

        # Delete the knowledge base
        response = client.delete(f"/api/ai/rag-knowledge-base/bases/{kb_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_delete_knowledge_base_not_found(self, client):
        """Test deleting non-existent knowledge base"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/ai/rag-knowledge-base/bases/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Load Balancer Tests
# ============================================================================


class TestLoadBalancer:
    """Test suite for load balancer endpoints"""

    @patch("api.ai_advanced_router.get_configs")
    async def test_get_load_balancer_configs_with_engine(self, mock_get, client):
        """Test getting load balancer configs with actual engine"""
        mock_get.return_value = []
        response = client.get("/api/ai/load-balancer/configs")
        assert response.status_code == 200
        data = response.json()
        assert "configs" in data

    def test_get_load_balancer_configs_fallback(self, client):
        """Test getting load balancer configs with fallback"""
        response = client.get("/api/ai/load-balancer/configs")
        assert response.status_code == 200
        data = response.json()
        assert "configs" in data

    @patch("api.ai_advanced_router.create_config")
    async def test_create_load_balancer_config_with_engine(
        self, mock_create, client, sample_load_balancer_config
    ):
        """Test creating load balancer config with actual engine"""
        mock_create.return_value = {"id": "lb-123", "name": "Test LB", "strategy": "round_robin"}
        response = client.post(
            "/api/ai/load-balancer/configs", json=sample_load_balancer_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test LB"

    def test_create_load_balancer_config_fallback(self, client, sample_load_balancer_config):
        """Test creating load balancer config with fallback"""
        response = client.post(
            "/api/ai/load-balancer/configs", json=sample_load_balancer_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test LB"

    def test_update_load_balancer_config(self, client, sample_load_balancer_config):
        """Test updating load balancer config"""
        # First create a config
        create_response = client.post(
            "/ai/load-balancer/configs", json=sample_load_balancer_config.dict()
        )
        config_id = create_response.json()["id"]

        # Update the config
        update_data = {"enabled": False}
        response = client.patch(f"/api/ai/load-balancer/configs/{config_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_update_load_balancer_config_not_found(self, client):
        """Test updating non-existent load balancer config"""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/api/ai/load-balancer/configs/{fake_id}", json={"enabled": False})
        assert response.status_code == 404


# ============================================================================
# Capability Evaluator Tests
# ============================================================================


class TestCapabilityEvaluator:
    """Test suite for capability evaluator endpoints"""

    @patch("api.ai_advanced_router.evaluate_model")
    async def test_evaluate_capability_with_engine(
        self, mock_evaluate, client, sample_evaluate_request
    ):
        """Test evaluating capability with actual engine"""
        mock_evaluate.return_value = {"capabilities": {"reasoning": 0.9}, "overall_score": 0.85}
        response = client.post(
            "/api/ai/capability-evaluator/evaluate", json=sample_evaluate_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "model_id" in data
        assert "capabilities" in data
        assert "overall_score" in data

    def test_evaluate_capability_fallback(self, client, sample_evaluate_request):
        """Test evaluating capability with fallback"""
        response = client.post(
            "/api/ai/capability-evaluator/evaluate", json=sample_evaluate_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "model_id" in data
        assert "capabilities" in data
        assert "overall_score" in data


# ============================================================================
# Cost Optimizer Tests
# ============================================================================


class TestCostOptimizer:
    """Test suite for cost optimizer endpoints"""

    @patch("api.ai_advanced_router.get_suggestions")
    async def test_get_cost_suggestions_with_engine(self, mock_get, client):
        """Test getting cost suggestions with actual engine"""
        mock_get.return_value = []
        response = client.get("/api/ai/cost-optimizer/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_get_cost_suggestions_fallback(self, client):
        """Test getting cost suggestions with fallback"""
        response = client.get("/api/ai/cost-optimizer/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_create_cost_suggestion(self, client, sample_cost_suggestion):
        """Test creating a cost suggestion"""
        response = client.post(
            "/api/ai/cost-optimizer/suggestions", json=sample_cost_suggestion.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["type"] == "model_selection"


# ============================================================================
# LLM Router Tests
# ============================================================================


class TestLLMRouter:
    """Test suite for LLM router endpoints"""

    @patch("api.ai_advanced_router.get_rules")
    async def test_get_routing_rules_with_engine(self, mock_get, client):
        """Test getting routing rules with actual engine"""
        mock_get.return_value = []
        response = client.get("/api/ai/llm-router/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data

    def test_get_routing_rules_fallback(self, client):
        """Test getting routing rules with fallback"""
        response = client.get("/api/ai/llm-router/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data

    @patch("api.ai_advanced_router.add_rule")
    async def test_create_routing_rule_with_engine(self, mock_add, client, sample_routing_rule):
        """Test creating routing rule with actual engine"""
        mock_add.return_value = {"id": "rule-123", "name": "Test Rule"}
        response = client.post("/api/ai/llm-router/rules", json=sample_routing_rule.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Rule"

    def test_create_routing_rule_fallback(self, client, sample_routing_rule):
        """Test creating routing rule with fallback"""
        response = client.post("/api/ai/llm-router/rules", json=sample_routing_rule.dict())
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Rule"

    def test_create_routing_rule_invalid_priority(self, client):
        """Test creating routing rule with invalid priority"""
        invalid_rule = {
            "name": "Test Rule",
            "condition": "test",
            "target_model": "gpt-4",
            "priority": 150,  # Too high
        }
        response = client.post("/api/ai/llm-router/rules", json=invalid_rule)
        assert response.status_code == 422

    def test_update_routing_rule(self, client, sample_routing_rule):
        """Test updating routing rule"""
        # First create a rule
        create_response = client.post("/api/ai/llm-router/rules", json=sample_routing_rule.dict())
        rule_id = create_response.json()["id"]

        # Update the rule
        update_data = {"enabled": False}
        response = client.patch(f"/api/ai/llm-router/rules/{rule_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False

    def test_update_routing_rule_not_found(self, client):
        """Test updating non-existent routing rule"""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/api/ai/llm-router/rules/{fake_id}", json={"enabled": False})
        assert response.status_code == 404

    def test_delete_routing_rule(self, client, sample_routing_rule):
        """Test deleting routing rule"""
        # First create a rule
        create_response = client.post("/api/ai/llm-router/rules", json=sample_routing_rule.dict())
        rule_id = create_response.json()["id"]

        # Delete the rule
        response = client.delete(f"/api/ai/llm-router/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_delete_routing_rule_not_found(self, client):
        """Test deleting non-existent routing rule"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/ai/llm-router/rules/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Data Validation Tests
# ============================================================================


class TestDataValidation:
    """Test suite for data validation"""

    def test_fine_tuning_job_validation(self, client):
        """Test fine-tuning job field validation"""
        valid_job = {
            "base_model": "gpt-3.5-turbo",
            "model_name": "custom-model",
            "dataset_id": "dataset-123",
            "learning_rate": 0.0001,
            "epochs": 3,
        }
        response = client.post("/api/ai/model-fine-tuning/jobs", json=valid_job)
        assert response.status_code == 200

    def test_feedback_rating_validation(self, client):
        """Test feedback rating range validation"""
        for rating in [1, 2, 3, 4, 5]:
            feedback = {"type": "positive", "content": "Test", "rating": rating}
            response = client.post("/api/ai/ai-feedback/feedbacks", json=feedback)
            assert response.status_code == 200

    def test_routing_rule_priority_validation(self, client):
        """Test routing rule priority range validation"""
        for priority in [1, 50, 100]:
            rule = {
                "name": "Test Rule",
                "condition": "test",
                "target_model": "gpt-4",
                "priority": priority,
            }
            response = client.post("/api/ai/llm-router/rules", json=rule)
            assert response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling"""

    def test_404_on_nonexistent_resource(self, client):
        """Test 404 error for non-existent resources"""
        fake_id = str(uuid.uuid4())
        endpoints = [
            f"/api/ai/langgraph-dsl/definitions/{fake_id}",
            f"/api/ai/langgraph-workflow/workflows/{fake_id}",
            f"/api/ai/advanced-ai/features/{fake_id}",
            f"/api/ai/ai-feedback/feedbacks/{fake_id}",
            f"/api/ai/rag-knowledge-base/bases/{fake_id}",
            f"/api/ai/load-balancer/configs/{fake_id}",
            f"/api/ai/llm-router/rules/{fake_id}",
        ]
        for endpoint in endpoints:
            response = client.patch(endpoint, json={"name": "test"})
            assert response.status_code == 404

    def test_validation_error_on_missing_required_fields(self, client):
        """Test validation error when required fields are missing"""
        response = client.post("/api/ai/model-fine-tuning/jobs", json={})
        assert response.status_code == 422


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance"""

    def test_multiple_creates(self, client, sample_feedback):
        """Test creating multiple resources"""
        for i in range(10):
            feedback_data = sample_feedback.dict()
            feedback_data["content"] = f"Feedback {i}"
            response = client.post("/api/ai/ai-feedback/feedbacks", json=feedback_data)
            assert response.status_code == 200

    def test_get_after_multiple_creates(self, client, sample_feedback):
        """Test getting list after creating multiple resources"""
        # Create multiple feedbacks
        for i in range(5):
            feedback_data = sample_feedback.dict()
            feedback_data["content"] = f"Feedback {i}"
            client.post("/ai/ai-feedback/feedbacks", json=feedback_data)

        # Get all feedbacks
        response = client.get("/api/ai/ai-feedback/feedbacks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["feedbacks"]) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.ai_advanced_router", "--cov-report=html"])
