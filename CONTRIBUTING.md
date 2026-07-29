# Contributing to AIOps SRE Agent

Thank you for your interest in contributing! This document explains how to get started and what we expect from contributions.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if available
   ```
4. Run the test suite:
   ```bash
   pytest
   ```

## Code style

We use the following tools:

- `black` for formatting.
- `isort` for import sorting.
- `flake8` for linting.
- `mypy` for type checking.
- `bandit` for security scanning.
- `pytest` for tests.

Before committing, run:

```bash
python -m black .
python -m isort .
python -m flake8
python -m mypy
python -m bandit -r core api services
python -m pytest
```

## Pull request process

1. Create a feature branch from `main`.
2. Make focused changes with clear commit messages in English.
3. Add or update tests for new functionality.
4. Ensure CI checks pass.
5. Open a PR and link any related issue.

## Reporting issues

Use GitHub Issues with one of the provided templates (bug report or feature request).

## Code of conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).
