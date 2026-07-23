---
name: testing-debugging
description: Automated testing, debugging, and quality assurance
argument-hint: "[test_file]"
allowed-tools:
  - read_file
  - write_to_file
  - edit
  - multi_edit
  - grep_search
  - find_by_name
  - bash
  - command_status
  - todo_list
  - skill
  - list_resources
  - read_resource
  - search_web
  - read_url_content
triggers:
  - user
  - model
subagent: false
priority: high
auto-apply:
  - "编写测试"
  - "调试代码"
  - "运行测试"
  - "测试失败"
  - "调试错误"
  - "性能测试"
  - "测试覆盖率"
file-patterns:
  - "tests/**/*.py"
  - "test_*.py"
  - "**/test_*.py"
  - "**/conftest.py"
keywords:
  - "测试"
  - "test"
  - "调试"
  - "debug"
  - "错误"
  - "error"
  - "失败"
  - "fail"
  - "coverage"
  - "性能"
---

# Testing and Debugging Skill

## Purpose
Automated testing, debugging, and quality assurance for the AIOps Agent project.

## Auto-approved Tools
- read
- write
- edit
- grep
- find_file_by_name
- exec

## Skill Instructions

### Testing Standards

#### Test Structure
```
tests/
├── unit/              # Unit tests
├── integration/       # Integration tests
├── e2e/              # End-to-end tests
└── conftest.py       # Shared fixtures
```

#### Test Template
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_your_function():
    """Test description."""
    # Arrange
    test_data = {"key": "value"}
    
    # Act
    result = your_function(test_data)
    
    # Assert
    assert result == expected_value

@pytest.mark.asyncio
async def test_api_endpoint(client: AsyncClient, db: AsyncSession):
    """Test API endpoint."""
    response = await client.get("/api/endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

### Pytest Configuration

#### Markers
```python
# conftest.py
pytest.mark.unit: Unit tests
pytest.mark.integration: Integration tests
pytest.mark.e2e: End-to-end tests
pytest.mark.slow: Slow-running tests
pytest.mark.asyncio: Async tests
```

#### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_module.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific markers
pytest -m unit

# Run in parallel
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run failed tests only
pytest --lf
```

### Async Testing

#### Async Test Patterns
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None

@pytest.mark.asyncio
async def test_api_with_auth(client: AsyncClient, auth_headers: dict):
    """Test API with authentication."""
    response = await client.get(
        "/api/protected",
        headers=auth_headers
    )
    assert response.status_code == 200
```

### Fixtures

#### Common Fixtures
```python
# conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from main import app
from aiops_core.database import get_db, Base

@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def db_session():
    """Database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
```

### Mocking

#### Mock Patterns
```python
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
@patch('core.external_api.call_external_service')
async def test_with_mock(mock_external_call):
    """Test with mocked external service."""
    mock_external_call.return_value = {"data": "test"}
    result = await function_using_external_api()
    assert result == "test"
    mock_external_call.assert_called_once()

@pytest.mark.asyncio
@patch('core.database.get_db')
async def test_database_mock(mock_get_db):
    """Test with mocked database."""
    mock_db = AsyncMock()
    mock_get_db.return_value = mock_db
    # Test logic here
```

### Debugging Strategies

#### Logging Debug
```python
from loguru import logger

# Add debug logging
logger.debug(f"Variable value: {variable}")
logger.info(f"Function called with args: {args}")
logger.error(f"Error occurred: {error}")

# View logs during test
pytest -s -v test_file.py
```

#### Breakpoint Debugging
```python
# Add breakpoint for debugging
import pdb; pdb.set_trace()

# Or use ipdb (if installed)
import ipdb; ipdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

#### Print Debugging
```python
# Quick debugging
print(f"DEBUG: {variable}")
print(f"Type: {type(variable)}")
print(f"Dir: {dir(variable)}")
```

### Error Analysis

#### Common Error Patterns
```python
# AttributeError
# Check object attributes
print(dir(object))

# TypeError
# Check argument types
print(f"Expected type: {expected_type}, got: {type(actual)}")

# ImportError
# Check Python path
import sys
print(sys.path)

# Database errors
# Check SQL queries
# Verify connection strings
# Check table existence
```

### Performance Testing

#### Profiling
```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Function to profile
    result = your_function()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

#### Benchmarking
```python
import time

def benchmark_function():
    start = time.time()
    for _ in range(1000):
        your_function()
    end = time.time()
    print(f"Average time: {(end - start) / 1000:.4f}s")
```

### Coverage Analysis

#### Coverage Configuration
```bash
# Generate coverage report
pytest --cov=. --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Coverage thresholds
# pyproject.toml
[tool.coverage.run]
source = ["."]
omit = ["tests/*", "venv/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

### Integration Testing

#### Database Integration Tests
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_integration(db_session: AsyncSession):
    """Test database integration."""
    # Create test data
    test_object = YourModel(name="test")
    db_session.add(test_object)
    await db_session.commit()
    
    # Query and verify
    result = await db_session.execute(select(YourModel))
    objects = result.scalars().all()
    assert len(objects) == 1
    assert objects[0].name == "test"
```

#### API Integration Tests
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_integration(client: AsyncClient):
    """Test API integration."""
    # Test full flow
    response = await client.post("/api/resource", json={"name": "test"})
    assert response.status_code == 201
    
    resource_id = response.json()["id"]
    response = await client.get(f"/api/resource/{resource_id}")
    assert response.status_code == 200
```

### E2E Testing

#### Playwright E2E Tests
```python
from playwright.async_api import async_playwright

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_user_flow():
    """Test end-to-end user flow."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto("http://localhost:8000")
        await page.click("text=Login")
        await page.fill("input[name='username']", "testuser")
        await page.fill("input[name='password']", "password")
        await page.click("button[type='submit']")
        
        assert await page.inner_text("text=Welcome") == "Welcome"
        
        await browser.close()
```

### Debugging Checklist

When debugging issues:

1. **Reproduce the issue**
   - Can you reproduce it consistently?
   - What are the exact steps?
   - What is the expected vs actual behavior?

2. **Check logs**
   - Application logs
   - Database logs
   - System logs
   - Error messages

3. **Isolate the problem**
   - Create minimal reproduction case
   - Test components individually
   - Use binary search debugging

4. **Verify assumptions**
   - Check data types
   - Verify function signatures
   - Confirm configuration values

5. **Use debugging tools**
   - Breakpoints
   - Logging
   - Print statements
   - Profilers

6. **Fix and test**
   - Implement fix
   - Write regression test
   - Verify no side effects
   - Update documentation

### Quality Gates

#### Pre-commit Checks
```bash
# Run all quality checks
black . --check
flake8 .
mypy .
bandit -r .
pytest --cov=. --cov-fail-under=80
```

#### CI/CD Integration
```yaml
# Example GitHub Actions
- name: Run tests
  run: pytest --cov=. --cov-report=xml

- name: Type check
  run: mypy .

- name: Lint
  run: flake8 .

- name: Security check
  run: bandit -r .
```

## When to Invoke
Invoke this skill automatically when:
- Writing new tests
- Debugging failing tests
- Investigating bugs
- Performance issues
- Code quality checks
- Setting up CI/CD pipelines
- Writing integration/E2E tests

## GitLab 上传权限控制

### 项目配置
- **项目目录**: `C:\AIOps_Agent_bak`
- **GitLab项目**: `Hualong_Chen/neurosync-agent-tool-platform`
- **上传控制**: 严格启用，需要明确用户指令

### 上传权限规则
- ❌ **禁止**: 未经用户明确指令的任何GitLab上传操作
- ✅ **允许**: 仅在用户明确给出上传指令时执行上传
- **上传指令格式**: "将某一个目录(含目录中的子目录和文件)或者某一个/几个文件(具体文件名)上传到我的gitlab中"

### 测试安全检查
在执行任何可能涉及GitLab操作时：
1. 验证是否为只读操作（搜索、查看等）
2. 如果是写入操作，检查是否有明确的上传指令
3. 确认操作不会违反上传控制规则
4. 记录所有GitLab相关操作

## Project-Specific Context
This project uses:
- pytest with async support
- pytest-cov for coverage
- pytest-xdist for parallel testing
- pytest-mock for mocking
- Playwright for E2E testing
- Coverage target: 80%+
- Pre-commit hooks for quality checks