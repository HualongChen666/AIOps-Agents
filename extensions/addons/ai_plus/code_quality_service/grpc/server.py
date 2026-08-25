"""
gRPC Server for Code Quality Service
Implements the CodeQualityService gRPC interface.
"""

import grpc
from concurrent import futures
import os
import sys
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import generated protobuf classes
try:
    from proto import code_quality_pb2
    from proto import code_quality_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    print("Warning: gRPC protobuf files not available. gRPC server functionality disabled.")
    print("To enable gRPC, install grpcio-tools and run: python main.py generate-proto")
    GRPC_AVAILABLE = False
    code_quality_pb2 = None
    code_quality_pb2_grpc = None

from code_analyzer import CodeAnalyzer, Issue, CheckResult
from quality_checker import QualityChecker, QualityReport
from metrics_collector import MetricsCollector


if GRPC_AVAILABLE:
    class CodeQualityServiceImpl(code_quality_pb2_grpc.CodeQualityServiceServicer):
        """Implementation of the CodeQualityService gRPC service."""
        
        def __init__(self):
            self.analyzer = CodeAnalyzer()
            self.quality_checker = QualityChecker()
            self.metrics_collector = MetricsCollector()
        
        def AnalyzeCode(self, request, context):
            """Analyze code quality using multiple checkers."""
            try:
                checkers = list(request.checkers) if request.checkers else None
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                # Perform analysis
                results = self.analyzer.analyze_code(code, file_path, checkers)
                
                # Build response
                response = code_quality_pb2.AnalyzeCodeResponse()
                response.success = True
                response.message = "Code analysis completed successfully"
                
                # Add individual checker results
                for checker_name, result in results.items():
                    if checker_name == 'summary':
                        # Add summary
                        summary = results['summary']
                        response.summary.overall_score = summary.get('overall_score', 0)
                        response.summary.total_issues = summary.get('total_issues', 0)
                        response.summary.critical_issues = summary.get('critical_issues', 0)
                        response.summary.major_issues = summary.get('major_issues', 0)
                        response.summary.minor_issues = summary.get('minor_issues', 0)
                        
                        for checker, score in summary.get('checker_scores', {}).items():
                            response.summary.checker_scores[checker] = score
                    else:
                        # Add checker result
                        check_result = response.results[checker_name]
                        if hasattr(result, 'passed'):
                            check_result.passed = result.passed
                            check_result.error_count = result.error_count
                            check_result.warning_count = result.warning_count
                            check_result.score = result.score
                            
                            for issue in result.issues:
                                issue_pb = check_result.issues.add()
                                issue_pb.file_path = issue.file_path
                                issue_pb.line = issue.line
                                issue_pb.column = issue.column
                                issue_pb.code = issue.code
                                issue_pb.severity = issue.severity
                                issue_pb.message = issue.message
                                issue_pb.category = issue.category
                        elif isinstance(result, dict):
                            check_result.passed = result.get('success', True)
                            check_result.score = result.get('score', 100)
                            
                            for issue in result.get('issues', []):
                                issue_pb = check_result.issues.add()
                                issue_pb.file_path = issue.get('file_path', file_path)
                                issue_pb.line = issue.get('line', 0)
                                issue_pb.column = issue.get('column', 0)
                                issue_pb.code = issue.get('code', '')
                                issue_pb.severity = issue.get('severity', 'info')
                                issue_pb.message = issue.get('message', '')
                                issue_pb.category = issue.get('category', 'general')
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.AnalyzeCodeResponse()
                response.success = False
                response.message = f"Error during analysis: {str(e)}"
                return response
        
        def CheckStyle(self, request, context):
            """Check code style with flake8."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                result = self.analyzer.check_flake8(
                    self.analyzer._write_code_to_file(code, file_path),
                    file_path
                )
                
                response = code_quality_pb2.CheckStyleResponse()
                response.success = True
                response.message = "Style check completed"
                response.score = result.score
                
                for issue in result.issues:
                    issue_pb = response.issues.add()
                    issue_pb.file_path = issue.file_path
                    issue_pb.line = issue.line
                    issue_pb.column = issue.column
                    issue_pb.code = issue.code
                    issue_pb.severity = issue.severity
                    issue_pb.message = issue.message
                    issue_pb.category = issue.category
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.CheckStyleResponse()
                response.success = False
                response.message = f"Error during style check: {str(e)}"
                return response
        
        def CheckTypes(self, request, context):
            """Check types with mypy."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                result = self.analyzer.check_mypy(
                    self.analyzer._write_code_to_file(code, file_path),
                    file_path
                )
                
                response = code_quality_pb2.CheckTypesResponse()
                response.success = True
                response.message = "Type check completed"
                response.score = result.score
                
                for issue in result.issues:
                    issue_pb = response.issues.add()
                    issue_pb.file_path = issue.file_path
                    issue_pb.line = issue.line
                    issue_pb.column = issue.column
                    issue_pb.code = issue.code
                    issue_pb.severity = issue.severity
                    issue_pb.message = issue.message
                    issue_pb.category = issue.category
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.CheckTypesResponse()
                response.success = False
                response.message = f"Error during type check: {str(e)}"
                return response
        
        def CheckQuality(self, request, context):
            """Check code quality with pylint."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                result = self.analyzer.check_pylint(
                    self.analyzer._write_code_to_file(code, file_path),
                    file_path
                )
                
                response = code_quality_pb2.CheckQualityResponse()
                response.success = True
                response.message = "Quality check completed"
                response.score = result.score
                
                for issue in result.issues:
                    issue_pb = response.issues.add()
                    issue_pb.file_path = issue.file_path
                    issue_pb.line = issue.line
                    issue_pb.column = issue.column
                    issue_pb.code = issue.code
                    issue_pb.severity = issue.severity
                    issue_pb.message = issue.message
                    issue_pb.category = issue.category
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.CheckQualityResponse()
                response.success = False
                response.message = f"Error during quality check: {str(e)}"
                return response
        
        def SecurityCheck(self, request, context):
            """Security check with bandit."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                result = self.analyzer.check_bandit(
                    self.analyzer._write_code_to_file(code, file_path),
                    file_path
                )
                
                response = code_quality_pb2.SecurityCheckResponse()
                response.success = True
                response.message = "Security check completed"
                response.score = result.score
                
                for issue in result.issues:
                    issue_pb = response.issues.add()
                    issue_pb.file_path = issue.file_path
                    issue_pb.line = issue.line
                    issue_pb.column = issue.column
                    issue_pb.code = issue.code
                    issue_pb.severity = issue.severity
                    issue_pb.message = issue.message
                    issue_pb.category = issue.category
                    
                    if issue.category == 'security':
                        response.security_issues.append(issue.message)
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.SecurityCheckResponse()
                response.success = False
                response.message = f"Error during security check: {str(e)}"
                return response
        
        def AnalyzeComplexity(self, request, context):
            """Analyze code complexity."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                result = self.analyzer.analyze_complexity(code, file_path)
                
                response = code_quality_pb2.AnalyzeComplexityResponse()
                response.success = result.get('success', True)
                response.message = result.get('message', 'Complexity analysis completed')
                response.average_complexity = result.get('average_complexity', 0)
                response.max_complexity = result.get('max_complexity', 0)
                response.score = result.get('score', 100)
                
                for func_name, func_data in result.get('functions', {}).items():
                    func_pb = response.functions[func_name]
                    func_pb.name = func_data.get('name', func_name)
                    func_pb.line = func_data.get('line', 0)
                    func_pb.cyclomatic_complexity = func_data.get('cyclomatic_complexity', 0)
                    func_pb.lines_of_code = func_data.get('lines_of_code', 0)
                    func_pb.parameters = func_data.get('parameters', 0)
                    func_pb.nesting_depth = func_data.get('nesting_depth', 0)
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.AnalyzeComplexityResponse()
                response.success = False
                response.message = f"Error during complexity analysis: {str(e)}"
                return response
        
        def DetectDuplication(self, request, context):
            """Detect code duplication."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                min_lines = request.min_lines if request.min_lines > 0 else 5
                
                result = self.analyzer.detect_duplication(code, file_path, min_lines)
                
                response = code_quality_pb2.DetectDuplicationResponse()
                response.success = result.get('success', True)
                response.message = result.get('message', 'Duplication detection completed')
                response.duplication_rate = result.get('duplication_rate', 0)
                response.score = result.get('score', 100)
                
                for dup in result.get('duplications', []):
                    dup_pb = response.duplications.add()
                    dup_pb.fragment1 = dup.get('fragment1', '')
                    dup_pb.fragment2 = dup.get('fragment2', '')
                    dup_pb.lines = dup.get('lines', 0)
                    dup_pb.start_line1.extend([dup.get('start_line1', 0)])
                    dup_pb.start_line2.extend([dup.get('start_line2', 0)])
                    dup_pb.similarity = dup.get('similarity', 0)
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.DetectDuplicationResponse()
                response.success = False
                response.message = f"Error during duplication detection: {str(e)}"
                return response
        
        def CollectMetrics(self, request, context):
            """Collect quality metrics."""
            try:
                code = request.code
                file_path = request.file_path or "unknown.py"
                
                metrics = self.metrics_collector.collect_file_metrics(file_path, code)
                
                response = code_quality_pb2.CollectMetricsResponse()
                response.success = True
                response.message = "Metrics collection completed"
                
                response.metrics.total_lines = metrics.total_lines
                response.metrics.code_lines = metrics.code_lines
                response.metrics.comment_lines = metrics.comment_lines
                response.metrics.blank_lines = metrics.blank_lines
                response.metrics.functions = metrics.functions
                response.metrics.classes = metrics.classes
                response.metrics.average_function_length = metrics.average_function_length
                response.metrics.maintainability_index = metrics.maintainability_index
                
                return response
                
            except Exception as e:
                response = code_quality_pb2.CollectMetricsResponse()
                response.success = False
                response.message = f"Error during metrics collection: {str(e)}"
                return response


def serve(port: int = 50051):
    """Start the gRPC server."""
    if not GRPC_AVAILABLE:
        print("Error: gRPC protobuf files not available. Cannot start server.")
        print("Please run: python main.py generate-proto")
        return False
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    code_quality_pb2_grpc.add_CodeQualityServiceServicer_to_server(
        CodeQualityServiceImpl(), server
    )
    server.add_insecure_port(f'[::]:{port}')
    print(f"Code Quality Service started on port {port}")
    server.start()
    server.wait_for_termination()
    return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Code Quality gRPC Server')
    parser.add_argument('--port', type=int, default=50051, help='Server port')
    args = parser.parse_args()
    
    serve(args.port)
