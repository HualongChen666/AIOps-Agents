# Code Quality Service

A comprehensive microservice for code quality analysis that provides multiple checking capabilities through a gRPC interface.

## Features

- **Style Checking**: Flake8 integration for PEP 8 style compliance
- **Type Checking**: MyPy integration for static type checking
- **Quality Checking**: Pylint integration for code quality analysis
- **Security Checking**: Bandit integration for security vulnerability detection
- **Complexity Analysis**: Cyclomatic complexity and nesting depth analysis
- **Duplication Detection**: Code duplication detection using token-based analysis
- **Metrics Collection**: Comprehensive code metrics including maintainability index

## Installation

```bash
cd extensions/addons/ai_plus/code_quality_service
pip install -r requirements.txt
```

## Usage

### Starting the gRPC Server

```bash
python main.py server --port 50051
```

### Analyzing a File Directly

```bash
python main.py analyze path/to/file.py
```

### Analyzing a Project

```bash
python main.py project path/to/project
```

### Generating Protobuf Files

```bash
python main.py generate-proto
```

## gRPC API

### AnalyzeCode

Perform comprehensive code analysis using multiple checkers.

```python
client.analyze_code(code, file_path, checkers)
```

### CheckStyle

Check code style with flake8.

```python
client.check_style(code, file_path, config)
```

### CheckTypes

Check type annotations with mypy.

```python
client.check_types(code, file_path, config)
```

### CheckQuality

Check code quality with pylint.

```python
client.check_quality(code, file_path, config)
```

### SecurityCheck

Perform security analysis with bandit.

```python
client.security_check(code, file_path, config)
```

### AnalyzeComplexity

Analyze code complexity.

```python
client.analyze_complexity(code, file_path)
```

### DetectDuplication

Detect code duplication.

```python
client.detect_duplication(code, file_path, min_lines)
```

### CollectMetrics

Collect code metrics.

```python
client.collect_metrics(code, file_path)
```

## Architecture

```
code_quality_service/
├── main.py                 # Service entry point
├── code_analyzer.py        # Core code analysis logic
├── quality_checker.py      # Quality assessment logic
├── metrics_collector.py    # Metrics collection logic
├── proto/
│   └── code_quality.proto  # gRPC service definition
├── grpc/
│   ├── server.py          # gRPC server implementation
│   └── client.py          # gRPC client implementation
├── requirements.txt        # Python dependencies
└── README.md             # This file
```

## Fallback Implementations

The service includes fallback implementations for all code quality tools:
- If flake8 is not installed, basic style checks are performed
- If mypy is not installed, basic type annotation checks are performed
- If pylint is not installed, basic quality checks are performed
- If bandit is not installed, basic security pattern checks are performed

This ensures the service remains functional even without external tool dependencies.

## Quality Scoring

The service provides comprehensive quality scoring:
- **Overall Score**: Weighted average of all checker scores
- **Category Scores**: Individual scores for each checker
- **Quality Level**: EXCELLENT, GOOD, FAIR, POOR, or CRITICAL
- **Issue Classification**: Critical, Major, and Minor issues

## Example Usage

```python
from code_quality_service import CodeAnalyzer, QualityChecker

# Analyze code
analyzer = CodeAnalyzer()
results = analyzer.analyze_code(code, "example.py")

# Generate quality report
checker = QualityChecker()
report = checker.check_quality(code, "example.py", results)

print(f"Quality Level: {report.quality_level}")
print(f"Overall Score: {report.overall_score}")
```

## License

Internal use only.
