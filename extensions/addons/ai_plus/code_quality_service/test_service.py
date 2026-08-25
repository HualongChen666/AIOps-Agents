"""
Test script for Code Quality Service
Tests the core functionality without requiring gRPC server.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_analyzer import CodeAnalyzer
from quality_checker import QualityChecker
from metrics_collector import MetricsCollector


def test_code_analyzer():
    """Test the CodeAnalyzer class."""
    print("="*60)
    print("Testing CodeAnalyzer")
    print("="*60)
    
    # Test code with various issues
    test_code = '''
def hello():
    x=1+2
    y=3+4
    if x>0:
        print(y)
    return x

def complex_function(a,b,c,d,e,f):
    if a>0:
        if b>0:
            if c>0:
                if d>0:
                    if e>0:
                        return f
    return 0

# Duplicate code
def func1():
    x=1+2
    y=3+4
    return x+y

def func2():
    x=1+2
    y=3+4
    return x+y
'''
    
    analyzer = CodeAnalyzer()
    results = analyzer.analyze_code(test_code, "test.py")
    
    print(f"\nAnalysis completed successfully")
    print(f"Summary: {results.get('summary', {})}")
    
    for checker, result in results.items():
        if checker == 'summary':
            continue
        print(f"\n{checker}:")
        if hasattr(result, 'score'):
            print(f"  Score: {result.score}")
            print(f"  Issues: {len(result.issues)}")
        elif isinstance(result, dict):
            print(f"  Score: {result.get('score')}")
            print(f"  Issues: {len(result.get('issues', []))}")
    
    print("\nCodeAnalyzer test PASSED\n")
    return True


def test_quality_checker():
    """Test the QualityChecker class."""
    print("="*60)
    print("Testing QualityChecker")
    print("="*60)
    
    test_code = '''
def calculate(a: int, b: int) -> int:
    """Calculate sum of two numbers."""
    return a + b

class Calculator:
    def __init__(self):
        self.value = 0
    
    def add(self, x):
        self.value += x
        return self.value
'''
    
    checker = QualityChecker()
    report = checker.check_quality(test_code, "test.py")
    
    print(f"\nQuality Report:")
    print(f"  File: {report.file_path}")
    print(f"  Overall Score: {report.overall_score:.2f}")
    print(f"  Quality Level: {report.quality_level.value}")
    print(f"  Total Issues: {report.total_issues}")
    print(f"  Critical: {report.critical_issues}")
    print(f"  Major: {report.major_issues}")
    print(f"  Minor: {report.minor_issues}")
    
    print(f"\nCategory Scores:")
    for category, score in report.category_scores.items():
        print(f"  {category}: {score:.2f}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")
    
    print(f"\nMetrics:")
    for key, value in report.metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\nQualityChecker test PASSED\n")
    return True


def test_metrics_collector():
    """Test the MetricsCollector class."""
    print("="*60)
    print("Testing MetricsCollector")
    print("="*60)
    
    test_code = '''
# This is a comment
def function1():
    """Function 1 docstring."""
    return 1

def function2():
    """Function 2 docstring."""
    return 2

class MyClass:
    def method(self):
        return 3
'''
    
    collector = MetricsCollector()
    metrics = collector.collect_file_metrics("test.py", test_code)
    
    print(f"\nFile Metrics:")
    print(f"  File: {metrics.file_path}")
    print(f"  Total Lines: {metrics.total_lines}")
    print(f"  Code Lines: {metrics.code_lines}")
    print(f"  Comment Lines: {metrics.comment_lines}")
    print(f"  Blank Lines: {metrics.blank_lines}")
    print(f"  Functions: {metrics.functions}")
    print(f"  Classes: {metrics.classes}")
    print(f"  Avg Function Length: {metrics.average_function_length:.2f}")
    print(f"  Maintainability Index: {metrics.maintainability_index:.2f}")
    print(f"  Cyclomatic Complexity: {metrics.cyclomatic_complexity:.2f}")
    print(f"  Duplication Rate: {metrics.duplication_rate:.2%}")
    
    print("\nMetricsCollector test PASSED\n")
    return True


def test_integration():
    """Test integration of all components."""
    print("="*60)
    print("Testing Integration")
    print("="*60)
    
    test_code = '''
import os

def process_data(data: list) -> dict:
    """Process input data and return results."""
    results = {}
    for item in data:
        if item:
            results[item] = len(item)
    return results

class DataProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.cache = {}
    
    def process(self, data):
        if not data:
            return None
        return self.process_data(data)
    
    def process_data(self, data):
        return process_data(data)
'''
    
    # Use all components together
    analyzer = CodeAnalyzer()
    checker = QualityChecker()
    collector = MetricsCollector()
    
    # Analyze code
    analysis_results = analyzer.analyze_code(test_code, "integration_test.py")
    
    # Generate quality report
    quality_report = checker.check_quality(test_code, "integration_test.py", analysis_results)
    
    # Collect metrics
    metrics = collector.collect_file_metrics("integration_test.py", test_code)
    
    print(f"\nIntegration Test Results:")
    print(f"  Analysis Checkers: {len(analysis_results)}")
    print(f"  Quality Score: {quality_report.overall_score:.2f}")
    print(f"  Quality Level: {quality_report.quality_level.value}")
    print(f"  Total Issues: {quality_report.total_issues}")
    print(f"  Maintainability Index: {metrics.maintainability_index:.2f}")
    
    print("\nIntegration test PASSED\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Code Quality Service - Test Suite")
    print("="*60 + "\n")
    
    tests = [
        ("CodeAnalyzer", test_code_analyzer),
        ("QualityChecker", test_quality_checker),
        ("MetricsCollector", test_metrics_collector),
        ("Integration", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"{test_name} test FAILED\n")
        except Exception as e:
            failed += 1
            print(f"{test_name} test FAILED with exception: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
