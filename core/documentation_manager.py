# -*- coding: utf-8 -*-
"""
Documentation Manager
Enterprise-grade documentation management and generation
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class DocType(Enum):
    """Documentation types"""

    USER_MANUAL = "user_manual"
    USER_GUIDE = "user_guide"
    UI_DOCUMENTATION = "ui_documentation"
    VIDEO_TUTORIAL = "video_tutorial"
    ARCHITECTURE = "architecture"
    DEVELOPER_GUIDE = "developer_guide"
    API_DOCUMENTATION = "api_documentation"
    DEPLOYMENT_GUIDE = "deployment_guide"
    SECURITY_GUIDE = "security_guide"


class DocStatus(Enum):
    """Documentation status"""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


@dataclass
class Document:
    """Document metadata"""

    doc_id: str
    title: str
    doc_type: DocType
    status: DocStatus
    version: str
    author: str
    last_updated: datetime
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocTemplate:
    """Documentation template"""

    template_id: str
    template_name: str
    doc_type: DocType
    template_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentationManager:
    """
    Enterprise-grade documentation manager
    Provides documentation management, generation, and version control
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize documentation manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Documents registry
        self.documents: Dict[str, Document] = {}

        # Document templates
        self.templates: Dict[str, DocTemplate] = {}

        # Document categories
        self.categories: Dict[str, List[str]] = {}

        # Configuration
        self.default_author = self.config.get("default_author", "System")
        self.auto_generate_toc = self.config.get("auto_generate_toc", True)

        # Statistics
        self.total_documents = 0
        self.published_documents = 0

        # Load default templates
        self._load_default_templates()

        logger.info("Documentation manager initialized")

    def _load_default_templates(self) -> None:
        """Load default documentation templates"""
        # User manual template
        self.templates["user_manual"] = DocTemplate(
            template_id="user_manual",
            template_name="User Manual Template",
            doc_type=DocType.USER_MANUAL,
            template_content="""''# {title}

## Table of Contents
- [Quick Start](#quick-start)
- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Quick Start
{quick_start_content}

## Features
{features_content}

## Configuration
{configuration_content}

## Usage
{usage_content}

## Troubleshooting
{troubleshooting_content}

## Best Practices
{best_practices_content}

---
*Last Updated: {last_updated}*
*Version: {version}*
*Author: {author}*
""",
            metadata={"description": "Template for user manuals"},
        )

        # API documentation template
        self.templates["api_documentation"] = DocTemplate(
            template_id="api_documentation",
            template_name="API Documentation Template",
            doc_type=DocType.API_DOCUMENTATION,
            template_content="""''# {title}

## API Documentation

### Overview
{overview_content}

### Base URL
```
{base_url}
```

### Authentication
{authentication_content}

### Endpoints
{endpoints_content}

### Error Codes
{error_codes_content}

### Examples
{examples_content}

---
*Last Updated: {last_updated}*
*Version: {version}*
*Author: {author}*
""",
            metadata={"description": "Template for API documentation"},
        )

        # Developer guide template
        self.templates["developer_guide"] = DocTemplate(
            template_id="developer_guide",
            template_name="Developer Guide Template",
            doc_type=DocType.DEVELOPER_GUIDE,
            template_content="""''# {title}

## Developer Guide

## Getting Started
{getting_started_content}

## Development Environment
{development_environment_content}

## Code Standards
{code_standards_content}

## Testing
{testing_content}

## Deployment
{deployment_content}

---
*Last Updated: {last_updated}*
*Version: {version}*
*Author: {author}*
""",
            metadata={"description": "Template for developer guides"},
        )

        # Deployment guide template
        self.templates["deployment_guide"] = DocTemplate(
            template_id="deployment_guide",
            template_name="Deployment Guide Template",
            doc_type=DocType.DEPLOYMENT_GUIDE,
            template_content="""''# {title}

## Deployment Guide

## Prerequisites
{prerequisites_content}

## Installation
{installation_content}

## Configuration
{configuration_content}

## Monitoring
{monitoring_content}

## Troubleshooting
{troubleshooting_content}

---
*Last Updated: {last_updated}*
*Version: {version}*
*Author: {author}*
""",
            metadata={"description": "Template for deployment guides"},
        )

        # Security guide template
        self.templates["security_guide"] = DocTemplate(
            template_id="security_guide",
            template_name="Security Guide Template",
            doc_type=DocType.SECURITY_GUIDE,
            template_content="""''# {title}

## Security Guide

## Overview
{overview_content}

## Security Configuration
{security_configuration_content}

## Access Control
{access_control_content}

## Audit Logging
{audit_logging_content}

## Incident Response
{incident_response_content}

---
*Last Updated: {last_updated}*
*Version: {version}*
*Author: {author}*
""",
            metadata={"description": "Template for security guides"},
        )

    def create_document(
        self,
        doc_id: str,
        title: str,
        doc_type: DocType,
        content: str,
        author: Optional[str] = None,
        version: str = "1.0",
    ) -> bool:
        """
        Create a document

        Args:
            doc_id: Document ID
            title: Document title
            doc_type: Document type
            content: Document content
            author: Document author
            version: Document version

        Returns:
            True if created, False otherwise
        """
        if doc_id in self.documents:
            logger.warning(f"Document {doc_id} already exists")
            return False

        document = Document(
            doc_id=doc_id,
            title=title,
            doc_type=doc_type,
            status=DocStatus.DRAFT,
            version=version,
            author=author or self.default_author,
            last_updated=datetime.now(timezone.utc),
            content=content,
        )

        self.documents[doc_id] = document
        self.total_documents += 1

        # Add to category
        if doc_type.value not in self.categories:
            self.categories[doc_type.value] = []
        self.categories[doc_type.value].append(doc_id)

        logger.info(f"Created document: {doc_id}")

        return True

    def generate_document_from_template(
        self, template_id: str, title: str, content_vars: Dict[str, str], output_path: str
    ) -> bool:
        """
        Generate document from template

        Args:
            template_id: Template ID
            title: Document title
            content_vars: Content variables
            output_path: Output file path

        Returns:
            True if generated, False otherwise
        """
        if template_id not in self.templates:
            logger.error(f"Template {template_id} not found")
            return False

        template = self.templates[template_id]

        try:
            # Generate content from template
            content = template.template_content.format(
                title=title,
                last_updated=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                version=content_vars.get("version", "1.0"),
                author=content_vars.get("author", self.default_author),
                **content_vars,
            )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Generated document from template: {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error generating document: {e}")
            return False

    def update_document(
        self, doc_id: str, content: Optional[str] = None, status: Optional[DocStatus] = None
    ) -> bool:
        """
        Update document

        Args:
            doc_id: Document ID
            content: New content
            status: New status

        Returns:
            True if updated, False otherwise
        """
        if doc_id not in self.documents:
            logger.error(f"Document {doc_id} not found")
            return False

        document = self.documents[doc_id]

        if content:
            document.content = content
        if status:
            document.status = status

        document.last_updated = datetime.now(timezone.utc)

        if status == DocStatus.PUBLISHED:
            self.published_documents += 1

        logger.info(f"Updated document: {doc_id}")

        return True

    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get document by ID

        Args:
            doc_id: Document ID

        Returns:
            Document or None
        """
        return self.documents.get(doc_id)

    def list_documents(
        self, doc_type: Optional[DocType] = None, status: Optional[DocStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        List documents

        Args:
            doc_type: Filter by document type
            status: Filter by status

        Returns:
            List of document information
        """
        documents = []

        for doc_id, document in self.documents.items():
            # Apply filters
            if doc_type and document.doc_type != doc_type:
                continue
            if status and document.status != status:
                continue

            documents.append(
                {
                    "doc_id": doc_id,
                    "title": document.title,
                    "doc_type": document.doc_type.value,
                    "status": document.status.value,
                    "version": document.version,
                    "author": document.author,
                    "last_updated": document.last_updated.isoformat(),
                }
            )

        return documents

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        Get available documentation templates

        Returns:
            List of available templates
        """
        return [
            {
                "template_id": template.template_id,
                "template_name": template.template_name,
                "doc_type": template.doc_type.value,
                "description": template.metadata.get("description", ""),
            }
            for template in self.templates.values()
        ]

    def get_doc_summary(self) -> Dict[str, Any]:
        """
        Get documentation summary

        Returns:
            Documentation summary
        """
        return {
            "total_documents": self.total_documents,
            "published_documents": self.published_documents,
            "total_templates": len(self.templates),
            "documents_by_type": {
                doc_type: len(docs) for doc_type, docs in self.categories.items()
            },
            "documents_by_status": {
                status.value: len([d for d in self.documents.values() if d.status == status])
                for status in DocStatus
            },
        }


# Global instance
_documentation_manager: Optional[DocumentationManager] = None


def get_documentation_manager() -> DocumentationManager:
    """
    Get the global documentation manager instance

    Returns:
        DocumentationManager instance
    """
    global _documentation_manager
    if _documentation_manager is None:
        _documentation_manager = DocumentationManager()
    return _documentation_manager
