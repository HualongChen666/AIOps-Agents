"""
Code Quality Service - Main Entry Point
A microservice for comprehensive code quality analysis including:
- Style checking (flake8)
- Type checking (mypy)
- Quality checking (pylint)
- Security checking (bandit)
- Complexity analysis
- Duplication detection
- Metrics collection
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from grpc.server import serve
    GRPC_AVAILABLE = True
except ImportError:
    print("Warning: gRPC server not available. Install grpcio-tools to enable gRPC functionality.")
    GRPC_AVAILABLE = False

from code_analyzer import CodeAnalyzer
from quality_checker import QualityChecker
from metrics_collector import MetricsCollector


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_protobuf_files():
    """Generate protobuf files from .proto definition."""
    logger.info("Generating protobuf files...")
    
    proto_dir = os.path.join(os.path.dirname(__file__), 'proto')
    proto_file = os.path.join(proto_dir, 'code_quality.proto')
    
    if not os.path.exists(proto_file):
        logger.error(f"Proto file not found: {proto_file}")
        return False
    
    try:
        import grpc_tools.protoc
        cmd = [
            'grpc_tools.protoc',
            f'-I{proto_dir}',
            f'--python_out={proto_dir}',
            f'--grpc_python_out={proto_dir}',
            proto_file
        ]
        
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Protobuf files generated successfully")
            return True
        else:
            logger.error(f"Failed to generate protobuf files: {result.stderr}")
            return False
    except ImportError:
        logger.error("grpcio-tools not installed. Install with: pip install grpcio-tools")
        return False
    except Exception as e:
        logger.error(f"Error generating protobuf files: {e}")
        return False


def run_server(port: int = 50051):
    """Run the gRPC server."""
    if not GRPC_AVAILABLE:
        logger.error("gRPC server not available. Install grpcio-tools to enable gRPC functionality.")
        logger.error("Run: pip install grpcio grpcio-tools")
        logger.error("Then run: python main.py generate-proto")
        sys.exit(1)
    
    logger.info(f"Starting Code Quality Service on port {port}")
    
    # Check if protobuf files exist, generate if needed
    proto_dir = os.path.join(os.path.dirname(__file__), 'proto')
    pb2_file = os.path.join(proto_dir, 'code_quality_pb2.py')
    
    if not os.path.exists(pb2_file):
        logger.info("Protobuf files not found, generating...")
        if not generate_protobuf_files():
            logger.error("Failed to generate protobuf files. Please install grpcio-tools")
            sys.exit(1)
    
    try:
        serve(port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


def analyze_file(file_path: str, checkers: Optional[list] = None):
    """Analyze a single file directly (without gRPC)."""
    logger.info(f"Analyzing file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    analyzer = CodeAnalyzer()
    results = analyzer.analyze_code(code, file_path, checkers)
    
    # Print results
    print("\n" + "="*60)
    print(f"Code Analysis Results for: {file_path}")
    print("="*60)
    
    if 'summary' in results:
        summary = results['summary']
        print(f"\nOverall Score: {summary['overall_score']:.2f}/100")
        print(f"Total Issues: {summary['total_issues']}")
        print(f"  Critical: {summary['critical_issues']}")
        print(f"  Major: {summary['major_issues']}")
        print(f"  Minor: {summary['minor_issues']}")
        
        print("\nChecker Scores:")
        for checker, score in summary.get('checker_scores', {}).items():
            print(f"  {checker}: {score:.2f}/100")
    
    # Print detailed results for each checker
    for checker, result in results.items():
        if checker == 'summary':
            continue
        
        print(f"\n{checker.upper()} Results:")
        if hasattr(result, 'passed'):
            print(f"  Passed: {result.passed}")
            print(f"  Errors: {result.error_count}")
            print(f"  Warnings: {result.warning_count}")
            print(f"  Score: {result.score:.2f}/100")
            
            if result.issues:
                print(f"  Issues ({len(result.issues)}):")
                for issue in result.issues[:10]:  # Show first 10 issues
                    print(f"    Line {issue.line}: [{issue.code}] {issue.message}")
                if len(result.issues) > 10:
                    print(f"    ... and {len(result.issues) - 10} more")
        elif isinstance(result, dict):
            print(f"  Success: {result.get('success', True)}")
            print(f"  Score: {result.get('score', 100):.2f}/100")
            
            if 'issues' in result and result['issues']:
                print(f"  Issues ({len(result['issues'])}):")
                for issue in result['issues'][:10]:
                    print(f"    Line {issue.get('line', 0)}: [{issue.get('code', '')}] {issue.get('message', '')}")
    
    # Quality report
    print("\n" + "="*60)
    print("Quality Report")
    print("="*60)
    
    checker = QualityChecker()
    report = checker.check_quality(code, file_path, results)
    
    print(f"\nQuality Level: {report.quality_level.value.upper()}")
    print(f"Overall Score: {report.overall_score:.2f}/100")
    print(f"Total Issues: {report.total_issues}")
    
    if report.recommendations:
        print("\nRecommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
    
    print("\n" + "="*60)


def analyze_project(project_path: str, file_patterns: Optional[list] = None):
    """Analyze an entire project."""
    logger.info(f"Analyzing project: {project_path}")
    
    if not os.path.exists(project_path):
        logger.error(f"Project directory not found: {project_path}")
        return
    
    if file_patterns is None:
        file_patterns = ['*.py']
    
    collector = MetricsCollector()
    metrics = collector.collect_project_metrics(project_path, file_patterns)
    
    # Print project metrics
    print("\n" + "="*60)
    print(f"Project Metrics: {metrics.project_name}")
    print("="*60)
    
    print(f"\nTimestamp: {metrics.timestamp}")
    print(f"Total Files: {metrics.total_files}")
    print(f"Total Lines: {metrics.total_lines}")
    print(f"Code Lines: {metrics.total_code_lines}")
    print(f"Comment Lines: {metrics.total_comment_lines}")
    print(f"Total Functions: {metrics.total_functions}")
    print(f"Total Classes: {metrics.total_classes}")
    
    print(f"\nAverage Metrics:")
    print(f"  Maintainability Index: {metrics.average_maintainability_index:.2f}")
    print(f"  Cyclomatic Complexity: {metrics.average_complexity:.2f}")
    print(f"  Duplication Rate: {metrics.average_duplication_rate:.2%}")
    
    if metrics.category_breakdown:
        print(f"\nFile Distribution:")
        for category, count in metrics.category_breakdown.items():
            print(f"  {category}: {count} files")
    
    print("\n" + "="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Code Quality Service - Comprehensive code quality analysis'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Server command
    server_parser = subparsers.add_parser('server', help='Run gRPC server')
    server_parser.add_argument('--port', type=int, default=50051, 
                              help='Server port (default: 50051)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a file')
    analyze_parser.add_argument('file', help='File to analyze')
    analyze_parser.add_argument('--checkers', nargs='+', 
                               choices=['flake8', 'mypy', 'pylint', 'bandit', 'complexity', 'duplication'],
                               help='Checkers to use')
    
    # Project command
    project_parser = subparsers.add_parser('project', help='Analyze a project')
    project_parser.add_argument('path', help='Project directory to analyze')
    project_parser.add_argument('--patterns', nargs='+', default=['*.py'],
                              help='File patterns to include (default: *.py)')
    
    # Generate proto command
    proto_parser = subparsers.add_parser('generate-proto', help='Generate protobuf files')
    
    args = parser.parse_args()
    
    if args.command == 'server':
        run_server(args.port)
    elif args.command == 'analyze':
        analyze_file(args.file, args.checkers)
    elif args.command == 'project':
        analyze_project(args.path, args.patterns)
    elif args.command == 'generate-proto':
        generate_protobuf_files()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
