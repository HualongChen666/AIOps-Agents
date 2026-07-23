# -*- coding: utf-8 -*-
"""
Integration Documentation Enhancement (Phase 5)
Enterprise-grade integration documentation management system
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class IntegrationDocType(Enum):
    """Integration documentation type"""

    ARCHITECTURE = "architecture"
    API_REFERENCE = "api_reference"
    DATA_FLOW = "data_flow"
    DEPLOYMENT = "deployment"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICES = "best_practices"
    CHANGELOG = "changelog"


class IntegrationDocStatus(Enum):
    """Integration documentation status"""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"


@dataclass
class IntegrationDocumentation:
    """Integration documentation configuration"""

    doc_id: str
    doc_name: str
    doc_type: IntegrationDocType
    component: str
    content: str = ""
    status: IntegrationDocStatus = IntegrationDocStatus.DRAFT
    version: str = "1.0.0"
    author: str = ""
    reviewers: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationDiagram:
    """Integration diagram"""

    diagram_id: str
    diagram_name: str
    diagram_type: str
    component: str
    description: str = ""
    data: str = ""
    format: str = "mermaid"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrationDocumentationManager:
    """Enterprise-grade integration documentation manager"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize integration documentation manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Integration documentation
        self.integration_docs: Dict[str, IntegrationDocumentation] = {}
        self._initialize_default_docs()

        # Integration diagrams
        self.integration_diagrams: Dict[str, IntegrationDiagram] = {}
        self._initialize_default_diagrams()

        # Documentation storage
        self.docs_dir = Path(self.config.get("docs_dir", "./integration_docs"))
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.total_docs = 0
        self.published_docs = 0

        logger.info("Integration documentation manager initialized")

    def _initialize_default_docs(self):
        """Initialize default integration documentation"""
        # Architecture documentation
        self.integration_docs["architecture_overview"] = IntegrationDocumentation(
            doc_id="architecture_overview",
            doc_name="Architecture Overview",
            doc_type=IntegrationDocType.ARCHITECTURE,
            component="system",
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        # API reference
        self.integration_docs["api_reference"] = IntegrationDocumentation(
            doc_id="api_reference",
            doc_name="API Reference",
            doc_type=IntegrationDocType.API_REFERENCE,
            component="api",
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        # Data flow
        self.integration_docs["data_flow"] = IntegrationDocumentation(
            doc_id="data_flow",
            doc_name="Data Flow Documentation",
            doc_type=IntegrationDocType.DATA_FLOW,
            component="data",
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        # Deployment
        self.integration_docs["deployment_guide"] = IntegrationDocumentation(
            doc_id="deployment_guide",
            doc_name="Deployment Guide",
            doc_type=IntegrationDocType.DEPLOYMENT,
            component="deployment",
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        # Troubleshooting
        self.integration_docs["troubleshooting"] = IntegrationDocumentation(
            doc_id="troubleshooting",
            doc_name="Troubleshooting Guide",
            doc_type=IntegrationDocType.TROUBLESHOOTING,
            component="system",
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        # Best practices
        self.integration_docs["best_practices"] = IntegrationDocumentation(
            doc_id="best_practices",
            doc_name="Best Practices",
            doc_type=IntegrationDocType.BEST_PRACTICES,
            component="system",
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        logger.info(f"Initialized {len(self.integration_docs)} default integration documents")

    def _initialize_default_diagrams(self):
        """Initialize default integration diagrams"""
        # System architecture diagram
        self.integration_diagrams["system_architecture"] = IntegrationDiagram(
            diagram_id="system_architecture",
            diagram_name="System Architecture Diagram",
            diagram_type="architecture",
            component="system",
            description="Overall system architecture showing all layers and components",
            format="mermaid",
        )

        # Data flow diagram
        self.integration_diagrams["data_flow"] = IntegrationDiagram(
            diagram_id="data_flow",
            diagram_name="Data Flow Diagram",
            diagram_type="data_flow",
            component="data",
            description="Data flow between components and layers",
            format="mermaid",
        )

        # API flow diagram
        self.integration_diagrams["api_flow"] = IntegrationDiagram(
            diagram_id="api_flow",
            diagram_name="API Flow Diagram",
            diagram_type="api_flow",
            component="api",
            description="API request/response flow",
            format="mermaid",
        )

        logger.info(f"Initialized {len(self.integration_diagrams)} default integration diagrams")

    def register_documentation(self, doc: IntegrationDocumentation) -> None:
        """
        Register integration documentation

        Args:
            doc: Integration documentation
        """
        self.integration_docs[doc.doc_id] = doc
        self.total_docs += 1
        logger.info(f"Registered integration documentation: {doc.doc_id}")

    def register_diagram(self, diagram: IntegrationDiagram) -> None:
        """
        Register integration diagram

        Args:
            diagram: Integration diagram
        """
        self.integration_diagrams[diagram.diagram_id] = diagram
        logger.info(f"Registered integration diagram: {diagram.diagram_id}")

    async def generate_architecture_docs(self) -> str:
        """
        Generate architecture documentation

        Returns:
            Document ID
        """
        doc_id = "architecture_docs_generated"

        content = """
# Architecture Documentation

## System Overview
The AIOps Agent system follows a 7-layer architecture designed for scalability,
maintainability, and performance.

## Layer Architecture

### L1: Data Collection Layer
- Collects data from various sources
- Normalizes and validates data
- Provides unified data interface

### L2: Analysis Layer
- Performs data analysis
- Causal analysis
- Pattern recognition
- Anomaly detection

### L3: Knowledge Layer
- Stores and retrieves knowledge
- Knowledge graph management
- Vector database operations
- Knowledge updates

### L4: Storage Layer
- Data storage management
- Database operations
- Cache management
- Data persistence

### L5: Knowledge Layer (Advanced)
- Advanced knowledge operations
- Knowledge reasoning
- Knowledge inference
- Knowledge synthesis

### L6: Execution Layer
- Task execution
- Workflow management
- Fault tolerance
- Execution monitoring

### L7: Integration Layer
- API integration
- Third-party service integration
- Frontend integration
- Notification management

## Component Integration
Components communicate through well-defined interfaces and follow event-driven architecture patterns.  # noqa: E501

## Technology Stack
- Backend: Python, FastAPI
- Database: PostgreSQL, Redis
- Message Queue: RabbitMQ
- Cache: Redis
- Search: Elasticsearch
- Graph: Neo4j
- Service Discovery: Consul
"""

        doc = IntegrationDocumentation(
            doc_id=doc_id,
            doc_name="Generated Architecture Documentation",
            doc_type=IntegrationDocType.ARCHITECTURE,
            component="system",
            content=content,
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        self.integration_docs[doc_id] = doc
        self.total_docs += 1
        self.published_docs += 1

        await self._save_document(doc)

        logger.info(f"Generated architecture documentation: {doc_id}")

        return doc_id

    async def generate_data_flow_docs(self) -> str:
        """
        Generate data flow documentation

        Returns:
            Document ID
        """
        doc_id = "data_flow_docs_generated"

        content = """
# Data Flow Documentation

## Data Flow Overview
Data flows through the system in a structured manner, following the 7-layer architecture.

## Data Collection Flow
1. L1 collects data from external sources
2. Data is normalized and validated
3. Data is passed to L2 for analysis

## Analysis Flow
1. L2 receives data from L1
2. Analysis is performed
3. Results are stored in L3 and L4

## Knowledge Flow
1. L3 stores knowledge from L2 analysis
2. L5 performs advanced knowledge operations
3. Knowledge is retrieved for L6 execution

## Execution Flow
1. L6 receives execution requests
2. Tasks are executed based on knowledge
3. Results are returned through L7

## Integration Flow
1. L7 handles external integrations
2. API requests are processed
3. Third-party services are called
4. Results are aggregated and returned

## Data Consistency
- Event-driven architecture ensures data consistency
- Message queues guarantee reliable delivery
- Caching layers optimize performance
"""

        doc = IntegrationDocumentation(
            doc_id=doc_id,
            doc_name="Generated Data Flow Documentation",
            doc_type=IntegrationDocType.DATA_FLOW,
            component="data",
            content=content,
            status=IntegrationDocStatus.PUBLISHED,
            version="1.0.0",
        )

        self.integration_docs[doc_id] = doc
        self.total_docs += 1
        self.published_docs += 1

        await self._save_document(doc)

        logger.info(f"Generated data flow documentation: {doc_id}")

        return doc_id

    async def _save_document(self, doc: IntegrationDocumentation) -> None:
        """
        Save documentation to file

        Args:
            doc: Documentation
        """
        doc_path = self.docs_dir / f"{doc.doc_id}.md"

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc.content)

        # Update updated_at
        doc.updated_at = datetime.now(timezone.utc)

    def get_documentation(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get integration documentation

        Args:
            doc_id: Document ID

        Returns:
            Documentation details
        """
        if doc_id not in self.integration_docs:
            return None

        doc = self.integration_docs[doc_id]

        return {
            "doc_id": doc.doc_id,
            "doc_name": doc.doc_name,
            "doc_type": doc.doc_type.value,
            "component": doc.component,
            "status": doc.status.value,
            "version": doc.version,
            "author": doc.author,
            "reviewers": doc.reviewers,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }

    def list_documentation(
        self,
        doc_type: Optional[IntegrationDocType] = None,
        component: Optional[str] = None,
        status: Optional[IntegrationDocStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        List integration documentation with filters

        Args:
            doc_type: Filter by type
            component: Filter by component
            status: Filter by status

        Returns:
            List of documentation
        """
        docs = []

        for doc in self.integration_docs.values():
            if doc_type and doc.doc_type != doc_type:
                continue
            if component and doc.component != component:
                continue
            if status and doc.status != status:
                continue

            docs.append(
                {
                    "doc_id": doc.doc_id,
                    "doc_name": doc.doc_name,
                    "doc_type": doc.doc_type.value,
                    "component": doc.component,
                    "status": doc.status.value,
                    "version": doc.version,
                }
            )

        return docs

    def get_diagram(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        """
        Get integration diagram

        Args:
            diagram_id: Diagram ID

        Returns:
            Diagram details
        """
        if diagram_id not in self.integration_diagrams:
            return None

        diagram = self.integration_diagrams[diagram_id]

        return {
            "diagram_id": diagram.diagram_id,
            "diagram_name": diagram.diagram_name,
            "diagram_type": diagram.diagram_type,
            "component": diagram.component,
            "description": diagram.description,
            "format": diagram.format,
            "created_at": diagram.created_at.isoformat(),
        }

    async def update_documentation(
        self, doc_id: str, content: str, version: Optional[str] = None
    ) -> bool:
        """
        Update integration documentation

        Args:
            doc_id: Document ID
            content: New content
            version: New version

        Returns:
            Success status
        """
        if doc_id not in self.integration_docs:
            return False

        doc = self.integration_docs[doc_id]
        doc.content = content
        doc.updated_at = datetime.now(timezone.utc)

        if version:
            doc.version = version

        await self._save_document(doc)

        logger.info(f"Updated integration documentation: {doc_id}")

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get integration documentation statistics"""
        return {
            "total_docs": self.total_docs,
            "published_docs": self.published_docs,
            "draft_docs": len(
                [
                    d
                    for d in self.integration_docs.values()
                    if d.status == IntegrationDocStatus.DRAFT
                ]
            ),
            "total_diagrams": len(self.integration_diagrams),
            "by_type": {
                doc_type.value: len(
                    [d for d in self.integration_docs.values() if d.doc_type == doc_type]
                )
                for doc_type in IntegrationDocType
            },
        }


def get_integration_documentation_manager(
    config: Optional[Dict[str, Any]] = None,
) -> IntegrationDocumentationManager:
    """
    Factory function to get integration documentation manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        IntegrationDocumentationManager: Manager instance
    """
    return IntegrationDocumentationManager(config)
