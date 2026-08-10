# AIOps Agent Contributing Guide

Thank you for your interest in contributing to AIOps Agent! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Assume good intentions
- Respect different viewpoints and experiences

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/AIOps_Agent.git
cd AIOps_Agent
```

### 2. Set Up Development Environment

```bash
python -m venv venv
source venv/bin/activate # Linux/Mac
# or
venv\Scripts\activate # Windows

pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run Tests

```bash
pytest
```

### 5. Start Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Write code following the coding standards
- Add tests for new functionality
- Update documentation
- Run tests locally

### 3. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
# or
git commit -m "fix: resolve issue with X"
```

Use conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance tasks

### 4. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:
- Clear description of changes
- Reference related issues
- Screenshots if applicable
- Test results

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Maximum line length: 100 characters
- Use type hints
- Write docstrings (Google style)

### Code Formatting

```bash
# Format code
python -m black .

# Sort imports
python -m isort .

# Type checking
python -m mypy .

# Linting
python -m flake8 .
```

### Code Quality

- Write self-documenting code
- Keep functions focused and small
- Use meaningful variable names
- Add comments for complex logic
- Avoid code duplication

### Security

- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user inputs
- Follow security best practices

## Testing

### Test Structure

```
tests/
├── unit/ # Unit tests
├── integration/ # Integration tests
├── e2e/ # End-to-end tests
└── fixtures/ # Test fixtures
```

### Writing Tests

```python
import pytest
from your_module import your_function

def test_your_function():
 # Arrange
 input_data = {...}
 
 # Act
 result = your_function(input_data)
 
 # Assert
 assert result == expected
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_module.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/unit/test_module.py::test_function
```

### Test Coverage

- Aim for ≥80% coverage
- Write tests for critical paths
- Test edge cases and error conditions
- Mock external dependencies

## Documentation

### Code Documentation

- Add docstrings to all functions and classes
- Use Google style docstrings
- Document parameters and return values
- Include usage examples

### API Documentation

- Add response examples to all endpoints
- Document error responses
- Update OpenAPI schema
- Keep Swagger UI current

### Project Documentation

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for structural changes
- Update DEPLOYMENT.md for deployment changes
- Add inline comments for complex logic

## Pull Request Process

### Before Submitting

1. **Code Quality**
 - Run formatting tools: `black`, `isort`
 - Run linting: `flake8`
 - Run type checking: `mypy`
 - Run tests: `pytest`

2. **Documentation**
 - Update relevant documentation
 - Add docstrings to new code
 - Update API documentation

3. **Testing**
 - Add tests for new features
 - Ensure all tests pass
 - Check test coverage

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] No merge conflicts
- [ ] Commit messages follow convention

### Review Process

1. Automated checks run on all PRs
2. Maintainers review code changes
3. Address review feedback
4. Update PR based on feedback
5. Approval and merge

## Getting Help

### Documentation

- [API Quick Start](./API_QUICKSTART.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Architecture](./ARCHITECTURE.md)

### Communication

- GitHub Issues: Report bugs and request features
- GitHub Discussions: Ask questions and share ideas
- Pull Requests: Submit code changes

### Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to AIOps Agent!
