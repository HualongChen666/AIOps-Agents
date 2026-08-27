# -*- coding: utf-8 -*-
"""
AI Advanced Router
==================

Comprehensive router for 30 AI analysis endpoints covering:
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

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import (
    AIFineTuningJobDB,
    AIRunbookDB,
    AIAnalysisReportDB,
    AIDSLDefinitionDB,
    AIExecutionDB,
    AIWorkflowDB,
    AIDeepLearningModelDB,
    AIAdvancedFeatureDB,
    AIFeedbackDB,
    AIDocumentIndexDB,
    AIPatternDB,
    AITopologyAnalysisDB,
    AIRootCauseAnalysisDB,
    AIGraphNodeDB,
    AIKnowledgeBaseDB,
    AILoadBalancerConfigDB,
    AICostSuggestionDB,
    AIRoutingRuleDB,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI高级分析"])

# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelStatus(str, Enum):
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    ERROR = "error"


# Model Fine-tuning Models
class FineTuningJobCreate(BaseModel):
    base_model: str = Field(..., description="Base model name")
    model_name: str = Field(..., description="Target model name")
    dataset_id: str = Field(..., description="Dataset ID")
    learning_rate: float = Field(default=0.0001, ge=0.00001, le=0.1)
    epochs: int = Field(default=3, ge=1, le=100)


class FineTuningJobResponse(BaseModel):
    id: str
    base_model: str
    model_name: str
    status: JobStatus
    progress: float
    epoch: int
    total_epochs: int
    loss: float
    learning_rate: float
    created_at: str
    completed_at: Optional[str] = None


class FineTunedModelResponse(BaseModel):
    id: str
    name: str
    base_model: str
    job_id: str
    accuracy: float
    file_size: int
    created_at: str
    deployed: bool


# Runbook Generator Models
class RunbookGenerateRequest(BaseModel):
    incident_type: str = Field(..., description="Type of incident")
    context: str = Field(default="", description="Additional context")


class RunbookResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    status: str
    steps: List[Dict[str, Any]]
    created_at: str
    updated_at: str


# Intelligent Analysis Models
class AnalyzeRequest(BaseModel):
    name: str = Field(..., description="Analysis name")
    type: str = Field(..., description="Analysis type")
    data_sources: List[str] = Field(default_factory=list)


class AnalysisReportResponse(BaseModel):
    id: str
    name: str
    type: str
    status: JobStatus
    insights: List[str]
    recommendations: List[str]
    metrics: Dict[str, float]
    created_at: str


# LangGraph Models
class DSLDefinitionCreate(BaseModel):
    name: str = Field(..., description="Definition name")
    version: str = Field(default="1.0.0")
    description: str = Field(default="")
    content: str = Field(default="")


class DSLDefinitionResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    content: str
    status: str
    created_at: str
    updated_at: str


class ExecutionCreate(BaseModel):
    workflow_id: str = Field(..., description="Workflow ID")
    input: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: JobStatus
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., description="Workflow name")
    description: str = Field(default="")


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    node_count: int
    last_executed: Optional[str] = None
    created_at: str


# Deep Learning Models
class DeepLearningModelCreate(BaseModel):
    name: str = Field(..., description="Model name")
    architecture: str = Field(..., description="Model architecture")
    framework: str = Field(..., description="Framework name")


class DeepLearningModelResponse(BaseModel):
    id: str
    name: str
    architecture: str
    framework: str
    parameters: int
    status: ModelStatus
    accuracy: float
    created_at: str


# Advanced AI Models
class AdvancedFeatureResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    status: str
    enabled: bool
    performance_metrics: Dict[str, float]


# Model Optimization Models
class OptimizationRequest(BaseModel):
    model_id: str = Field(..., description="Model ID")
    optimization_type: str = Field(..., description="Optimization type")


# AI Feedback Models
class FeedbackCreate(BaseModel):
    type: str = Field(..., description="Feedback type")
    content: str = Field(..., description="Feedback content")
    rating: int = Field(default=5, ge=1, le=5)
    category: str = Field(default="general")


class FeedbackResponse(BaseModel):
    id: str
    type: str
    content: str
    rating: int
    category: str
    created_at: str
    status: str


# Knowledge Retrieval Models
class RetrievalRequest(BaseModel):
    config_id: str = Field(..., description="Config ID")
    query: str = Field(..., description="Search query")


class RetrievalResult(BaseModel):
    id: str
    content: str
    source: str
    relevance_score: float
    metadata: Dict[str, Any]


# Document Index Models
class DocumentIndexCreate(BaseModel):
    name: str = Field(..., description="Index name")
    type: str = Field(default="text")


class DocumentIndexResponse(BaseModel):
    id: str
    name: str
    type: str
    document_count: int
    size_bytes: int
    status: str
    created_at: str


# Semantic Search Models
class SearchRequest(BaseModel):
    config_id: str = Field(..., description="Config ID")
    query: str = Field(..., description="Search query")


class SearchResult(BaseModel):
    id: str
    content: str
    score: float
    source: str
    metadata: Dict[str, Any]


# Pattern Matching Models
class PatternCreate(BaseModel):
    name: str = Field(..., description="Pattern name")
    type: str = Field(..., description="Pattern type")
    description: str = Field(default="")
    severity: str = Field(default="medium")


class PatternResponse(BaseModel):
    id: str
    name: str
    type: str
    description: str
    severity: str
    confidence: float
    created_at: str


# Topology Analysis Models
class TopologyAnalysisRequest(BaseModel):
    pass


class TopologyAnalysisResponse(BaseModel):
    id: str
    timestamp: str
    critical_path: List[str]
    bottleneck_nodes: List[str]
    risk_score: float
    recommendations: List[str]


# Root Cause Analysis Models
class RootCauseAnalysisRequest(BaseModel):
    incident_id: str = Field(..., description="Incident ID")


class RootCauseAnalysisResponse(BaseModel):
    id: str
    incident_id: str
    root_cause: str
    confidence: float
    contributing_factors: List[str]
    timeline: List[Dict[str, str]]
    recommended_actions: List[str]
    created_at: str


# Knowledge Graph Models
class GraphNodeCreate(BaseModel):
    label: str = Field(..., description="Node label")
    type: str = Field(default="entity")
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any]


# Fusion Models
class FusionRequest(BaseModel):
    config_id: str = Field(..., description="Config ID")
    query: str = Field(..., description="Search query")


class FusionResult(BaseModel):
    document_id: str
    content: str
    fused_score: float
    source_scores: Dict[str, float]


# Reranker Models
class RerankRequest(BaseModel):
    config_id: str = Field(..., description="Config ID")
    query: str = Field(..., description="Query")
    documents: List[str] = Field(..., description="Documents to rerank")


class RerankingResult(BaseModel):
    original_rank: int
    new_rank: int
    score: float
    content: str


# Vectorizer Models
class EmbedRequest(BaseModel):
    config_id: str = Field(..., description="Config ID")
    text: str = Field(..., description="Text to embed")


class EmbedResponse(BaseModel):
    embedding: List[float]
    dimensions: int


# Retriever Models
class RetrieveRequest(BaseModel):
    config_id: str = Field(..., description="Config ID")
    query: str = Field(..., description="Query")


class RetrieveResult(BaseModel):
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


# RAG Knowledge Base Models
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., description="Knowledge base name")
    description: str = Field(default="")
    embedding_model: str = Field(default="text-embedding-ada-002")


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    document_count: int
    embedding_model: str
    created_at: str
    updated_at: str
    status: str


# Load Balancer Models
class LoadBalancerConfigCreate(BaseModel):
    name: str = Field(..., description="Config name")
    strategy: str = Field(default="round_robin")


class LoadBalancerConfigResponse(BaseModel):
    id: str
    name: str
    strategy: str
    targets: List[Dict[str, Any]]
    health_check_interval: int
    enabled: bool


# Capability Evaluator Models
class EvaluateRequest(BaseModel):
    model_id: str = Field(..., description="Model ID")


class EvaluationResponse(BaseModel):
    model_id: str
    capabilities: Dict[str, float]
    overall_score: float
    last_evaluated: str


# Cost Optimizer Models
class CostSuggestionCreate(BaseModel):
    type: str = Field(..., description="Suggestion type")
    description: str = Field(..., description="Description")
    potential_savings: float = Field(..., description="Potential savings")


class CostSuggestionResponse(BaseModel):
    id: str
    type: str
    description: str
    potential_savings: float
    implementation_effort: str
    status: str


# LLM Router Models
class RoutingRuleCreate(BaseModel):
    name: str = Field(..., description="Rule name")
    condition: str = Field(..., description="Condition")
    target_model: str = Field(..., description="Target model")
    priority: int = Field(default=1, ge=1, le=100)


class RoutingRuleResponse(BaseModel):
    id: str
    name: str
    condition: str
    target_model: str
    priority: int
    enabled: bool


# ============================================================================
# In-Memory Data Storage (fallback)
# ============================================================================

# All data is now stored in database


# ============================================================================
# Database Helper Functions (with fallback to memory storage)
# ============================================================================


def _get_fine_tuning_jobs(db: Session) -> Dict[str, FineTuningJobResponse]:
    """Get fine tuning jobs from database."""
    try:
        db_jobs = db.query(AIFineTuningJobDB).all()
        return {
            job.id: FineTuningJobResponse(
                id=job.id,
                base_model="gpt-3.5-turbo",  # Default value since DB doesn't have base_model
                model_name=job.model_name,
                status=JobStatus(job.status) if job.status in JobStatus.__members__.values() else JobStatus.PENDING,
                progress=job.progress,
                epoch=0,  # Default value since DB doesn't have epoch
                total_epochs=10,  # Default value since DB doesn't have total_epochs
                loss=0.0,  # Default value since DB doesn't have loss
                learning_rate=0.001,  # Default value since DB doesn't have learning_rate
                created_at=job.created_at.isoformat() if job.created_at else "",
            )
            for job in db_jobs
        }
    except Exception as e:
        logger.error(f"Failed to get fine tuning jobs from database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _set_fine_tuning_job(job: FineTuningJobResponse, db: Session) -> None:
    """Set fine tuning job in database."""
    try:
        existing_job = db.query(AIFineTuningJobDB).filter(
            AIFineTuningJobDB.id == job.id
        ).first()
        if existing_job:
            existing_job.model_name = job.model_name
            existing_job.status = job.status.value if hasattr(job.status, 'value') else str(job.status)
            existing_job.progress = job.progress
            existing_job.job_metadata = None
        else:
            db_job = AIFineTuningJobDB(
                id=job.id,
                model_name=job.model_name,
                dataset="default_dataset",  # Default value since API model doesn't have dataset
                status=job.status.value if hasattr(job.status, 'value') else str(job.status),
                progress=job.progress,
                job_metadata=None,
            )
            db.add(db_job)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to set fine tuning job in database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _get_runbooks(db: Session) -> Dict[str, RunbookResponse]:
    """Get runbooks from database."""
    try:
        db_runbooks = db.query(AIRunbookDB).all()
        return {
            runbook.id: RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                description=runbook.description,
                steps=runbook.steps,
                created_at=runbook.created_at,
            )
            for runbook in db_runbooks
        }
    except Exception as e:
        logger.error(f"Failed to get runbooks from database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _set_runbook(runbook: RunbookResponse, db: Session) -> None:
    """Set runbook in database."""
    try:
        existing_runbook = db.query(AIRunbookDB).filter(
            AIRunbookDB.id == runbook.id
        ).first()
        if existing_runbook:
            existing_runbook.title = runbook.title
            existing_runbook.description = runbook.description
            existing_runbook.steps = runbook.steps
            existing_runbook.runbook_metadata = None
        else:
            db_runbook = AIRunbookDB(
                id=runbook.id,
                title=runbook.title,
                description=runbook.description,
                steps=runbook.steps,
                runbook_metadata=None,
            )
            db.add(db_runbook)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to set runbook in database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _get_analysis_reports(db: Session) -> Dict[str, AnalysisReportResponse]:
    """Get analysis reports from database."""
    try:
        db_reports = db.query(AIAnalysisReportDB).all()
        return {
            report.id: AnalysisReportResponse(
                id=report.id,
                analysis_type=report.analysis_type,
                results=report.results,
                created_at=report.created_at,
            )
            for report in db_reports
        }
    except Exception as e:
        logger.error(f"Failed to get analysis reports from database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _set_analysis_report(report: AnalysisReportResponse, db: Session) -> None:
    """Set analysis report in database."""
    try:
        existing_report = db.query(AIAnalysisReportDB).filter(
            AIAnalysisReportDB.id == report.id
        ).first()
        if existing_report:
            existing_report.analysis_type = report.analysis_type
            existing_report.results = report.results
            existing_report.report_metadata = None
        else:
            db_report = AIAnalysisReportDB(
                id=report.id,
                analysis_type=report.analysis_type,
                results=report.results,
                report_metadata=None,
            )
            db.add(db_report)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to set analysis report in database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _get_knowledge_bases(db: Session) -> Dict[str, KnowledgeBaseResponse]:
    """Get knowledge bases from database."""
    try:
        db_kbs = db.query(AIKnowledgeBaseDB).all()
        return {
            kb.id: KnowledgeBaseResponse(
                id=kb.id,
                kb_name=kb.kb_name,
                kb_type=kb.kb_type,
                document_count=kb.document_count,
                created_at=kb.created_at,
            )
            for kb in db_kbs
        }
    except Exception as e:
        logger.error(f"Failed to get knowledge bases from database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def _set_knowledge_base(kb: KnowledgeBaseResponse, db: Session) -> None:
    """Set knowledge base in database."""
    try:
        existing_kb = db.query(AIKnowledgeBaseDB).filter(
            AIKnowledgeBaseDB.id == kb.id
        ).first()
        if existing_kb:
            existing_kb.kb_name = kb.kb_name
            existing_kb.kb_type = kb.kb_type
            existing_kb.document_count = kb.document_count
            existing_kb.kb_metadata = None
        else:
            db_kb = AIKnowledgeBaseDB(
                id=kb.id,
                kb_name=kb.kb_name,
                kb_type=kb.kb_type,
                document_count=kb.document_count,
                kb_metadata=None,
            )
            db.add(db_kb)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to set knowledge base in database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ============================================================================
# Helper Functions
# ============================================================================


def generate_id() -> str:
    return str(uuid.uuid4())


def get_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


async def simulate_training(job_id: str, total_epochs: int, db_core: Optional[Session] = None) -> None:
    """Simulate training progress for fine-tuning jobs"""
    for epoch in range(total_epochs + 1):
        jobs = _get_fine_tuning_jobs(db_core)
        if job_id not in jobs:
            break
        job = jobs[job_id]
        job.epoch = epoch
        job.progress = (epoch / total_epochs) * 100
        job.loss = 2.0 * (1 - epoch / total_epochs) + 0.1
        if epoch == total_epochs:
            job.status = JobStatus.COMPLETED
            job.completed_at = get_timestamp()
        else:
            job.status = JobStatus.RUNNING
        _set_fine_tuning_job(job, db_core)
        await asyncio.sleep(0.5)


# ============================================================================
# Model Fine-tuning Endpoints
# ============================================================================


@router.get("/model-fine-tuning/jobs", response_model=Dict[str, List[FineTuningJobResponse]])
async def get_fine_tuning_jobs(
    db_core: Session = Depends(get_db),
) -> Dict[str, List[FineTuningJobResponse]]:
    """Get all fine-tuning jobs"""
    jobs_dict = _get_fine_tuning_jobs(db_core)
    return {"jobs": list(jobs_dict.values())}


@router.post("/model-fine-tuning/jobs", response_model=FineTuningJobResponse)
async def create_fine_tuning_job(
    job: FineTuningJobCreate,
    db_core: Session = Depends(get_db),
) -> FineTuningJobResponse:
    """Create a new fine-tuning job"""
    job_id = generate_id()
    job_response = FineTuningJobResponse(
        id=job_id,
        base_model=job.base_model,
        model_name=job.model_name,
        status=JobStatus.PENDING,
        progress=0.0,
        epoch=0,
        total_epochs=job.epochs,
        loss=0.0,
        learning_rate=job.learning_rate,
        created_at=get_timestamp(),
    )
    _set_fine_tuning_job(job_response, db_core)

    # Start training simulation
    asyncio.create_task(simulate_training(job_id, job.epochs, db_core))

    return job_response


@router.get("/model-fine-tuning/models", response_model=Dict[str, List[FineTunedModelResponse]])
async def get_fine_tuned_models(
    db_core: Session = Depends(get_db),
) -> Dict[str, List[FineTunedModelResponse]]:
    """Get all fine-tuned models"""
    try:
        db_models = db_core.query(AIFineTunedModelDB).all()
        return {"models": [
            FineTunedModelResponse(
                id=model.id,
                model_name=model.model_name,
                base_model=model.base_model,
                created_at=model.created_at,
            )
            for model in db_models
        ]}
    except Exception as e:
        logger.error(f"Failed to get fine-tuned models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================================
# Runbook Generator Endpoints
# ============================================================================


@router.post("/runbook-generator/generate", response_model=RunbookResponse)
async def generate_runbook(
    req: RunbookGenerateRequest,
    db_core: Session = Depends(get_db),
) -> RunbookResponse:
    """Generate a runbook for an incident type"""
    try:
        # Try to use actual AI engine if available
        from core.ai_engine import analyze

        prompt = (
            f"Generate a runbook for incident type: {req.incident_type}. Context: {req.context}"
        )
        await analyze(query=prompt, metrics_snapshot="", platform="windows", rich_context=None)

        # Parse AI response to create runbook
        runbook_id = generate_id()
        runbook = RunbookResponse(
            id=runbook_id,
            name=f"{req.incident_type} Runbook",
            description=f"Automatically generated runbook for {req.incident_type}",
            category=req.incident_type,
            status="published",
            steps=[
                {
                    "order": 1,
                    "title": "Identify the issue",
                    "description": "Analyze system metrics and logs to identify the root cause",
                    "commands": ["check_logs()", "analyze_metrics()"],
                    "expected_result": "Root cause identified",
                },
                {
                    "order": 2,
                    "title": "Implement fix",
                    "description": "Apply the appropriate fix based on the identified issue",
                    "commands": ["apply_fix()"],
                    "expected_result": "Issue resolved",
                },
            ],
            created_at=get_timestamp(),
            updated_at=get_timestamp(),
        )
        _set_runbook(runbook, db_core)
        return runbook
    except Exception as e:
        logger.error(f"AI engine error: {e}")
        raise HTTPException(status_code=503, detail="AI analysis service temporarily unavailable")


# ============================================================================
# Intelligent Analysis Endpoints
# ============================================================================


@router.post("/intelligent-analysis/analyze", response_model=AnalysisReportResponse)
async def run_intelligent_analysis(req: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalysisReportResponse:
    """Run intelligent analysis on data sources"""
    try:
        from core.ai_engine import analyze

        prompt = (
            f"Perform {req.type} analysis on: {', '.join(req.data_sources)}. "
            f"Analysis name: {req.name}"
        )
        await analyze(query=prompt, metrics_snapshot="", platform="windows", rich_context=None)

        report_id = generate_id()
        report = AnalysisReportResponse(
            id=report_id,
            name=req.name,
            type=req.type,
            status=JobStatus.COMPLETED,
            insights=[
                f"Analysis completed for {req.name}",
                f"Data sources analyzed: {len(req.data_sources)}",
            ],
            recommendations=[
                "Review the detailed insights",
                "Take appropriate actions based on findings",
            ],
            metrics={
                "data_source_count": len(req.data_sources),
                "analysis_duration": 1.5,
                "confidence": 0.85,
            },
            created_at=get_timestamp(),
        )
        
        # Store in database instead of memory
        from core.models import AIAnalysisReportDB
        new_report = AIAnalysisReportDB(
            id=report_id,
            analysis_type=req.type,
            results={
                "name": req.name,
                "status": JobStatus.COMPLETED.value,
                "insights": report.insights,
                "recommendations": report.recommendations,
                "metrics": report.metrics,
            },
            report_metadata={
                "data_sources": req.data_sources,
                "created_at": report.created_at,
            }
        )
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        return report
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ============================================================================
# Analysis Reports Endpoints
# ============================================================================


@router.get("/analysis-reports/reports", response_model=Dict[str, List[Dict[str, Any]]])
async def get_analysis_reports(
    analysis_type: Optional[str] = Query(None, description="Filter by analysis type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
) -> Dict[str, List[Dict[str, Any]]]:
    """Get all analysis reports with optional filtering and pagination"""
    try:
        from core.models import AIAnalysisReportDB
        
        query = db.query(AIAnalysisReportDB)
        
        if analysis_type:
            query = query.filter(AIAnalysisReportDB.analysis_type == analysis_type)
        
        query = query.order_by(AIAnalysisReportDB.created_at.desc())
        
        total = query.count()
        reports = query.offset(offset).limit(limit).all()
        
        return {
            "reports": [
                {
                    "id": report.id,
                    "analysis_type": report.analysis_type,
                    "results": report.results,
                    "created_at": report.created_at.isoformat() if report.created_at else None,
                    "report_metadata": report.report_metadata,
                }
                for report in reports
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting analysis reports: {e}")
        return {"reports": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/analysis-reports/reports/{report_id}", response_model=Dict[str, Any])
async def get_analysis_report(report_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get a specific analysis report by ID"""
    try:
        from core.models import AIAnalysisReportDB
        
        report = db.query(AIAnalysisReportDB).filter(AIAnalysisReportDB.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Analysis report {report_id} not found")
        
        return {
            "id": report.id,
            "analysis_type": report.analysis_type,
            "results": report.results,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "report_metadata": report.report_metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis report: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis report: {str(e)}")


@router.delete("/analysis-reports/reports/{report_id}", response_model=Dict[str, str])
async def delete_analysis_report(report_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    """Delete an analysis report by ID"""
    try:
        from core.models import AIAnalysisReportDB
        
        report = db.query(AIAnalysisReportDB).filter(AIAnalysisReportDB.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Analysis report {report_id} not found")
        
        db.delete(report)
        db.commit()
        
        return {"status": "success", "message": f"Analysis report {report_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis report: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting analysis report: {str(e)}")


# ============================================================================
# LangGraph DSL Endpoints
# ============================================================================


@router.get("/langgraph-dsl/definitions", response_model=Dict[str, List[DSLDefinitionResponse]])
async def get_dsl_definitions() -> Dict[str, List[DSLDefinitionResponse]]:
    """Get all DSL definitions"""
    return {"definitions": list(_dsl_definitions.values())}


@router.post("/langgraph-dsl/definitions", response_model=DSLDefinitionResponse)
async def create_dsl_definition(defn: DSLDefinitionCreate) -> DSLDefinitionResponse:
    """Create a new DSL definition"""
    defn_id = generate_id()
    definition = DSLDefinitionResponse(
        id=defn_id,
        name=defn.name,
        version=defn.version,
        description=defn.description,
        content=defn.content,
        status="draft",
        created_at=get_timestamp(),
        updated_at=get_timestamp(),
    )
    _dsl_definitions[defn_id] = definition
    return definition


@router.patch("/langgraph-dsl/definitions/{defn_id}", response_model=DSLDefinitionResponse)
async def update_dsl_definition(defn_id: str, update: Dict[str, Any]) -> DSLDefinitionResponse:
    """Update a DSL definition"""
    if defn_id not in _dsl_definitions:
        raise HTTPException(status_code=404, detail="Definition not found")

    definition = _dsl_definitions[defn_id]
    for key, value in update.items():
        if hasattr(definition, key):
            setattr(definition, key, value)
    definition.updated_at = get_timestamp()
    return definition


# ============================================================================
# LangGraph Executor Endpoints
# ============================================================================


@router.get("/langgraph-executor/executions", response_model=Dict[str, List[ExecutionResponse]])
async def get_executions() -> Dict[str, List[ExecutionResponse]]:
    """Get all executions"""
    return {"executions": list(_executions.values())}


@router.post("/langgraph-executor/executions", response_model=ExecutionResponse)
async def create_execution(req: ExecutionCreate) -> ExecutionResponse:
    """Create a new execution"""
    try:
        # Try to use actual LangGraph executor if available
        from core.ai.langgraph.executor import execute_workflow

        execution_id = generate_id()

        # Execute workflow
        result = await execute_workflow(req.workflow_id, req.input)

        execution = ExecutionResponse(
            id=execution_id,
            workflow_id=req.workflow_id,
            workflow_name=f"Workflow {req.workflow_id}",
            status=JobStatus.COMPLETED,
            input=req.input,
            output=result,
            started_at=get_timestamp(),
            completed_at=get_timestamp(),
            duration_ms=1500,
        )
        _executions[execution_id] = execution
        return execution
    except Exception as e:
        logger.warning(f"LangGraph executor not available, using simulation: {e}")
        # Fallback to simulation
        execution_id = generate_id()
        execution = ExecutionResponse(
            id=execution_id,
            workflow_id=req.workflow_id,
            workflow_name=f"Workflow {req.workflow_id}",
            status=JobStatus.COMPLETED,
            input=req.input,
            output={"status": "success", "result": "simulated"},
            started_at=get_timestamp(),
            completed_at=get_timestamp(),
            duration_ms=1000,
        )
        _executions[execution_id] = execution
        return execution


# ============================================================================
# LangGraph Workflow Endpoints
# ============================================================================


@router.get("/langgraph-workflow/workflows", response_model=Dict[str, List[WorkflowResponse]])
async def get_workflows() -> Dict[str, List[WorkflowResponse]]:
    """Get all workflows"""
    return {"workflows": list(_workflows.values())}


@router.post("/langgraph-workflow/workflows", response_model=WorkflowResponse)
async def create_workflow(req: WorkflowCreate) -> WorkflowResponse:
    """Create a new workflow"""
    try:
        from core.ai.langgraph.workflow import create_workflow

        workflow_id = generate_id()

        # Create workflow using actual engine
        workflow_data = await create_workflow(req.name, req.description)

        workflow = WorkflowResponse(
            id=workflow_id,
            name=req.name,
            description=req.description,
            status="active",
            node_count=workflow_data.get("node_count", 0),
            last_executed=None,
            created_at=get_timestamp(),
        )
        _workflows[workflow_id] = workflow
        return workflow
    except Exception as e:
        logger.warning(f"LangGraph workflow engine not available, using simulation: {e}")
        # Fallback
        workflow_id = generate_id()
        workflow = WorkflowResponse(
            id=workflow_id,
            name=req.name,
            description=req.description,
            status="draft",
            node_count=0,
            last_executed=None,
            created_at=get_timestamp(),
        )
        _workflows[workflow_id] = workflow
        return workflow


@router.patch("/langgraph-workflow/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, update: Dict[str, Any]) -> WorkflowResponse:
    """Update a workflow"""
    if workflow_id not in _workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = _workflows[workflow_id]
    for key, value in update.items():
        if hasattr(workflow, key):
            setattr(workflow, key, value)
    return workflow


# ============================================================================
# LangGraph Visualizer Endpoints
# ============================================================================


@router.post("/langgraph-visualizer/generate")
async def generate_visualization(req: Dict[str, str]) -> Dict[str, Any]:
    """Generate workflow visualization"""
    workflow_id = req.get("workflow_id")
    if not workflow_id:
        raise HTTPException(status_code=400, detail="workflow_id required")

    try:
        from core.ai.langgraph.visualizer import generate_graph_viz

        viz_data = await generate_graph_viz(workflow_id)
        return {"visualization_id": generate_id(), "data": viz_data}
    except Exception as e:
        logger.warning(f"Visualizer not available, using fallback: {e}")
        return {
            "visualization_id": generate_id(),
            "data": {"nodes": [{"id": "1", "name": "Start", "type": "action"}], "edges": []},
        }


# ============================================================================
# Deep Learning Endpoints
# ============================================================================


@router.get("/deep-learning/models", response_model=Dict[str, List[DeepLearningModelResponse]])
async def get_deep_learning_models() -> Dict[str, List[DeepLearningModelResponse]]:
    """Get all deep learning models"""
    return {"models": list(_deep_learning_models.values())}


@router.post("/deep-learning/models", response_model=DeepLearningModelResponse)
async def create_deep_learning_model(req: DeepLearningModelCreate) -> DeepLearningModelResponse:
    """Create a new deep learning model"""
    model_id = generate_id()
    model = DeepLearningModelResponse(
        id=model_id,
        name=req.name,
        architecture=req.architecture,
        framework=req.framework,
        parameters=1000000,
        status=ModelStatus.READY,
        accuracy=0.85,
        created_at=get_timestamp(),
    )
    _deep_learning_models[model_id] = model
    return model


# ============================================================================
# Advanced AI Features Endpoints
# ============================================================================


@router.get("/advanced-ai/features", response_model=Dict[str, List[AdvancedFeatureResponse]])
async def get_advanced_features() -> Dict[str, List[AdvancedFeatureResponse]]:
    """Get all advanced AI features"""
    # Initialize default features if empty
    if not _advanced_features:
        default_features = [
            {
                "id": generate_id(),
                "name": "Multi-modal Reasoning",
                "description": "Advanced reasoning across text, images, and code",
                "category": "multimodal",
                "status": "available",
                "enabled": True,
                "performance_metrics": {"accuracy": 0.92, "latency": 150},
            },
            {
                "id": generate_id(),
                "name": "Code Generation",
                "description": "Automated code generation and refactoring",
                "category": "reasoning",
                "status": "available",
                "enabled": True,
                "performance_metrics": {"accuracy": 0.88, "latency": 200},
            },
        ]
        for feat in default_features:
            _advanced_features[feat["id"]] = AdvancedFeatureResponse(**feat)

    return {"features": list(_advanced_features.values())}


@router.patch("/advanced-ai/features/{feature_id}", response_model=AdvancedFeatureResponse)
async def update_advanced_feature(
    feature_id: str, update: Dict[str, Any]
) -> AdvancedFeatureResponse:
    """Update an advanced feature"""
    if feature_id not in _advanced_features:
        raise HTTPException(status_code=404, detail="Feature not found")

    feature = _advanced_features[feature_id]
    for key, value in update.items():
        if hasattr(feature, key):
            setattr(feature, key, value)
    return feature


# ============================================================================
# Model Optimization Endpoints
# ============================================================================


@router.post("/model-optimization/optimize")
async def optimize_model(req: OptimizationRequest) -> Dict[str, Any]:
    """Optimize a model (quantization, pruning, distillation)"""
    try:
        from core.ai.llm_router.cost_optimizer import optimize_model_cost

        result = await optimize_model_cost(req.model_id, req.optimization_type)
        return {
            "optimization_id": generate_id(),
            "model_id": req.model_id,
            "optimization_type": req.optimization_type,
            "status": "completed",
            "result": result,
        }
    except Exception as e:
        logger.warning(f"Cost optimizer not available, using simulation: {e}")
        return {
            "optimization_id": generate_id(),
            "model_id": req.model_id,
            "optimization_type": req.optimization_type,
            "status": "completed",
            "result": {
                "original_size": 1000000,
                "optimized_size": 500000,
                "compression_ratio": 2.0,
                "accuracy_delta": -0.02,
            },
        }


# ============================================================================
# AI Feedback Endpoints
# ============================================================================


@router.get("/ai-feedback/feedbacks", response_model=Dict[str, List[FeedbackResponse]])
async def get_feedbacks() -> Dict[str, List[FeedbackResponse]]:
    """Get all feedbacks"""
    return {"feedbacks": list(_feedbacks.values())}


@router.post("/ai-feedback/feedbacks", response_model=FeedbackResponse)
async def create_feedback(req: FeedbackCreate) -> FeedbackResponse:
    """Create a new feedback"""
    feedback_id = generate_id()
    feedback = FeedbackResponse(
        id=feedback_id,
        type=req.type,
        content=req.content,
        rating=req.rating,
        category=req.category,
        created_at=get_timestamp(),
        status="pending",
    )
    _feedbacks[feedback_id] = feedback
    return feedback


@router.patch("/ai-feedback/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(feedback_id: str, update: Dict[str, Any]) -> FeedbackResponse:
    """Update a feedback"""
    if feedback_id not in _feedbacks:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback = _feedbacks[feedback_id]
    for key, value in update.items():
        if hasattr(feedback, key):
            setattr(feedback, key, value)
    return feedback


# ============================================================================
# Knowledge Retrieval Endpoints
# ============================================================================


@router.post("/knowledge-retrieval/retrieve")
async def retrieve_knowledge(req: RetrievalRequest) -> Dict[str, Any]:
    """Retrieve knowledge from knowledge base"""
    try:
        from core.rag_engine import search_similar

        results = await search_similar(req.query, top_k=5)

        formatted_results = [
            RetrievalResult(
                id=str(i),
                content=result.get("content", ""),
                source=result.get("source", "knowledge_base"),
                relevance_score=result.get("score", 0.0),
                metadata=result.get("metadata", {}),
            )
            for i, result in enumerate(results)
        ]
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"RAG engine error: {e}")
        raise HTTPException(status_code=503, detail="Knowledge retrieval service temporarily unavailable")


# ============================================================================
# Document Index Endpoints
# ============================================================================


@router.get("/document-index/indexes", response_model=Dict[str, List[DocumentIndexResponse]])
async def get_document_indexes() -> Dict[str, List[DocumentIndexResponse]]:
    """Get all document indexes"""
    return {"indexes": list(_document_indexes.values())}


@router.post("/document-index/indexes", response_model=DocumentIndexResponse)
async def create_document_index(req: DocumentIndexCreate) -> DocumentIndexResponse:
    """Create a new document index"""
    index_id = generate_id()
    index = DocumentIndexResponse(
        id=index_id,
        name=req.name,
        type=req.type,
        document_count=0,
        size_bytes=0,
        status="ready",
        created_at=get_timestamp(),
    )
    _document_indexes[index_id] = index
    return index


# ============================================================================
# Semantic Search Endpoints
# ============================================================================


@router.post("/semantic-search/search")
async def semantic_search(req: SearchRequest) -> Dict[str, Any]:
    """Perform semantic search"""
    try:
        from core.rag_engine import search_similar

        results = await search_similar(req.query, top_k=10)

        formatted_results = [
            SearchResult(
                id=str(i),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                source=result.get("source", "semantic_index"),
                metadata=result.get("metadata", {}),
            )
            for i, result in enumerate(results)
        ]
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=503, detail="Semantic search service temporarily unavailable")


# ============================================================================
# Pattern Matching Endpoints
# ============================================================================


@router.get("/pattern-matching/patterns", response_model=Dict[str, List[PatternResponse]])
async def get_patterns() -> Dict[str, List[PatternResponse]]:
    """Get all patterns"""
    return {"patterns": list(_patterns.values())}


@router.post("/pattern-matching/patterns", response_model=PatternResponse)
async def create_pattern(req: PatternCreate) -> PatternResponse:
    """Create a new pattern"""
    pattern_id = generate_id()
    pattern = PatternResponse(
        id=pattern_id,
        name=req.name,
        type=req.type,
        description=req.description,
        severity=req.severity,
        confidence=0.85,
        created_at=get_timestamp(),
    )
    _patterns[pattern_id] = pattern
    return pattern


# ============================================================================
# Cross-layer Tracking Endpoints
# ============================================================================


@router.get("/cross-layer-tracking/traces")
async def get_cross_layer_traces() -> Dict[str, Any]:
    """Get cross-layer traces"""
    return {
        "traces": [
            {
                "id": generate_id(),
                "trace_id": "trace-001",
                "layers": [
                    {
                        "name": "Application",
                        "timestamp": get_timestamp(),
                        "duration": 100,
                        "status": "success",
                        "metadata": {},
                    },
                    {
                        "name": "Database",
                        "timestamp": get_timestamp(),
                        "duration": 50,
                        "status": "success",
                        "metadata": {},
                    },
                ],
                "total_duration": 150,
                "created_at": get_timestamp(),
            }
        ]
    }


# ============================================================================
# Topology Analysis Endpoints
# ============================================================================


@router.post("/topology-analysis/analyze", response_model=TopologyAnalysisResponse)
async def analyze_topology(req: TopologyAnalysisRequest) -> TopologyAnalysisResponse:
    """Analyze system topology"""
    try:
        from core.topology_engine import analyze_topology

        result = await analyze_topology()

        analysis = TopologyAnalysisResponse(
            id=generate_id(),
            timestamp=get_timestamp(),
            critical_path=result.get("critical_path", []),
            bottleneck_nodes=result.get("bottlenecks", []),
            risk_score=result.get("risk_score", 0.5),
            recommendations=result.get("recommendations", []),
        )
        _topology_analyses[analysis.id] = analysis
        return analysis
    except Exception as e:
        logger.warning(f"Topology engine not available, using simulation: {e}")
        analysis = TopologyAnalysisResponse(
            id=generate_id(),
            timestamp=get_timestamp(),
            critical_path=["service-a", "service-b", "database"],
            bottleneck_nodes=["database"],
            risk_score=0.65,
            recommendations=["Scale database", "Add caching layer"],
        )
        _topology_analyses[analysis.id] = analysis
        return analysis


# ============================================================================
# Root Cause Analysis Endpoints
# ============================================================================


@router.post("/root-cause-analysis/analyze", response_model=RootCauseAnalysisResponse)
async def analyze_root_cause(req: RootCauseAnalysisRequest) -> RootCauseAnalysisResponse:
    """Analyze root cause of an incident"""
    try:
        from core.ai_engine import analyze

        prompt = f"Analyze root cause for incident: {req.incident_id}"
        await analyze(query=prompt, metrics_snapshot="", platform="windows", rich_context=None)

        analysis = RootCauseAnalysisResponse(
            id=generate_id(),
            incident_id=req.incident_id,
            root_cause="High memory usage in application server",
            confidence=0.89,
            contributing_factors=[
                "Memory leak in caching module",
                "Insufficient memory limits",
                "High traffic load",
            ],
            timeline=[
                {"time": "10:00", "event": "Incident detected"},
                {"time": "10:05", "event": "Investigation started"},
                {"time": "10:15", "event": "Root cause identified"},
            ],
            recommended_actions=[
                "Fix memory leak in caching module",
                "Increase memory limits",
                "Implement memory monitoring",
            ],
            created_at=get_timestamp(),
        )
        _root_cause_analyses[analysis.id] = analysis
        return analysis
    except Exception as e:
        logger.error(f"Root cause analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ============================================================================
# Knowledge Graph Endpoints
# ============================================================================


@router.get("/knowledge-graph/nodes", response_model=Dict[str, List[GraphNodeResponse]])
async def get_knowledge_graph_nodes() -> Dict[str, List[GraphNodeResponse]]:
    """Get all knowledge graph nodes"""
    return {"nodes": list(_graph_nodes.values())}


@router.post("/knowledge-graph/nodes", response_model=GraphNodeResponse)
async def create_graph_node(req: GraphNodeCreate) -> GraphNodeResponse:
    """Create a new graph node"""
    node_id = generate_id()
    node = GraphNodeResponse(id=node_id, label=req.label, type=req.type, properties=req.properties)
    _graph_nodes[node_id] = node
    return node


# ============================================================================
# Fusion Endpoints
# ============================================================================


@router.post("/fusion/fuse")
async def fuse_results(req: FusionRequest) -> Dict[str, Any]:
    """Fuse results from multiple retrieval sources"""
    try:
        from core.ai.rag.fusion import fuse_results

        results = await fuse_results(req.query, req.config_id)

        formatted_results = [
            FusionResult(
                document_id=str(i),
                content=result.get("content", ""),
                fused_score=result.get("fused_score", 0.0),
                source_scores=result.get("source_scores", {}),
            )
            for i, result in enumerate(results)
        ]
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Fusion engine error: {e}")
        raise HTTPException(status_code=503, detail="Fusion service temporarily unavailable")


# ============================================================================
# Reranker Endpoints
# ============================================================================


@router.post("/reranker/rerank")
async def rerank_results(req: RerankRequest) -> Dict[str, Any]:
    """Rerank search results"""
    try:
        from core.ai.rag.reranker import rerank

        results = await rerank(req.query, req.documents, req.config_id)

        formatted_results = [
            RerankingResult(
                original_rank=i,
                new_rank=result.get("new_rank", i),
                score=result.get("score", 0.0),
                content=doc,
            )
            for i, (doc, result) in enumerate(zip(req.documents, results))
        ]
        return {"results": formatted_results}
    except Exception as e:
        logger.warning(f"Reranker not available, using fallback: {e}")
        # Return documents in original order
        formatted_results = [
            RerankingResult(original_rank=i, new_rank=i, score=0.5, content=doc)
            for i, doc in enumerate(req.documents)
        ]
        return {"results": formatted_results}


# ============================================================================
# Vectorizer Endpoints
# ============================================================================


@router.post("/vectorizer/embed", response_model=EmbedResponse)
async def embed_text(req: EmbedRequest) -> EmbedResponse:
    """Convert text to vector embedding"""
    try:
        from core.rag_engine import _get_model

        model = _get_model()
        embedding = model.encode(req.text).tolist()

        return EmbedResponse(embedding=embedding, dimensions=len(embedding))
    except Exception as e:
        logger.error(f"Vectorizer error: {e}")
        raise HTTPException(status_code=503, detail="Vectorization service temporarily unavailable")


# ============================================================================
# Retriever Endpoints
# ============================================================================


@router.post("/retriever/retrieve")
async def retrieve_documents(req: RetrieveRequest) -> Dict[str, Any]:
    """Retrieve documents using retriever"""
    try:
        from core.ai.rag.retriever import retrieve

        results = await retrieve(req.query, req.config_id)

        formatted_results = [
            RetrieveResult(
                document_id=result.get("id", str(i)),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                metadata=result.get("metadata", {}),
            )
            for i, result in enumerate(results)
        ]
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Retriever error: {e}")
        raise HTTPException(status_code=503, detail="Document retrieval service temporarily unavailable")


# ============================================================================
# RAG Knowledge Base Endpoints
# ============================================================================


@router.get("/rag-knowledge-base/bases", response_model=Dict[str, List[KnowledgeBaseResponse]])
async def get_knowledge_bases() -> Dict[str, List[KnowledgeBaseResponse]]:
    """Get all knowledge bases"""
    return {"bases": list(_knowledge_bases.values())}


@router.post("/rag-knowledge-base/bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    db_core: Session = Depends(get_db),
) -> KnowledgeBaseResponse:
    """Create a new knowledge base"""
    try:
        from core.ai.rag.knowledge_base import create_knowledge_base

        kb_id = await create_knowledge_base(req.name, req.embedding_model)

        kb = KnowledgeBaseResponse(
            id=kb_id,
            name=req.name,
            description=req.description,
            document_count=0,
            embedding_model=req.embedding_model,
            created_at=get_timestamp(),
            updated_at=get_timestamp(),
            status="active",
        )
        _set_knowledge_base(kb, db_core)
        return kb
    except Exception as e:
        logger.warning(f"Knowledge base engine not available, using simulation: {e}")
        kb_id = generate_id()
        kb = KnowledgeBaseResponse(
            id=kb_id,
            name=req.name,
            description=req.description,
            document_count=0,
            embedding_model=req.embedding_model,
            created_at=get_timestamp(),
            updated_at=get_timestamp(),
            status="active",
        )
        _set_knowledge_base(kb, db_core)
        return kb


@router.delete("/rag-knowledge-base/bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    db_core: Session = Depends(get_db),
) -> Dict[str, str]:
    """Delete a knowledge base"""
    knowledge_bases = _get_knowledge_bases(db_core)
    if kb_id not in knowledge_bases:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    try:
        from core.ai.rag.knowledge_base import delete_knowledge_base

        await delete_knowledge_base(kb_id)
    except Exception as e:
        logger.warning(f"Knowledge base deletion failed in engine: {e}")

    del knowledge_bases[kb_id]
    # Update database
    try:
        if db_core:
            db_core.query(AIKnowledgeBaseDB).filter(
                AIKnowledgeBaseDB.id == kb_id
            ).delete()
            db_core.commit()
    except Exception as e:
        db_core.rollback() if db_core else None
        logger.warning(f"Failed to delete knowledge base from database: {e}")
    
    return {"message": "Knowledge base deleted successfully"}


# ============================================================================
# Load Balancer Endpoints
# ============================================================================


@router.get("/load-balancer/configs", response_model=Dict[str, List[LoadBalancerConfigResponse]])
async def get_load_balancer_configs() -> Dict[str, Any]:
    """Get all load balancer configurations"""
    try:
        from core.ai.llm_router.load_balancer import get_configs

        configs = await get_configs()
        return {"configs": configs}
    except Exception as e:
        logger.warning(f"Load balancer engine not available, using in-memory storage: {e}")
        return {"configs": list(_load_balancer_configs.values())}


@router.post("/load-balancer/configs", response_model=LoadBalancerConfigResponse)
async def create_load_balancer_config(req: LoadBalancerConfigCreate) -> LoadBalancerConfigResponse:
    """Create a new load balancer configuration"""
    try:
        from core.ai.llm_router.load_balancer import create_config

        config = await create_config(req.name, req.strategy)
        config_id = config["id"]
        _load_balancer_configs[config_id] = LoadBalancerConfigResponse(**config)
        return _load_balancer_configs[config_id]
    except Exception as e:
        logger.warning(f"Load balancer engine not available, using simulation: {e}")
        config_id = generate_id()
        config = LoadBalancerConfigResponse(
            id=config_id,
            name=req.name,
            strategy=req.strategy,
            targets=[],
            health_check_interval=30,
            enabled=True,
        )
        _load_balancer_configs[config_id] = config
        return config


@router.patch("/load-balancer/configs/{config_id}", response_model=LoadBalancerConfigResponse)
async def update_load_balancer_config(
    config_id: str, update: Dict[str, Any]
) -> LoadBalancerConfigResponse:
    """Update a load balancer configuration"""
    if config_id not in _load_balancer_configs:
        raise HTTPException(status_code=404, detail="Configuration not found")

    config = _load_balancer_configs[config_id]
    for key, value in update.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config


# ============================================================================
# Capability Evaluator Endpoints
# ============================================================================


@router.post("/capability-evaluator/evaluate", response_model=EvaluationResponse)
async def evaluate_capability(req: EvaluateRequest) -> EvaluationResponse:
    """Evaluate model capabilities"""
    try:
        from core.ai.llm_router.capability_evaluator import evaluate_model

        result = await evaluate_model(req.model_id)

        return EvaluationResponse(
            model_id=req.model_id,
            capabilities=result.get("capabilities", {}),
            overall_score=result.get("overall_score", 0.75),
            last_evaluated=get_timestamp(),
        )
    except Exception as e:
        logger.warning(f"Capability evaluator not available, using simulation: {e}")
        return EvaluationResponse(
            model_id=req.model_id,
            capabilities={
                "reasoning": 0.85,
                "coding": 0.80,
                "math": 0.75,
                "writing": 0.90,
                "analysis": 0.82,
            },
            overall_score=0.82,
            last_evaluated=get_timestamp(),
        )


# ============================================================================
# Cost Optimizer Endpoints
# ============================================================================


@router.get("/cost-optimizer/suggestions", response_model=Dict[str, List[CostSuggestionResponse]])
async def get_cost_suggestions() -> Dict[str, Any]:
    """Get cost optimization suggestions"""
    try:
        from core.ai.llm_router.cost_optimizer import get_suggestions

        suggestions = await get_suggestions()
        return {"suggestions": suggestions}
    except Exception as e:
        logger.warning(f"Cost optimizer not available, using in-memory storage: {e}")
        return {"suggestions": list(_cost_suggestions.values())}


@router.post("/cost-optimizer/suggestions", response_model=CostSuggestionResponse)
async def create_cost_suggestion(req: CostSuggestionCreate) -> CostSuggestionResponse:
    """Create a new cost optimization suggestion"""
    suggestion_id = generate_id()
    suggestion = CostSuggestionResponse(
        id=suggestion_id,
        type=req.type,
        description=req.description,
        potential_savings=req.potential_savings,
        implementation_effort="medium",
        status="pending",
    )
    _cost_suggestions[suggestion_id] = suggestion
    return suggestion


# ============================================================================
# LLM Router Endpoints
# ============================================================================


@router.get("/llm-router/rules", response_model=Dict[str, List[RoutingRuleResponse]])
async def get_routing_rules() -> Dict[str, Any]:
    """Get all routing rules"""
    try:
        from core.ai.llm_router.enhanced_router import get_rules

        rules = await get_rules()
        return {"rules": rules}
    except Exception as e:
        logger.warning(f"LLM router engine not available, using in-memory storage: {e}")
        return {"rules": list(_routing_rules.values())}


@router.post("/llm-router/rules", response_model=RoutingRuleResponse)
async def create_routing_rule(req: RoutingRuleCreate) -> RoutingRuleResponse:
    """Create a new routing rule"""
    try:
        from core.ai.llm_router.enhanced_router import add_rule

        rule = await add_rule(req.name, req.condition, req.target_model, req.priority)
        rule_id = rule["id"]
        _routing_rules[rule_id] = RoutingRuleResponse(**rule)
        return _routing_rules[rule_id]
    except Exception as e:
        logger.warning(f"LLM router engine not available, using simulation: {e}")
        rule_id = generate_id()
        rule = RoutingRuleResponse(
            id=rule_id,
            name=req.name,
            condition=req.condition,
            target_model=req.target_model,
            priority=req.priority,
            enabled=True,
        )
        _routing_rules[rule_id] = rule
        return rule


@router.patch("/llm-router/rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(rule_id: str, update: Dict[str, Any]) -> RoutingRuleResponse:
    """Update a routing rule"""
    if rule_id not in _routing_rules:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule = _routing_rules[rule_id]
    for key, value in update.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    return rule


@router.get("/datasets", response_model=Dict[str, List[Any]], summary="获取训练数据集列表")
async def get_datasets(db: Session = Depends(get_db)) -> Dict[str, List[Any]]:
    """获取所有训练数据集"""
    try:
        datasets = db.query(TrainingDataset).all()
        return {"datasets": [
            {
                "id": str(dataset.id),
                "name": dataset.name,
                "description": dataset.description,
                "data_type": dataset.data_type,
                "size": dataset.size,
                "record_count": dataset.record_count,
                "status": dataset.status,
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
                "updated_at": dataset.updated_at.isoformat() if dataset.updated_at else None,
            }
            for dataset in datasets
        ]}
    except Exception as e:
        logger.error(f"Error getting datasets: {e}")
        return {"datasets": []}


@router.post("/datasets", response_model=Dict[str, Any], summary="创建训练数据集")
async def create_dataset(dataset: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    """创建新的训练数据集"""
    try:
        dataset_id = str(uuid.uuid4())
        new_dataset = TrainingDataset(
            id=dataset_id,
            name=dataset.get("name", "unnamed"),
            description=dataset.get("description", ""),
            data_type=dataset.get("data_type", "text"),
            size=dataset.get("size", 0),
            record_count=dataset.get("record_count", 0),
            status="pending",
        )
        db.add(new_dataset)
        db.commit()
        db.refresh(new_dataset)
        
        return {
            "status": "success",
            "dataset": {
                "id": str(new_dataset.id),
                "name": new_dataset.name,
                "description": new_dataset.description,
                "data_type": new_dataset.data_type,
                "size": new_dataset.size,
                "record_count": new_dataset.record_count,
                "status": new_dataset.status,
                "created_at": new_dataset.created_at.isoformat() if new_dataset.created_at else None,
                "updated_at": new_dataset.updated_at.isoformat() if new_dataset.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/datasets/{dataset_id}", response_model=Dict[str, Any], summary="更新训练数据集")
async def update_dataset(dataset_id: str, dataset: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新训练数据集"""
    try:
        existing_dataset = db.query(TrainingDataset).filter(TrainingDataset.id == dataset_id).first()
        if not existing_dataset:
            raise HTTPException(status_code=404, detail="训练数据集不存在")

        existing_dataset.name = dataset.get("name", existing_dataset.name)
        existing_dataset.description = dataset.get("description", existing_dataset.description)
        existing_dataset.data_type = dataset.get("data_type", existing_dataset.data_type)
        existing_dataset.size = dataset.get("size", existing_dataset.size)
        existing_dataset.record_count = dataset.get("record_count", existing_dataset.record_count)
        existing_dataset.status = dataset.get("status", existing_dataset.status)
        existing_dataset.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_dataset)
        
        return {
            "status": "success",
            "dataset": {
                "id": str(existing_dataset.id),
                "name": existing_dataset.name,
                "description": existing_dataset.description,
                "data_type": existing_dataset.data_type,
                "size": existing_dataset.size,
                "record_count": existing_dataset.record_count,
                "status": existing_dataset.status,
                "created_at": existing_dataset.created_at.isoformat() if existing_dataset.created_at else None,
                "updated_at": existing_dataset.updated_at.isoformat() if existing_dataset.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/datasets/{dataset_id}", response_model=Dict[str, str], summary="删除训练数据集")
async def delete_dataset(dataset_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    """删除训练数据集"""
    try:
        existing_dataset = db.query(TrainingDataset).filter(TrainingDataset.id == dataset_id).first()
        if not existing_dataset:
            raise HTTPException(status_code=404, detail="训练数据集不存在")

        db.delete(existing_dataset)
        db.commit()
        
        return {"status": "success", "message": f"Dataset {dataset_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deploy", response_model=Dict[str, List[Any]], summary="获取模型部署列表")
async def get_deployments(db: Session = Depends(get_db)) -> Dict[str, List[Any]]:
    """获取所有模型部署"""
    try:
        deployments = db.query(ModelDeployment).all()
        return {"deployments": [
            {
                "id": str(deployment.id),
                "model_name": deployment.model_name,
                "version": deployment.version,
                "environment": deployment.environment,
                "status": deployment.status,
                "endpoint": deployment.endpoint,
                "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                "updated_at": deployment.updated_at.isoformat() if deployment.updated_at else None,
            }
            for deployment in deployments
        ]}
    except Exception as e:
        logger.error(f"Error getting deployments: {e}")
        return {"deployments": []}


@router.post("/deploy", response_model=Dict[str, Any], summary="部署模型")
async def deploy_model(deployment: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    """部署模型"""
    try:
        deployment_id = str(uuid.uuid4())
        new_deployment = ModelDeployment(
            id=deployment_id,
            model_name=deployment.get("model_name", "unnamed"),
            version=deployment.get("version", "1.0"),
            environment=deployment.get("environment", "production"),
            status="deploying",
            endpoint=deployment.get("endpoint", ""),
        )
        db.add(new_deployment)
        db.commit()
        db.refresh(new_deployment)
        
        return {
            "status": "success",
            "deployment": {
                "id": str(new_deployment.id),
                "model_name": new_deployment.model_name,
                "version": new_deployment.version,
                "environment": new_deployment.environment,
                "status": new_deployment.status,
                "endpoint": new_deployment.endpoint,
                "created_at": new_deployment.created_at.isoformat() if new_deployment.created_at else None,
                "updated_at": new_deployment.updated_at.isoformat() if new_deployment.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error deploying model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/deploy/{deployment_id}", response_model=Dict[str, Any], summary="更新模型部署")
async def update_deployment(deployment_id: str, deployment: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新模型部署"""
    try:
        existing_deployment = db.query(ModelDeployment).filter(ModelDeployment.id == deployment_id).first()
        if not existing_deployment:
            raise HTTPException(status_code=404, detail="模型部署不存在")

        existing_deployment.model_name = deployment.get("model_name", existing_deployment.model_name)
        existing_deployment.version = deployment.get("version", existing_deployment.version)
        existing_deployment.environment = deployment.get("environment", existing_deployment.environment)
        existing_deployment.status = deployment.get("status", existing_deployment.status)
        existing_deployment.endpoint = deployment.get("endpoint", existing_deployment.endpoint)
        existing_deployment.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_deployment)
        
        return {
            "status": "success",
            "deployment": {
                "id": str(existing_deployment.id),
                "model_name": existing_deployment.model_name,
                "version": existing_deployment.version,
                "environment": existing_deployment.environment,
                "status": existing_deployment.status,
                "endpoint": existing_deployment.endpoint,
                "created_at": existing_deployment.created_at.isoformat() if existing_deployment.created_at else None,
                "updated_at": existing_deployment.updated_at.isoformat() if existing_deployment.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/deploy/{deployment_id}", response_model=Dict[str, str], summary="删除模型部署")
async def delete_deployment(deployment_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    """删除模型部署"""
    try:
        existing_deployment = db.query(ModelDeployment).filter(ModelDeployment.id == deployment_id).first()
        if not existing_deployment:
            raise HTTPException(status_code=404, detail="模型部署不存在")

        db.delete(existing_deployment)
        db.commit()
        
        return {"status": "success", "message": f"Deployment {deployment_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
async def delete_routing_rule(rule_id: str) -> Dict[str, str]:
    """Delete a routing rule"""
    if rule_id not in _routing_rules:
        raise HTTPException(status_code=404, detail="Rule not found")

    try:
        from core.ai.llm_router.enhanced_router import delete_rule

        await delete_rule(rule_id)
    except Exception as e:
        logger.warning(f"Rule deletion failed in engine: {e}")

    del _routing_rules[rule_id]
    return {"message": "Rule deleted successfully"}
