# Makefile for AIOps Agent Testing
# Provides convenient commands for test validation and CI/CD integration

.PHONY: help test-collection validate-tests clean-cache install-deps run-tests

help:
	@echo "AIOps Agent Testing Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  test-collection   - Run pytest collection validation"
	@echo "  validate-tests     - Run comprehensive test validation"
	@echo "  clean-cache        - Clean Python cache files"
	@echo "  install-deps       - Install project dependencies"
	@echo "  run-tests          - Run all tests"
	@echo "  help              - Show this help message"

test-collection:
	@echo "Running pytest collection validation..."
	python -m pytest --collect-only --tb=line
	@echo "✅ Test collection completed"

validate-tests:
	@echo "Running comprehensive test validation..."
	python scripts/validate_test_collection.py --min-tests 2000 --report test-validation-report.txt
	@echo "✅ Test validation completed"
	@echo "Report saved to: test-validation-report.txt"

clean-cache:
	@echo "Cleaning Python cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true
	find . -type f -name "*.pyo" -delete || true
	@echo "✅ Cache cleaned"

install-deps:
	@echo "Installing project dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

run-tests:
	@echo "Running core/api/infrastructure tests with isolation..."
	python scripts/run_core_api_infrastructure_tests.py -v --tb=short
	@echo "✅ Core/API/Infrastructure tests completed"

run-performance-tests:
	@echo "Running performance tests separately (no xdist, no coverage)..."
	python scripts/run_performance_tests.py -v --tb=short
	@echo "✅ Performance tests completed"

ci-validation:
	@echo "Running CI/CD validation..."
	$(MAKE) clean-cache
	$(MAKE) install-deps
	$(MAKE) validate-tests
	@echo "✅ CI/CD validation completed"

setup-pre-commit:
	@echo "Setting up pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Pre-commit hooks installed"

check-imports:
	@echo "Checking for import errors..."
	python -c "
import sys
import subprocess
import os

sys.path.insert(0, '.')

# Find all test files
test_files = []
for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.startswith('test_') and file.endswith('.py'):
            test_files.append(os.path.join(root, file))

import_errors = []
for test_file in test_files:
    try:
        with open(test_file, 'r') as f:
            compile(f.read(), test_file, 'exec')
    except SyntaxError as e:
        import_errors.append(f'{test_file}: {e}')
    except Exception as e:
        import_errors.append(f'{test_file}: {e}')

print(f'Total test files: {len(test_files)}')
print(f'Errors found: {len(import_errors)}')
if import_errors:
    print('Errors:')
    for error in import_errors:
        print(f'  {error}')
    sys.exit(1)
else:
    print('✅ No import errors found'
"
	@echo "✅ Import check completed"

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	$(MAKE) install-deps
	$(MAKE) setup-pre-commit
	@echo "✅ Development environment setup completed"

dev-test:
	@echo "Running development test suite..."
	python -m pytest tests/unit/ tests/integration/ -v --tb=short
	@echo "✅ Development tests completed"

# Quality gates
quality-gate:
	@echo "Running quality gate validation..."
	$(MAKE) check-imports
	$(MAKE) test-collection
	python -m black --check .
	python -m isort --check-only .
	python -m flake8 .
	@echo "✅ Quality gate validation completed"