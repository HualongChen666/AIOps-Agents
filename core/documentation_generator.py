# -*- coding: utf-8 -*-
"""
Documentation Generator
Enterprise-grade documentation generation and templating
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class GeneratorType(Enum):
    """Documentation generator types"""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    WIKI = "wiki"


@dataclass
class GeneratedDoc:
    """Generated document metadata"""

    doc_id: str
    title: str
    generator_type: GeneratorType
    content: str
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentationGenerator:
    """
    Enterprise-grade documentation generator
    Provides document generation from templates and data
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize documentation generator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Generated documents registry
        self.generated_docs: Dict[str, GeneratedDoc] = {}

        # Generator templates
        self.generator_templates: Dict[str, str] = {}

        # Configuration
        self.default_generator_type = GeneratorType(
            self.config.get("default_generator_type", "markdown")
        )

        # Statistics
        self.total_generated = 0

        # Load default generator templates
        self._load_generator_templates()

        logger.info("Documentation generator initialized")

    def _load_generator_templates(self) -> None:
        """Load default generator templates"""
        # Quick start guide template
        self.generator_templates["quick_start"] = """# {title} - Quick Start Guide

## Introduction
Welcome to {title}. This guide will help you get started quickly.

## Prerequisites
Before you begin, ensure you have:
- {prerequisites}

## Installation
1. {installation_step_1}
2. {installation_step_2}
3. {installation_step_3}

## First Steps
1. {first_step_1}
2. {first_step_2}
3. {first_step_3}

## Next Steps
- {next_step_1}
- {next_step_2}
- {next_step_3}

## Getting Help
- Documentation: {documentation_url}
- Support: {support_url}
- Community: {community_url}

---
*Generated: {generated_date}*
"""

        # Feature guide template
        self.generator_templates["feature_guide"] = """# {title} - Feature Guide

## Feature Overview
{feature_overview}

## Key Features
### {feature_1}
{feature_1_description}

### {feature_2}
{feature_2_description}

### {feature_3}
{feature_3_description}

## Usage Examples
{usage_examples}

## Configuration
{configuration_guide}

## Best Practices
{best_practices}

---
*Generated: {generated_date}*
"""

        # Troubleshooting guide template
        self.generator_templates["troubleshooting"] = """# {title} - Troubleshooting Guide

## Common Issues

### Issue 1: {issue_1_title}
**Symptoms**: {issue_1_symptoms}
**Cause**: {issue_1_cause}
**Solution**: {issue_1_solution}

### Issue 2: {issue_2_title}
**Symptoms**: {issue_2_symptoms}
**Cause**: {issue_2_cause}
**Solution**: {issue_2_solution}

### Issue 3: {issue_3_title}
**Symptoms**: {issue_3_symptoms}
**Cause**: {issue_3_cause}
**Solution**: {issue_3_solution}

## Getting Additional Help
If you continue to experience issues:
- Check logs: {log_location}
- Contact support: {support_contact}
- Review documentation: {documentation_url}

---
*Generated: {generated_date}*
"""

        # Architecture overview template
        self.generator_templates["architecture"] = """# {title} - Architecture Overview

## System Overview
{system_overview}

## Architecture Diagram
```
{architecture_diagram}
```

## Components
### {component_1}
- Description: {component_1_description}
- Responsibilities: {component_1_responsibilities}
- Dependencies: {component_1_dependencies}

### {component_2}
- Description: {component_2_description}
- Responsibilities: {component_2_responsibilities}
- Dependencies: {component_2_dependencies}

## Data Flow
{data_flow_description}

## Technology Stack
- {tech_1}: {tech_1_description}
- {tech_2}: {tech_2_description}
- {tech_3}: {tech_3_description}

---
*Generated: {generated_date}*
"""

        # API endpoint template
        self.generator_templates["api_endpoint"] = """# {title} - API Endpoint Documentation

## Endpoint: {endpoint_path}
**Method**: {method}
**Description**: {description}

## Request
### Headers
```
{request_headers}
```

### Parameters
{parameters}

### Request Body
```json
{request_body}
```

## Response
### Success Response
**Status Code**: {success_status_code}
```json
{success_response}
```

### Error Response
**Status Code**: {error_status_code}
```json
{error_response}
```

## Example
{example_code}

---
*Generated: {generated_date}*
"""

    def generate_document(
        self,
        doc_id: str,
        title: str,
        template_name: str,
        content_vars: Dict[str, str],
        generator_type: Optional[GeneratorType] = None,
    ) -> Optional[GeneratedDoc]:
        """
        Generate document from template

        Args:
            doc_id: Document ID
            title: Document title
            template_name: Template name
            content_vars: Content variables
            generator_type: Generator type

        Returns:
            Generated document or None
        """
        if template_name not in self.generator_templates:
            logger.error(f"Template {template_name} not found")
            return None

        template = self.generator_templates[template_name]
        gen_type = generator_type or self.default_generator_type

        try:
            # Add default variables
            content_vars["generated_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Generate content
            content = template.format(**content_vars)

            # Create generated document
            generated_doc = GeneratedDoc(
                doc_id=doc_id,
                title=title,
                generator_type=gen_type,
                content=content,
                generated_at=datetime.now(timezone.utc),
                metadata={"template_name": template_name},
            )

            self.generated_docs[doc_id] = generated_doc
            self.total_generated += 1

            logger.info(f"Generated document: {doc_id}")

            return generated_doc
        except Exception as e:
            logger.error(f"Error generating document: {e}")
            return None

    def save_generated_document(self, doc_id: str, output_path: str) -> bool:
        """
        Save generated document to file

        Args:
            doc_id: Document ID
            output_path: Output file path

        Returns:
            True if saved, False otherwise
        """
        if doc_id not in self.generated_docs:
            logger.error(f"Generated document {doc_id} not found")
            return False

        generated_doc = self.generated_docs[doc_id]

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(generated_doc.content)

            # Set restrictive permissions for generated document file (644 - owner read/write, group/others read)
            try:
                import os
                import stat

                os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except (OSError, AttributeError):
                # chmod may fail on Windows or non-Unix systems
                pass

            logger.info(f"Saved generated document: {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return False

    def get_generated_document(self, doc_id: str) -> Optional[GeneratedDoc]:
        """
        Get generated document by ID

        Args:
            doc_id: Document ID

        Returns:
            Generated document or None
        """
        return self.generated_docs.get(doc_id)

    def list_generated_documents(self) -> List[Dict[str, Any]]:
        """
        List all generated documents

        Returns:
            List of generated document information
        """
        return [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "generator_type": doc.generator_type.value,
                "generated_at": doc.generated_at.isoformat(),
            }
            for doc in self.generated_docs.values()
        ]

    def get_available_templates(self) -> List[str]:
        """
        Get available generator templates

        Returns:
            List of template names
        """
        return list(self.generator_templates.keys())

    def get_generator_summary(self) -> Dict[str, Any]:
        """
        Get generator summary

        Returns:
            Generator summary
        """
        return {
            "total_generated": self.total_generated,
            "total_templates": len(self.generator_templates),
            "available_templates": self.get_available_templates(),
        }


# Global instance
_documentation_generator: Optional[DocumentationGenerator] = None


def get_documentation_generator() -> DocumentationGenerator:
    """
    Get the global documentation generator instance

    Returns:
        DocumentationGenerator instance
    """
    global _documentation_generator
    if _documentation_generator is None:
        _documentation_generator = DocumentationGenerator()
    return _documentation_generator
