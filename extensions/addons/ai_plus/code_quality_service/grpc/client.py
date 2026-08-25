"""
gRPC Client for Code Quality Service
Provides client methods to interact with the CodeQualityService gRPC server.
"""

import grpc
import os
import sys
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import generated protobuf classes
try:
    from proto import code_quality_pb2
    from proto import code_quality_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    print("Warning: gRPC protobuf files not available. gRPC client functionality disabled.")
    print("To enable gRPC, install grpcio-tools and run: python main.py generate-proto")
    GRPC_AVAILABLE = False
    code_quality_pb2 = None
    code_quality_pb2_grpc = None


class CodeQualityClient:
    """Client for the Code Quality gRPC service."""
    
    def __init__(self, host: str = 'localhost', port: int = 50051):
        """
        Initialize the client.
        
        Args:
            host: Server host address
            port: Server port
        """
        if not GRPC_AVAILABLE:
            raise RuntimeError("gRPC not available. Install grpcio-tools and generate protobuf files.")
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = code_quality_pb2_grpc.CodeQualityServiceStub(self.channel)
    
    def close(self):
        """Close the client connection."""
        self.channel.close()
    
    def analyze_code(self, code: str, file_path: str = "unknown.py",
                     checkers: List[str] = None) -> Dict:
        """
        Analyze code quality using multiple checkers.
        
        Args:
            code: Source code to analyze
            file_path: Original file path for reporting
            checkers: List of checkers to use (flake8, mypy, pylint, bandit, complexity, duplication)
        
        Returns:
            Dictionary containing analysis results
        """
        if checkers is None:
            checkers = ['flake8', 'mypy', 'pylint', 'bandit', 'complexity', 'duplication']
        
        request = code_quality_pb2.AnalyzeCodeRequest(
            file_path=file_path,
            code=code,
            checkers=checkers
        )
        
        response = self.stub.AnalyzeCode(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'results': self._parse_check_results(response.results),
            'summary': {
                'overall_score': response.summary.overall_score,
                'total_issues': response.summary.total_issues,
                'critical_issues': response.summary.critical_issues,
                'major_issues': response.summary.major_issues,
                'minor_issues': response.summary.minor_issues,
                'checker_scores': dict(response.summary.checker_scores)
            }
        }
    
    def check_style(self, code: str, file_path: str = "unknown.py",
                    config: Dict[str, str] = None) -> Dict:
        """
        Check code style with flake8.
        
        Args:
            code: Source code to check
            file_path: Original file path for reporting
            config: Configuration options
        
        Returns:
            Dictionary containing style check results
        """
        if config is None:
            config = {}
        
        request = code_quality_pb2.CheckStyleRequest(
            file_path=file_path,
            code=code,
            config=config
        )
        
        response = self.stub.CheckStyle(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'issues': [self._parse_issue(issue) for issue in response.issues],
            'score': response.score
        }
    
    def check_types(self, code: str, file_path: str = "unknown.py",
                    config: Dict[str, str] = None) -> Dict:
        """
        Check types with mypy.
        
        Args:
            code: Source code to check
            file_path: Original file path for reporting
            config: Configuration options
        
        Returns:
            Dictionary containing type check results
        """
        if config is None:
            config = {}
        
        request = code_quality_pb2.CheckTypesRequest(
            file_path=file_path,
            code=code,
            config=config
        )
        
        response = self.stub.CheckTypes(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'issues': [self._parse_issue(issue) for issue in response.issues],
            'score': response.score
        }
    
    def check_quality(self, code: str, file_path: str = "unknown.py",
                      config: Dict[str, str] = None) -> Dict:
        """
        Check code quality with pylint.
        
        Args:
            code: Source code to check
            file_path: Original file path for reporting
            config: Configuration options
        
        Returns:
            Dictionary containing quality check results
        """
        if config is None:
            config = {}
        
        request = code_quality_pb2.CheckQualityRequest(
            file_path=file_path,
            code=code,
            config=config
        )
        
        response = self.stub.CheckQuality(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'issues': [self._parse_issue(issue) for issue in response.issues],
            'score': response.score,
            'category_scores': dict(response.category_scores)
        }
    
    def security_check(self, code: str, file_path: str = "unknown.py",
                       config: Dict[str, str] = None) -> Dict:
        """
        Perform security check with bandit.
        
        Args:
            code: Source code to check
            file_path: Original file path for reporting
            config: Configuration options
        
        Returns:
            Dictionary containing security check results
        """
        if config is None:
            config = {}
        
        request = code_quality_pb2.SecurityCheckRequest(
            file_path=file_path,
            code=code,
            config=config
        )
        
        response = self.stub.SecurityCheck(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'issues': [self._parse_issue(issue) for issue in response.issues],
            'score': response.score,
            'security_issues': list(response.security_issues)
        }
    
    def analyze_complexity(self, code: str, file_path: str = "unknown.py") -> Dict:
        """
        Analyze code complexity.
        
        Args:
            code: Source code to analyze
            file_path: Original file path for reporting
        
        Returns:
            Dictionary containing complexity analysis results
        """
        request = code_quality_pb2.AnalyzeComplexityRequest(
            file_path=file_path,
            code=code
        )
        
        response = self.stub.AnalyzeComplexity(request)
        
        functions = {}
        for func_name, func_data in response.functions.items():
            functions[func_name] = {
                'name': func_data.name,
                'line': func_data.line,
                'cyclomatic_complexity': func_data.cyclomatic_complexity,
                'lines_of_code': func_data.lines_of_code,
                'parameters': func_data.parameters,
                'nesting_depth': func_data.nesting_depth
            }
        
        return {
            'success': response.success,
            'message': response.message,
            'functions': functions,
            'average_complexity': response.average_complexity,
            'max_complexity': response.max_complexity,
            'score': response.score
        }
    
    def detect_duplication(self, code: str, file_path: str = "unknown.py",
                           min_lines: int = 5) -> Dict:
        """
        Detect code duplication.
        
        Args:
            code: Source code to analyze
            file_path: Original file path for reporting
            min_lines: Minimum lines for duplication detection
        
        Returns:
            Dictionary containing duplication detection results
        """
        request = code_quality_pb2.DetectDuplicationRequest(
            file_path=file_path,
            code=code,
            min_lines=min_lines
        )
        
        response = self.stub.DetectDuplication(request)
        
        duplications = []
        for dup in response.duplications:
            duplications.append({
                'fragment1': dup.fragment1,
                'fragment2': dup.fragment2,
                'lines': dup.lines,
                'start_line1': list(dup.start_line1),
                'start_line2': list(dup.start_line2),
                'similarity': dup.similarity
            })
        
        return {
            'success': response.success,
            'message': response.message,
            'duplications': duplications,
            'duplication_rate': response.duplication_rate,
            'score': response.score
        }
    
    def collect_metrics(self, code: str, file_path: str = "unknown.py") -> Dict:
        """
        Collect quality metrics.
        
        Args:
            code: Source code to analyze
            file_path: Original file path for reporting
        
        Returns:
            Dictionary containing code metrics
        """
        request = code_quality_pb2.CollectMetricsRequest(
            file_path=file_path,
            code=code
        )
        
        response = self.stub.CollectMetrics(request)
        
        return {
            'success': response.success,
            'message': response.message,
            'metrics': {
                'total_lines': response.metrics.total_lines,
                'code_lines': response.metrics.code_lines,
                'comment_lines': response.metrics.comment_lines,
                'blank_lines': response.metrics.blank_lines,
                'functions': response.metrics.functions,
                'classes': response.metrics.classes,
                'average_function_length': response.metrics.average_function_length,
                'maintainability_index': response.metrics.maintainability_index
            }
        }
    
    def _parse_issue(self, issue) -> Dict:
        """Parse an issue protobuf message to dictionary."""
        return {
            'file_path': issue.file_path,
            'line': issue.line,
            'column': issue.column,
            'code': issue.code,
            'severity': issue.severity,
            'message': issue.message,
            'category': issue.category
        }
    
    def _parse_check_results(self, results) -> Dict:
        """Parse check results protobuf message to dictionary."""
        parsed = {}
        for checker_name, result in results.items():
            parsed[checker_name] = {
                'passed': result.passed,
                'error_count': result.error_count,
                'warning_count': result.warning_count,
                'score': result.score,
                'issues': [self._parse_issue(issue) for issue in result.issues]
            }
        return parsed


# Context manager for automatic connection cleanup
class CodeQualityClientContext:
    """Context manager for CodeQualityClient."""
    
    def __init__(self, host: str = 'localhost', port: int = 50051):
        self.host = host
        self.port = port
        self.client = None
    
    def __enter__(self):
        self.client = CodeQualityClient(self.host, self.port)
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()


if __name__ == '__main__':
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Code Quality gRPC Client')
    parser.add_argument('--host', type=str, default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=50051, help='Server port')
    parser.add_argument('--file', type=str, help='File to analyze')
    parser.add_argument('--code', type=str, help='Code to analyze')
    parser.add_argument('--checkers', type=str, nargs='+', 
                       help='Checkers to use (flake8, mypy, pylint, bandit, complexity, duplication)')
    
    args = parser.parse_args()
    
    # Get code to analyze
    if args.file:
        with open(args.file, 'r') as f:
            code = f.read()
        file_path = args.file
    elif args.code:
        code = args.code
        file_path = "inline_code.py"
    else:
        print("Error: Either --file or --code must be provided")
        sys.exit(1)
    
    # Perform analysis
    with CodeQualityClientContext(args.host, args.port) as client:
        result = client.analyze_code(code, file_path, args.checkers)
        
        print(f"Analysis Result: {result['message']}")
        print(f"Success: {result['success']}")
        print(f"Overall Score: {result['summary']['overall_score']:.2f}")
        print(f"Total Issues: {result['summary']['total_issues']}")
        print(f"Critical Issues: {result['summary']['critical_issues']}")
        print(f"Major Issues: {result['summary']['major_issues']}")
        print(f"Minor Issues: {result['summary']['minor_issues']}")
        print("\nChecker Scores:")
        for checker, score in result['summary']['checker_scores'].items():
            print(f"  {checker}: {score:.2f}")
