# Developer Guide
开发者指南

## 项目概述

AIOps SRE Agent是一个智能运维系统，提供全面的监控、自动化修复、AI分析和混沌工程功能。

## 技术栈

### 后端
- **语言**: Python 3.12+
- **框架**: FastAPI
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **ORM**: SQLAlchemy
- **迁移**: Alembic
- **缓存**: Redis

### 前端
- **框架**: React
- **状态管理**: Redux
- **UI组件**: Material-UI

### AI/ML
- **LLM**: OpenAI / MiniMax
- **向量数据库**: Qdrant
- **RAG**: LangChain

## 项目结构

```
aiops-sre-agent/
├── api/                    # API路由
│   ├── business_impact_advanced_router.py
│   ├── chaos_advanced_router.py
│   └── ...
├── core/                   # 核心模块
│   ├── models.py          # 数据库模型
│   ├── auth_db.py         # 认证数据库
│   ├── database.py        # 数据库连接
│   └── ...
├── alembic/               # 数据库迁移
│   └── versions/
├── tests/                 # 测试
│   ├── test_database_migration.py
│   ├── test_dual_write_logic.py
│   └── ...
├── scripts/               # 脚本
│   └── validate_business_impact_migration.py
├── docs/                  # 文档
└── config.py              # 配置文件
```

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/HualongChen666/AIOps-Agents.git
cd AIOps-Agents
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# AI / LLM providers
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://api.minimaxi.com/v1
AI_MODEL=MiniMax-Text-01
AI_ENABLED=true

# Data stores
DATABASE_URL=sqlite:///data/aiops.db
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password_here

# Security
AIOPS_ENFORCE_ABAC=true
SNAPSHOT_ENCRYPTION_KEY=your_encryption_key_here
INTERNAL_API_KEY=your_internal_api_key_here
JWT_SECRET_KEY=your_jwt_secret_key_minimum_32_characters
```

### 5. 初始化数据库

```bash
# 运行数据库迁移
python -m alembic upgrade head
```

### 6. 启动开发服务器

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 数据库迁移

### 创建新迁移

```bash
python -m alembic revision --autogenerate -m "description"
```

### 应用迁移

```bash
python -m alembic upgrade head
```

### 回滚迁移

```bash
python -m alembic downgrade -1
```

### 查看当前版本

```bash
python -m alembic current
```

## 测试

### 运行所有测试

```bash
python -m pytest
```

### 运行特定测试文件

```bash
python -m pytest tests/test_database_migration.py
```

### 运行特定测试

```bash
python -m pytest tests/test_database_migration.py::TestBusinessImpactMigration::test_business_impact_analysis_table_exists
```

### 生成覆盖率报告

```bash
python -m pytest --cov=api --cov=core --cov-report=html
```

## 代码规范

### Python代码规范

- 遵循PEP 8规范
- 使用类型提示
- 编写文档字符串
- 最大行长度：100字符

### 命名规范

- 类名：PascalCase (e.g., `BusinessImpactAnalysisDB`)
- 函数名：snake_case (e.g., `save_analysis_to_db`)
- 变量名：snake_case (e.g., `analysis_data`)
- 常量：UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)

### Git提交规范

提交消息格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构
- `chore`: 构建/工具相关

示例：

```
feat(business_impact): add database models for business impact analysis

Added three new database models:
- BusinessImpactAnalysisDB
- BusinessImpactDependencyDB  
- BusinessImpactReportDB

Closes #123
```

## API开发

### 创建新路由

1. 在 `api/` 目录下创建新文件
2. 定义路由和端点
3. 实现业务逻辑
4. 添加测试

示例：

```python
# api/example_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/example", tags=["Example"])

class ExampleRequest(BaseModel):
    name: str
    value: int

@router.post("/create")
async def create_example(request: ExampleRequest):
    try:
        # 实现业务逻辑
        return {"status": "success", "data": request.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 注册路由

在 `main.py` 中注册路由：

```python
from api.example_router import router as example_router

app.include_router(example_router)
```

## 数据库操作

### 查询数据

```python
from core.auth_db import get_session
from core.models import BusinessImpactAnalysisDB

def get_analysis(analysis_id: str):
    db = get_session()
    try:
        analysis = db.query(BusinessImpactAnalysisDB).filter(
            BusinessImpactAnalysisDB.id == analysis_id
        ).first()
        return analysis
    finally:
        db.close()
```

### 创建数据

```python
def create_analysis(data: dict):
    db = get_session()
    try:
        analysis = BusinessImpactAnalysisDB(**data)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
```

### 更新数据

```python
def update_analysis(analysis_id: str, updates: dict):
    db = get_session()
    try:
        analysis = db.query(BusinessImpactAnalysisDB).filter(
            BusinessImpactAnalysisDB.id == analysis_id
        ).first()
        if analysis:
            for key, value in updates.items():
                setattr(analysis, key, value)
            db.commit()
        return analysis
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
```

### 删除数据

```python
def delete_analysis(analysis_id: str):
    db = get_session()
    try:
        analysis = db.query(BusinessImpactAnalysisDB).filter(
            BusinessImpactAnalysisDB.id == analysis_id
        ).first()
        if analysis:
            db.delete(analysis)
            db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
```

## 双写模式

### 实现双写

```python
from core.auth_db import get_session
from core.models import BusinessImpactAnalysisDB

def save_with_dual_write(data: dict, json_file: Path):
    # 保存到JSON文件
    _save_json_file(json_file, data)
    
    # 双写到数据库
    db = get_session()
    try:
        _save_to_db(db, data)
    except Exception as e:
        # 记录错误但继续使用JSON存储
        logger.error(f"Database write failed: {e}")
    finally:
        db.close()
```

## 性能优化

### 数据库优化

1. **使用索引**
   ```python
   __table_args__ = (
       Index("idx_table_field", "field"),
   )
   ```

2. **批量操作**
   ```python
   # 批量插入
   db.bulk_insert_mappings(AnalysisDB, data_list)
   ```

3. **查询优化**
   ```python
   # 使用select减少数据传输
   db.query(AnalysisDB.id, AnalysisDB.name).all()
   ```

### 缓存策略

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_data(key: str):
    return expensive_operation(key)
```

## 调试

### 日志配置

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 添加处理器
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
```

### 断点调试

```python
import pdb

def debug_function():
    pdb.set_trace()  # 设置断点
    # 调试代码
```

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t aiops-sre-agent .

# 运行容器
docker run -p 8000:8000 aiops-sre-agent
```

### Kubernetes部署

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-sre-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiops-sre-agent
  template:
    metadata:
      labels:
        app: aiops-sre-agent
    spec:
      containers:
      - name: aiops-sre-agent
        image: aiops-sre-agent:latest
        ports:
        - containerPort: 8000
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库连接
   python -c "from core.database import engine; engine.connect()"
   ```

2. **迁移失败**
   ```bash
   # 检查迁移状态
   python -m alembic current
   
   # 回滚并重试
   python -m alembic downgrade -1
   python -m alembic upgrade head
   ```

3. **测试失败**
   ```bash
   # 运行特定测试查看详细输出
   python -m pytest tests/test_file.py -v -s
   ```

## 贡献指南

### 提交PR流程

1. Fork仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

### 代码审查

- 确保所有测试通过
- 添加必要的测试
- 更新相关文档
- 遵循代码规范

## 参考资料

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)

## 支持

如有问题，请：
1. 查看文档
2. 搜索现有Issues
3. 创建新的Issue
4. 联系维护团队