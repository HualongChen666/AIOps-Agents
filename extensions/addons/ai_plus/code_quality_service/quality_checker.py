"""
Quality Checker Module
Provides high-level quality checking functionality that orchestrates
various code analysis tools and provides comprehensive quality reports.
"""

import os
import ast
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class QualityLevel(Enum):
    """Quality level enumeration."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QualityReport:
    """Represents a comprehensive quality report."""
    file_path: str
    overall_score: float
    quality_level: QualityLevel
    total_issues: int
    critical_issues: int
    major_issues: int
    minor_issues: int
    category_scores: Dict[str, float]
    recommendations: List[str]
    metrics: Dict[str, Any]


class QualityChecker:
    """Main quality checker class that provides comprehensive quality assessment."""
    
    def __init__(self):
        self.quality_thresholds = {
            QualityLevel.EXCELLENT: 90,
            QualityLevel.GOOD: 75,
            QualityLevel.FAIR: 60,
            QualityLevel.POOR: 40,
            QualityLevel.CRITICAL: 0
        }
    
    def check_quality(self, code: str, file_path: str = "unknown.py",
                      analysis_results: Dict[str, Any] = None) -> QualityReport:
        """
        Perform comprehensive quality check and generate report.
        
        Args:
            code: The source code to check
            file_path: Original file path for reporting
            analysis_results: Pre-computed analysis results from CodeAnalyzer
        
        Returns:
            QualityReport with comprehensive quality assessment
        """
        if analysis_results is None:
            from code_analyzer import CodeAnalyzer
            analyzer = CodeAnalyzer()
            analysis_results = analyzer.analyze_code(code, file_path)
        
        # Extract scores from analysis results
        category_scores = self._extract_category_scores(analysis_results)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(category_scores)
        
        # Determine quality level
        quality_level = self._determine_quality_level(overall_score)
        
        # Count issues by severity
        issue_counts = self._count_issues(analysis_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(analysis_results, category_scores)
        
        # Collect metrics
        metrics = self._collect_metrics(code)
        
        return QualityReport(
            file_path=file_path,
            overall_score=overall_score,
            quality_level=quality_level,
            total_issues=issue_counts['total'],
            critical_issues=issue_counts['critical'],
            major_issues=issue_counts['major'],
            minor_issues=issue_counts['minor'],
            category_scores=category_scores,
            recommendations=recommendations,
            metrics=metrics
        )
    
    def _extract_category_scores(self, analysis_results: Dict[str, Any]) -> Dict[str, float]:
        """Extract category scores from analysis results."""
        scores = {}
        
        for checker, result in analysis_results.items():
            if checker == 'summary':
                continue
            
            if hasattr(result, 'score'):
                scores[checker] = result.score
            elif isinstance(result, dict) and 'score' in result:
                scores[checker] = result['score']
        
        # Ensure all categories have a score
        default_scores = {
            'flake8': 100,
            'mypy': 100,
            'pylint': 100,
            'bandit': 100,
            'complexity': 100,
            'duplication': 100
        }
        
        for category, default_score in default_scores.items():
            if category not in scores:
                scores[category] = default_score
        
        return scores
    
    def _calculate_overall_score(self, category_scores: Dict[str, float]) -> float:
        """Calculate overall quality score from category scores."""
        if not category_scores:
            return 100.0
        
        # Weight different categories
        weights = {
            'flake8': 0.2,      # Style is important but not critical
            'mypy': 0.15,       # Type safety is important
            'pylint': 0.25,     # General quality is very important
            'bandit': 0.25,     # Security is critical
            'complexity': 0.1,  # Complexity affects maintainability
            'duplication': 0.05 # Duplication is less critical
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for category, score in category_scores.items():
            weight = weights.get(category, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 100.0
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level based on score."""
        for level, threshold in sorted(self.quality_thresholds.items(), 
                                       key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return level
        return QualityLevel.CRITICAL
    
    def _count_issues(self, analysis_results: Dict[str, Any]) -> Dict[str, int]:
        """Count issues by severity from analysis results."""
        counts = {
            'total': 0,
            'critical': 0,
            'major': 0,
            'minor': 0
        }
        
        for checker, result in analysis_results.items():
            if checker == 'summary':
                continue
            
            issues = []
            if hasattr(result, 'issues'):
                issues = result.issues
            elif isinstance(result, dict) and 'issues' in result:
                issues = result['issues']
            
            for issue in issues:
                counts['total'] += 1
                if issue.severity == 'error':
                    counts['critical'] += 1
                elif issue.severity == 'warning':
                    counts['major'] += 1
                else:
                    counts['minor'] += 1
        
        return counts
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any],
                                  category_scores: Dict[str, float]) -> List[str]:
        """Generate improvement recommendations based on analysis results."""
        recommendations = []
        
        # Style recommendations
        if category_scores.get('flake8', 100) < 80:
            recommendations.append(
                "Improve code style by addressing flake8 warnings. "
                "Consider using auto-formatters like black or yapf."
            )
        
        # Type checking recommendations
        if category_scores.get('mypy', 100) < 80:
            recommendations.append(
                "Add type annotations to improve type safety. "
                "Use mypy strict mode for better type checking."
            )
        
        # Quality recommendations
        if category_scores.get('pylint', 100) < 80:
            recommendations.append(
                "Address pylint warnings to improve code quality. "
                "Focus on adding docstrings and reducing code complexity."
            )
        
        # Security recommendations
        if category_scores.get('bandit', 100) < 90:
            recommendations.append(
                "Address security issues immediately. "
                "Review and fix any potential security vulnerabilities."
            )
        
        # Complexity recommendations
        if category_scores.get('complexity', 100) < 70:
            recommendations.append(
                "Reduce code complexity by refactoring large functions. "
                "Consider breaking down complex functions into smaller ones."
            )
        
        # Duplication recommendations
        if category_scores.get('duplication', 100) < 80:
            recommendations.append(
                "Eliminate code duplication by extracting common code into functions. "
                "Consider using helper functions or utility classes."
            )
        
        # If no specific recommendations, add general advice
        if not recommendations:
            recommendations.append(
                "Code quality is good. Continue following best practices "
                "and consider adding more unit tests."
            )
        
        return recommendations
    
    def _collect_metrics(self, code: str) -> Dict[str, Any]:
        """Collect basic code metrics."""
        lines = code.split('\n')
        total_lines = len(lines)
        
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#'):
                comment_lines += 1
            else:
                code_lines += 1
        
        # Count functions and classes
        try:
            tree = ast.parse(code)
            functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
        except SyntaxError:
            functions = 0
            classes = 0
        
        # Calculate average function length
        avg_func_length = 0
        if functions > 0:
            try:
                tree = ast.parse(code)
                func_lengths = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.end_lineno:
                        func_lengths.append(node.end_lineno - node.lineno)
                if func_lengths:
                    avg_func_length = sum(func_lengths) / len(func_lengths)
            except SyntaxError:
                pass
        
        # Calculate maintainability index (simplified version)
        maintainability_index = self._calculate_maintainability_index(
            code_lines, functions, avg_func_length
        )
        
        return {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines,
            'functions': functions,
            'classes': classes,
            'average_function_length': avg_func_length,
            'maintainability_index': maintainability_index
        }
    
    def _calculate_maintainability_index(self, code_lines: int, 
                                          functions: int, 
                                          avg_func_length: float) -> float:
        """
        Calculate maintainability index (simplified version).
        Higher values indicate better maintainability.
        """
        if code_lines == 0:
            return 100.0
        
        # Simplified MI calculation
        volume = code_lines * (1 if functions == 0 else functions)
        complexity = avg_func_length if avg_func_length > 0 else 1
        
        mi = max(0, 171 - 5.2 * (volume ** 0.23) - 0.23 * complexity - 16.2)
        return min(100, mi)
    
    def get_quality_threshold(self, level: QualityLevel) -> float:
        """Get the score threshold for a quality level."""
        return self.quality_thresholds.get(level, 0)
    
    def set_quality_threshold(self, level: QualityLevel, threshold: float):
        """Set the score threshold for a quality level."""
        self.quality_thresholds[level] = threshold
    
    def compare_quality(self, report1: QualityReport, 
                        report2: QualityReport) -> Dict[str, Any]:
        """
        Compare two quality reports.
        
        Args:
            report1: First quality report
            report2: Second quality report
        
        Returns:
            Dictionary containing comparison results
        """
        score_diff = report2.overall_score - report1.overall_score
        issue_diff = report2.total_issues - report1.total_issues
        
        improvement = score_diff > 0
        trend = "improved" if improvement else "declined"
        
        category_diffs = {}
        for category in report1.category_scores:
            diff = report2.category_scores.get(category, 0) - report1.category_scores.get(category, 0)
            category_diffs[category] = diff
        
        return {
            'score_difference': score_diff,
            'issue_difference': issue_diff,
            'trend': trend,
            'improvement': improvement,
            'category_differences': category_diffs,
            'level_changed': report1.quality_level != report2.quality_level,
            'previous_level': report1.quality_level.value,
            'current_level': report2.quality_level.value
        }
