# AIOps Agent 项目配置

项目特定的开发命令、验证步骤和配置信息。

## 🏗️ 项目结构

```
AIOps_Agent_bak/
├── api/                    # FastAPI 路由 (70+ routers)
├── core/                   # 核心功能
│   ├── ai/                # AI/ML 集成
│   ├── agent/             # Agent 系统
│   └── database/          # 数据库配置
├── alembic/               # 数据库迁移
├── tests/                 # 测试套件
├── frontend/              # 前端代码
├── infrastructure/        # 基础设施配置
└── main.py               # 应用入口
```

## 🔧 开发命令

### 环境设置

```bash
# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 代码质量

```bash
# 格式化代码
python -m black .

# 排序导入并检查 Lint（ruff 被 Windows App Control 阻止时会自动 fallback 到 flake8 + isort）
python scripts/run_ruff.py .

# 类型检查
python -m mypy .

# 安全检查
bandit -r .

# 依赖安全检查
safety check
```

### 测试

```bash
# 运行 core / api / infrastructure（默认，已隔离避免 sys.modules 污染）
python scripts/run_core_api_infrastructure_tests.py

# 运行性能测试（单独进程，-n 0，--no-cov）
python scripts/run_performance_tests.py

# 运行特定测试文件
pytest tests/unit/test_module.py

# 运行带覆盖率的测试
pytest --cov=. --cov-report=html

# 运行特定标记的测试
pytest -m unit
pytest -m integration
pytest -m e2e

# 只运行失败的测试
pytest --lf
```

> **覆盖率状态**: 当前 `python scripts/run_core_api_infrastructure_tests.py` 输出 core+api+unit 整体覆盖率约 **50.80%**，目标 80%。剩余差距主要来自大量未接入 `main.py`/routers 的 P2 扩展模块；下一步需要为活跃模块补充测试或清理真正未使用的代码。
>
> **注意**: `tests/integration` 需要外部服务（Redis/PostgreSQL），未纳入默认隔离脚本，需单独在集成环境中运行。

### 数据库

```bash
# 生成新的迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

### 应用运行

```bash
# 开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产服务器
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🎯 项目约定

### 代码风格

- **Line length**: 100 字符
- **Python 版本**: 3.10+
- **类型检查**: mypy (严格模式可选)
- **格式化**: black
- **Linting / 导入排序**: ruff（替代 flake8 + isort）
- **文档**: Google style docstrings

### FastAPI 约定

- 所有路由在 `api/` 目录
- 使用 Pydantic v2 进行验证
- 异步数据库操作
- 统一错误处理
- OpenAPI 文档自动生成

### 数据库约定

- 使用 SQLAlchemy 2.0 async
- Alembic 进行迁移
- 连接池配置
- 事务管理

### 测试约定

- pytest 框架
- 异步测试支持
- 覆盖率目标: 80%+
- 单元/集成/E2E 测试分离

## 🔐 环境变量

### 必需变量

```env
DATABASE_URL=postgresql://user:password@localhost:5432/aiops
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 可选变量

```env
LOG_LEVEL=INFO
DEBUG=False
ENVIRONMENT=development
```

## 🚀 CI/CD 流程

### 测试收集验证

```bash
# 运行测试收集验证
python -m pytest --collect-only --tb=line

# 使用验证脚本
python scripts/validate_test_collection.py --min-tests 2000

# 使用Makefile
make test-collection
make validate-tests
```

### Pre-commit Hooks

```bash
# 安装 pre-commit
pre-commit install

# 手动运行
pre-commit run --all-files
```

### 质量门禁

- **测试收集验证**: 所有测试必须可以正常收集，无导入错误
- **最小测试数量**: 必须收集至少2000个测试项
- **所有测试必须通过**: 测试执行必须成功
- **覆盖率必须 >= 80%**: 整体代码覆盖率目标
- **无安全漏洞**: 通过bandit和safety检查
- **代码格式化检查通过**: black 和 ruff 检查
- **类型检查通过**: mypy 类型检查

## 📊 监控和日志

### 日志配置

- 使用 loguru
- 结构化日志
- 日志级别: DEBUG, INFO, WARNING, ERROR
- 日志文件: `logs/`

### 监控

- OpenTelemetry 集成
- Prometheus metrics
- 分布式追踪
- 性能监控

## 🐛 调试技巧

### 常见问题

1. **数据库连接失败**
   - 检查 DATABASE_URL
   - 验证 PostgreSQL 运行状态
   - 检查网络连接

2. **Redis 连接失败**
   - 检查 REDIS_URL
   - 验证 Redis 运行状态

3. **测试失败**
   - 检查测试数据库状态
   - 验证环境变量
   - 查看详细日志

### 调试命令

```bash
# 查看应用日志
tail -f logs/app.log

# 检查数据库连接
psql $DATABASE_URL

# 检查 Redis 连接
redis-cli ping
```

## 📈 性能优化

### 数据库优化

- 使用连接池
- 适当索引
- 查询优化
- 缓存策略

### API 优化

- 异步处理
- 响应缓存
- 分页
- 压缩

### 内存优化

- 监控内存使用
- 及时释放资源
- 使用生成器
- 避免内存泄漏

## 🔒 安全最佳实践

### 认证授权

- JWT tokens
- 角色基础访问控制
- API 密钥管理
- OAuth 2.0

### 数据保护

- 敏感数据加密
- SQL 注入防护
- XSS 防护
- CSRF 保护

### 依赖管理

- 定期更新依赖
- 安全扫描
- 使用固定版本
- 监控漏洞

## 🆘 支持和资源

### 文档

- FastAPI: <https://fastapi.tiangolo.com/>
- SQLAlchemy: <https://docs.sqlalchemy.org/>
- Alembic: <https://alembic.sqlalchemy.org/>
- Pytest: <https://docs.pytest.org/>

### 工具

- Devin IDE 配置: `.devin/`
- MCP 服务器: `.devin/config.json`
- Skills: `.devin/skills/`

## 📝 开发工作流

1. **功能开发**
   - 创建功能分支
   - 编写代码
   - 运行质量检查
   - 编写测试

2. **代码审查**
   - 提交 MR (Merge Request)
   - 自动 CI 检查
   - 人工审查
   - 修改和合并

3. **部署**
   - 更新版本
   - 运行迁移
   - 部署到 staging
   - 验证功能
   - 部署到生产

## 🔄 更新日志

### 最近变更

- 添加 Devin IDE 配置
- 配置 MCP 服务器
- 创建开发技能
- 设置自动化质量检查
- 修复 sys.modules 污染：core/api/infrastructure 使用隔离脚本运行
- 性能测试从默认 CI 分离：`scripts/run_performance_tests.py`
- ruff 受 Windows App Control 阻止时使用 `scripts/run_ruff.py` fallback
- 修复 bandit HIGH 问题并清理 core/db_optimization.py、core/rag_engine.py、core/authentication.py import-time 依赖
- 收紧 `.coveragerc` source 为 core/api 并清理未使用死代码

### 计划中

- 增强 CI/CD 流程
- 添加更多集成测试
- 优化性能监控
- 改进文档
