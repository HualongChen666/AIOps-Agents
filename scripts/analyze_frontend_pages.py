#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Frontend Page Classification Analysis Script
==========================================

Analyzes all frontend pages to classify them into:
- Core functional pages (150-200)
- Auxiliary pages (configuration, help, tools)
- Redundant pages (duplicates, empty shells, test pages)

This script automatically analyzes page complexity, business logic, and backend support.
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import json


class PageAnalyzer:
    """Analyzes frontend pages for classification"""

    def __init__(self, frontend_path: str):
        self.frontend_path = Path(frontend_path)
        self.pages = []
        self.classification_results = {
            "core_functional": [],
            "auxiliary": [],
            "redundant": []
        }

    def find_all_pages(self) -> List[Path]:
        """Find all page.tsx files"""
        page_files = []
        for root, dirs, files in os.walk(self.frontend_path):
            # Skip test files and node_modules
            if "__tests__" in root or "node_modules" in root or ".next" in root:
                continue
            
            for file in files:
                if file == "page.tsx":
                    page_files.append(Path(root) / file)
        
        return page_files

    def analyze_page_complexity(self, page_path: Path) -> Dict[str, Any]:
        """Analyze page complexity"""
        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count lines of code
            lines = content.split('\n')
            code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('//')])
            
            # Count imports
            imports = len(re.findall(r'import.*from', content))
            
            # Count function definitions
            functions = len(re.findall(r'function\s+\w+|const\s+\w+\s*=\s*\(|const\s+\w+\s*=\s*async', content))
            
            # Count API calls
            api_calls = len(re.findall(r'fetch\(|axios\.|useFetch|useSWR', content))
            
            # Count hooks usage
            hooks = len(re.findall(r'use[A-Z]\w+', content))
            
            return {
                "code_lines": code_lines,
                "imports": imports,
                "functions": functions,
                "api_calls": api_calls,
                "hooks": hooks,
                "complexity_score": code_lines + imports * 5 + functions * 3 + api_calls * 2
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "complexity_score": 0
            }

    def analyze_backend_support(self, page_path: Path) -> Dict[str, Any]:
        """Analyze backend API support"""
        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract API endpoints
            api_endpoints = re.findall(r'/api/[^\s\'"]+', content)
            
            # Check for real API integration patterns
            has_real_api = any(endpoint for endpoint in api_endpoints if len(endpoint) > 10)
            
            # Check for mock data or hardcoded values
            has_mock_data = bool(re.search(r'mock|stub|dummy|placeholder|hardcoded', content, re.IGNORECASE))
            
            # Check for error handling
            has_error_handling = bool(re.search(r'try.*catch|error|exception', content, re.IGNORECASE))
            
            return {
                "api_endpoints": api_endpoints,
                "endpoint_count": len(api_endpoints),
                "has_real_api": has_real_api,
                "has_mock_data": has_mock_data,
                "has_error_handling": has_error_handling
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "endpoint_count": 0,
                "has_real_api": False
            }

    def analyze_business_logic(self, page_path: Path) -> Dict[str, Any]:
        """Analyze business logic completeness"""
        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for state management
            has_state = bool(re.search(r'useState|useReducer|zustand|redux', content, re.IGNORECASE))
            
            # Check for form handling
            has_forms = bool(re.search(r'form|input|submit|validation', content, re.IGNORECASE))
            
            # Check for data visualization
            has_charts = bool(re.search(r'chart|graph|plot|visualization', content, re.IGNORECASE))
            
            # Check for real-time features
            has_realtime = bool(re.search(r'websocket|sse|polling|interval', content, re.IGNORECASE))
            
            return {
                "has_state": has_state,
                "has_forms": has_forms,
                "has_charts": has_charts,
                "has_realtime": has_realtime,
                "business_logic_score": sum([has_state, has_forms, has_charts, has_realtime])
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "business_logic_score": 0
            }

    def classify_page(self, page_path: Path) -> str:
        """Classify a single page"""
        complexity = self.analyze_page_complexity(page_path)
        backend = self.analyze_backend_support(page_path)
        business = self.analyze_business_logic(page_path)
        
        # Classification logic
        complexity_score = complexity.get("complexity_score", 0)
        has_real_api = backend.get("has_real_api", False)
        has_mock_data = backend.get("has_mock_data", False)
        business_score = business.get("business_logic_score", 0)
        
        # Core functional pages: high complexity, real API, business logic
        if complexity_score > 50 and has_real_api and not has_mock_data and business_score >= 2:
            return "core_functional"
        
        # Auxiliary pages: medium complexity, some functionality
        elif complexity_score > 20 and (has_real_api or business_score >= 1):
            return "auxiliary"
        
        # Redundant pages: low complexity, mock data, no real functionality
        elif complexity_score <= 20 or has_mock_data or not has_real_api:
            return "redundant"
        
        # Default to auxiliary for borderline cases
        return "auxiliary"

    def analyze_all_pages(self) -> Dict[str, Any]:
        """Analyze all pages and generate classification report"""
        page_files = self.find_all_pages()
        
        analysis_results = []
        
        for page_path in page_files:
            relative_path = page_path.relative_to(self.frontend_path)
            
            complexity = self.analyze_page_complexity(page_path)
            backend = self.analyze_backend_support(page_path)
            business = self.analyze_business_logic(page_path)
            classification = self.classify_page(page_path)
            
            page_info = {
                "path": str(relative_path),
                "classification": classification,
                "complexity": complexity,
                "backend_support": backend,
                "business_logic": business
            }
            
            analysis_results.append(page_info)
            self.classification_results[classification].append(page_info)
        
        return {
            "total_pages": len(page_files),
            "core_functional_count": len(self.classification_results["core_functional"]),
            "auxiliary_count": len(self.classification_results["auxiliary"]),
            "redundant_count": len(self.classification_results["redundant"]),
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "pages": analysis_results
        }

    def generate_classification_report(self, results: Dict[str, Any]) -> str:
        """Generate classification report"""
        report = []
        report.append("=" * 60)
        report.append("Frontend Page Classification Report")
        report.append("=" * 60)
        report.append(f"Analysis Timestamp: {results['analysis_timestamp']}")
        report.append(f"Total Pages Analyzed: {results['total_pages']}")
        report.append("")
        
        report.append("Classification Summary:")
        report.append("-" * 60)
        report.append(f"Core Functional Pages: {results['core_functional_count']}")
        report.append(f"Auxiliary Pages: {results['auxiliary_count']}")
        report.append(f"Redundant Pages: {results['redundant_count']}")
        report.append("")
        
        # Core functional pages
        report.append("Core Functional Pages (with backend support):")
        report.append("-" * 60)
        for page in self.classification_results["core_functional"][:20]:  # Show first 20
            report.append(f"  - {page['path']}")
            report.append(f"    Complexity: {page['complexity']['complexity_score']}")
            report.append(f"    API Endpoints: {page['backend_support']['endpoint_count']}")
            report.append(f"    Business Logic: {page['business_logic']['business_logic_score']}")
        
        if len(self.classification_results["core_functional"]) > 20:
            report.append(f"  ... and {len(self.classification_results['core_functional']) - 20} more")
        
        report.append("")
        
        # Auxiliary pages
        report.append("Auxiliary Pages (configuration, help, tools):")
        report.append("-" * 60)
        for page in self.classification_results["auxiliary"][:10]:  # Show first 10
            report.append(f"  - {page['path']}")
        
        if len(self.classification_results["auxiliary"]) > 10:
            report.append(f"  ... and {len(self.classification_results['auxiliary']) - 10} more")
        
        report.append("")
        
        # Redundant pages
        report.append("Redundant Pages (duplicates, empty shells, test pages):")
        report.append("-" * 60)
        for page in self.classification_results["redundant"][:10]:  # Show first 10
            report.append(f"  - {page['path']}")
            report.append(f"    Reason: Low complexity or mock data")
        
        if len(self.classification_results["redundant"]) > 10:
            report.append(f"  ... and {len(self.classification_results['redundant']) - 10} more")
        
        report.append("")
        
        # Classification criteria
        report.append("Classification Criteria:")
        report.append("-" * 60)
        report.append("Core Functional Pages:")
        report.append("  - High complexity (>50 score)")
        report.append("  - Real API integration")
        report.append("  - No mock data")
        report.append("  - Business logic score >= 2")
        report.append("")
        report.append("Auxiliary Pages:")
        report.append("  - Medium complexity (>20 score)")
        report.append("  - Some functionality (API or business logic)")
        report.append("")
        report.append("Redundant Pages:")
        report.append("  - Low complexity (<=20 score)")
        report.append("  - Mock data or no real API")
        report.append("  - Limited functionality")
        
        return "\n".join(report)


def main():
    """Main classification function"""
    frontend_path = "C:/aiops-sre-agent/frontend"
    
    print("Starting Frontend Page Classification Analysis...")
    print("=" * 60)
    
    analyzer = PageAnalyzer(frontend_path)
    results = analyzer.analyze_all_pages()
    
    # Generate and print report
    report = analyzer.generate_classification_report(results)
    print(report)
    
    # Save detailed results to JSON
    results_file = "frontend_page_classification_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Save report to file
    report_file = "frontend_page_classification_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"Report saved to: {report_file}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
