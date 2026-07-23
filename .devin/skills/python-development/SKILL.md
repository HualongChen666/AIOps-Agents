---
name: python-development
description: Python development best practices and code quality automation
argument-hint: "[task]"
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
  - "编辑 .py 文件"
  - "创建 Python 函数"
  - "定义 Python 类"
  - "Python 代码重构"
  - "添加类型提示"
  - "Python 性能优化"
file-patterns:
  - "**/*.py"
  - "**/requirements*.txt"
  - "**/pyproject.toml"
  - "**/setup.py"
excluded-patterns:
  - "**/venv/**"
  - "**/__pycache__/**"
  - "**/*.egg-info/**"
---

# Python Development Skill

## Purpose
Enhance Python development efficiency with intelligent code analysis, quality checks, and best practices enforcement.

## Auto-approved Tools
- read
- write
- edit
- grep
- find_file_by_name
- exec

## Skill Instructions

When working on Python code in this project:

### Code Quality Standards
- Follow PEP 8 style guidelines (project uses black with 100 character line length)
- Use type hints where appropriate (project uses mypy)
- Write docstrings for all public functions and classes
- Ensure code passes flake8 linting
- Maintain test coverage above 80%

### Project-Specific Conventions
- Use FastAPI for all API endpoints
- Use SQLAlchemy 2.0 with async support
- Use Pydantic v2 for data validation
- Use pydantic-settings for configuration management
- Follow the existing router structure in `api/` directory
- Use Alembic for database migrations

### Automatic Quality Checks
Before considering Python code changes complete, automatically:

1. **Run type checking**: `python -m mypy .`
2. **Run linting**: `python -m flake8 .`
3. **Run security checks**: `bandit -r .`
4. **Run formatting check**: `python -m black --check .`
5. **Run import sorting**: `python -m isort --check-only .`

### Code Review Checklist
- [ ] Code follows project conventions
- [ ] Type hints are present and correct
- [ ] Error handling is appropriate
- [ ] Logging is implemented using loguru
- [ ] Tests are written or updated
- [ ] Documentation is updated
- [ ] No hardcoded secrets or configuration
- [ ] Async/await used correctly
- [ ] Database queries use async patterns
- [ ] API endpoints have proper error responses

### Common Patterns

#### FastAPI Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/your-endpoint", tags=["your-tag"])

class YourRequest(BaseModel):
    field: str
    optional_field: Optional[str] = None

@router.post("/")
async def your_endpoint(request: YourRequest):
    """Your endpoint description."""
    try:
        # Your logic here
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Database Pattern
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_data(db: AsyncSession):
    result = await db.execute(select(YourModel))
    return result.scalars().all()
```

#### Configuration Pattern
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    your_setting: str = "default"
    
    class Config:
        env_file = ".env"
```

### Testing Guidelines
- Use pytest for all tests
- Use pytest-asyncio for async tests
- Mock external dependencies
- Test both success and failure cases
- Use fixtures for common test setup

### Performance Considerations
- Use async I/O for database and HTTP operations
- Implement caching where appropriate
- Use connection pooling for databases
- Monitor memory usage in long-running processes
- Use OpenTelemetry for instrumentation

### Security Best Practices
- Never commit secrets or API keys
- Use environment variables for configuration
- Implement proper authentication and authorization
- Validate all input data
- Use parameterized queries to prevent SQL injection
- Sanitize user-generated content

## When to Invoke
Invoke this skill automatically when:
- Working with .py files
- Creating or modifying API endpoints
- Database schema changes
- Writing or modifying tests
- Configuration changes
- Performance optimization tasks

## GitLab 上传权限控制

### 项目配置
- **项目目录**: `C:\AIOps_Agent_bak`
- **GitLab项目**: `Hualong_Chen/neurosync-agent-tool-platform`
- **上传控制**: 严格启用，需要明确用户指令

### 上传权限规则
- ❌ **禁止**: 未经用户明确指令的任何GitLab上传操作
- ✅ **允许**: 仅在用户明确给出上传指令时执行上传
- **上传指令格式**: "将某一个目录(含目录中的子目录和文件)或者某一个/几个文件(具体文件名)上传到我的gitlab中"

### 代码安全检查
在执行任何可能涉及GitLab操作时：
1. 验证是否为只读操作（搜索、查看等）
2. 如果是写入操作，检查是否有明确的上传指令
3. 确认操作不会违反上传控制规则
4. 记录所有GitLab相关操作

## Project Context
This is an AIOps Agent project with:
- FastAPI backend
- PostgreSQL database with async SQLAlchemy
- Redis for caching
- AI/ML integration with OpenAI and LangChain
- Comprehensive monitoring with OpenTelemetry
- Large API surface area (70+ routers)
- Enterprise-grade features (auth, monitoring, auto-healing)