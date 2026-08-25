"""
Metrics Collector Module
Collects and aggregates code quality metrics across multiple files and projects.
Provides comprehensive metrics reporting and trend analysis.
"""

import os
import ast
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json


@dataclass
class FileMetrics:
    """Metrics for a single file."""
    file_path: str
    timestamp: datetime
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: int
    classes: int
    average_function_length: float
    maintainability_index: float
    cyclomatic_complexity: float
    duplication_rate: float
    test_coverage: float = 0.0


@dataclass
class ProjectMetrics:
    """Aggregated metrics for a project."""
    project_name: str
    timestamp: datetime
    total_files: int
    total_lines: int
    total_code_lines: int
    total_comment_lines: int
    total_functions: int
    total_classes: int
    average_maintainability_index: float
    average_complexity: float
    average_duplication_rate: float
    overall_test_coverage: float
    file_metrics: List[FileMetrics] = field(default_factory=list)
    category_breakdown: Dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """Main metrics collector class for code quality metrics."""
    
    def __init__(self):
        self.metrics_history: List[ProjectMetrics] = []
        self.current_session: Dict[str, FileMetrics] = {}
    
    def collect_file_metrics(self, file_path: str, code: str = None) -> FileMetrics:
        """
        Collect metrics for a single file.
        
        Args:
            file_path: Path to the file
            code: Source code (if None, will read from file)
        
        Returns:
            FileMetrics object with collected metrics
        """
        if code is None:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        
        # Basic line metrics
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
        
        # AST-based metrics
        try:
            tree = ast.parse(code)
            functions = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            classes = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            
            # Calculate average function length
            func_lengths = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.end_lineno:
                    func_lengths.append(node.end_lineno - node.lineno)
            
            avg_func_length = sum(func_lengths) / len(func_lengths) if func_lengths else 0
            
            # Calculate cyclomatic complexity
            complexity = self._calculate_average_complexity(tree)
            
        except SyntaxError:
            functions = 0
            classes = 0
            avg_func_length = 0
            complexity = 0
        
        # Calculate maintainability index
        maintainability_index = self._calculate_maintainability_index(
            code_lines, functions, avg_func_length
        )
        
        # Calculate duplication rate (simplified)
        duplication_rate = self._calculate_duplication_rate(code)
        
        metrics = FileMetrics(
            file_path=file_path,
            timestamp=datetime.now(),
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            functions=functions,
            classes=classes,
            average_function_length=avg_func_length,
            maintainability_index=maintainability_index,
            cyclomatic_complexity=complexity,
            duplication_rate=duplication_rate
        )
        
        self.current_session[file_path] = metrics
        return metrics
    
    def collect_project_metrics(self, project_path: str, 
                                 file_patterns: List[str] = None) -> ProjectMetrics:
        """
        Collect metrics for an entire project.
        
        Args:
            project_path: Path to the project directory
            file_patterns: List of file patterns to include (default: ['*.py'])
        
        Returns:
            ProjectMetrics object with aggregated metrics
        """
        if file_patterns is None:
            file_patterns = ['*.py']
        
        project_name = os.path.basename(project_path)
        file_metrics_list = []
        
        # Find all matching files
        for root, dirs, files in os.walk(project_path):
            # Skip common directories to ignore
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 
                                                    '.venv', 'venv', 'env']]
            
            for file in files:
                if any(file.endswith(pattern.replace('*', '')) for pattern in file_patterns):
                    file_path = os.path.join(root, file)
                    try:
                        metrics = self.collect_file_metrics(file_path)
                        file_metrics_list.append(metrics)
                    except Exception as e:
                        print(f"Error collecting metrics for {file_path}: {e}")
        
        # Aggregate metrics
        total_files = len(file_metrics_list)
        total_lines = sum(m.total_lines for m in file_metrics_list)
        total_code_lines = sum(m.code_lines for m in file_metrics_list)
        total_comment_lines = sum(m.comment_lines for m in file_metrics_list)
        total_functions = sum(m.functions for m in file_metrics_list)
        total_classes = sum(m.classes for m in file_metrics_list)
        
        avg_maintainability = (
            sum(m.maintainability_index for m in file_metrics_list) / total_files
            if total_files > 0 else 0
        )
        
        avg_complexity = (
            sum(m.cyclomatic_complexity for m in file_metrics_list) / total_files
            if total_files > 0 else 0
        )
        
        avg_duplication = (
            sum(m.duplication_rate for m in file_metrics_list) / total_files
            if total_files > 0 else 0
        )
        
        # Calculate category breakdown
        category_breakdown = self._calculate_category_breakdown(project_path, file_patterns)
        
        project_metrics = ProjectMetrics(
            project_name=project_name,
            timestamp=datetime.now(),
            total_files=total_files,
            total_lines=total_lines,
            total_code_lines=total_code_lines,
            total_comment_lines=total_comment_lines,
            total_functions=total_functions,
            total_classes=total_classes,
            average_maintainability_index=avg_maintainability,
            average_complexity=avg_complexity,
            average_duplication_rate=avg_duplication,
            overall_test_coverage=0.0,  # Would need test coverage data
            file_metrics=file_metrics_list,
            category_breakdown=category_breakdown
        )
        
        self.metrics_history.append(project_metrics)
        return project_metrics
    
    def _calculate_average_complexity(self, tree: ast.AST) -> float:
        """Calculate average cyclomatic complexity for the file."""
        complexities = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_function_complexity(node)
                complexities.append(complexity)
        
        return sum(complexities) / len(complexities) if complexities else 0
    
    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a single function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _calculate_maintainability_index(self, code_lines: int, 
                                          functions: int, 
                                          avg_func_length: float) -> float:
        """Calculate maintainability index."""
        if code_lines == 0:
            return 100.0
        
        volume = code_lines * (1 if functions == 0 else functions)
        complexity = avg_func_length if avg_func_length > 0 else 1
        
        mi = max(0, 171 - 5.2 * (volume ** 0.23) - 0.23 * complexity - 16.2)
        return min(100, mi)
    
    def _calculate_duplication_rate(self, code: str) -> float:
        """Calculate code duplication rate (simplified)."""
        lines = code.split('\n')
        if len(lines) < 5:
            return 0.0
        
        # Normalize lines
        normalized = [' '.join(line.strip().lower().split()) for line in lines]
        
        # Count duplicates
        seen = set()
        duplicates = 0
        
        for line in normalized:
            if line and line in seen:
                duplicates += 1
            seen.add(line)
        
        return duplicates / len(lines) if lines else 0.0
    
    def _calculate_category_breakdown(self, project_path: str, 
                                       file_patterns: List[str]) -> Dict[str, int]:
        """Calculate breakdown of files by category."""
        categories = defaultdict(int)
        
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules',
                                                    '.venv', 'venv', 'env']]
            
            for file in files:
                if any(file.endswith(pattern.replace('*', '')) for pattern in file_patterns):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_path)
                    
                    # Determine category based on directory structure
                    parts = rel_path.split(os.sep)
                    if len(parts) > 1:
                        category = parts[0]
                    else:
                        category = 'root'
                    
                    categories[category] += 1
        
        return dict(categories)
    
    def get_metrics_summary(self, project_metrics: ProjectMetrics) -> Dict[str, Any]:
        """
        Get a summary of project metrics.
        
        Args:
            project_metrics: ProjectMetrics object
        
        Returns:
            Dictionary with metrics summary
        """
        return {
            'project_name': project_metrics.project_name,
            'timestamp': project_metrics.timestamp.isoformat(),
            'total_files': project_metrics.total_files,
            'total_lines': project_metrics.total_lines,
            'code_to_comment_ratio': (
                project_metrics.total_code_lines / project_metrics.total_comment_lines
                if project_metrics.total_comment_lines > 0 else 0
            ),
            'functions_per_file': (
                project_metrics.total_functions / project_metrics.total_files
                if project_metrics.total_files > 0 else 0
            ),
            'average_maintainability_index': project_metrics.average_maintainability_index,
            'average_complexity': project_metrics.average_complexity,
            'average_duplication_rate': project_metrics.average_duplication_rate,
            'category_breakdown': project_metrics.category_breakdown
        }
    
    def get_trend_analysis(self, metric_name: str, 
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Analyze trends for a specific metric over time.
        
        Args:
            metric_name: Name of the metric to analyze
            limit: Maximum number of historical points to consider
        
        Returns:
            List of trend data points
        """
        trend_data = []
        
        for metrics in self.metrics_history[-limit:]:
            value = getattr(metrics, metric_name, None)
            if value is not None:
                trend_data.append({
                    'timestamp': metrics.timestamp.isoformat(),
                    'value': value
                })
        
        return trend_data
    
    def compare_projects(self, project1: ProjectMetrics, 
                         project2: ProjectMetrics) -> Dict[str, Any]:
        """
        Compare metrics between two projects.
        
        Args:
            project1: First project metrics
            project2: Second project metrics
        
        Returns:
            Dictionary with comparison results
        """
        return {
            'project1': project1.project_name,
            'project2': project2.project_name,
            'file_count_diff': project2.total_files - project1.total_files,
            'line_count_diff': project2.total_lines - project1.total_lines,
            'maintainability_diff': (
                project2.average_maintainability_index - 
                project1.average_maintainability_index
            ),
            'complexity_diff': (
                project2.average_complexity - project1.average_complexity
            ),
            'duplication_diff': (
                project2.average_duplication_rate - project1.average_duplication_rate
            )
        }
    
    def export_metrics(self, project_metrics: ProjectMetrics, 
                       output_path: str, format: str = 'json'):
        """
        Export metrics to a file.
        
        Args:
            project_metrics: ProjectMetrics to export
            output_path: Path to output file
            format: Export format ('json' or 'csv')
        """
        if format == 'json':
            self._export_json(project_metrics, output_path)
        elif format == 'csv':
            self._export_csv(project_metrics, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, project_metrics: ProjectMetrics, output_path: str):
        """Export metrics as JSON."""
        data = {
            'project_name': project_metrics.project_name,
            'timestamp': project_metrics.timestamp.isoformat(),
            'summary': self.get_metrics_summary(project_metrics),
            'file_metrics': [
                {
                    'file_path': m.file_path,
                    'timestamp': m.timestamp.isoformat(),
                    'total_lines': m.total_lines,
                    'code_lines': m.code_lines,
                    'comment_lines': m.comment_lines,
                    'blank_lines': m.blank_lines,
                    'functions': m.functions,
                    'classes': m.classes,
                    'average_function_length': m.average_function_length,
                    'maintainability_index': m.maintainability_index,
                    'cyclomatic_complexity': m.cyclomatic_complexity,
                    'duplication_rate': m.duplication_rate
                }
                for m in project_metrics.file_metrics
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def _export_csv(self, project_metrics: ProjectMetrics, output_path: str):
        """Export metrics as CSV."""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write summary
            writer.writerow(['Summary'])
            writer.writerow(['Project', project_metrics.project_name])
            writer.writerow(['Timestamp', project_metrics.timestamp.isoformat()])
            writer.writerow(['Total Files', project_metrics.total_files])
            writer.writerow(['Total Lines', project_metrics.total_lines])
            writer.writerow(['Avg Maintainability', project_metrics.average_maintainability_index])
            writer.writerow(['Avg Complexity', project_metrics.average_complexity])
            writer.writerow([])
            
            # Write file metrics
            writer.writerow(['File Metrics'])
            writer.writerow(['File Path', 'Lines', 'Code Lines', 'Comment Lines', 
                           'Functions', 'Classes', 'Maintainability', 'Complexity'])
            
            for m in project_metrics.file_metrics:
                writer.writerow([
                    m.file_path,
                    m.total_lines,
                    m.code_lines,
                    m.comment_lines,
                    m.functions,
                    m.classes,
                    m.maintainability_index,
                    m.cyclomatic_complexity
                ])
    
    def clear_history(self):
        """Clear metrics history."""
        self.metrics_history.clear()
    
    def clear_session(self):
        """Clear current session metrics."""
        self.current_session.clear()
