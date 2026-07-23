# CI/CD 环境配置文档

## 概述

本文档描述了AIOps Agent项目的CI/CD环境配置，用于自动化测试执行。

## 工作流文件

### 1. integration-test-automation.yml
完整的集成测试自动化工作流，包括：
- 基础集成测试
- 数据库集成测试
- Redis集成测试
- 完整集成测试
- 单元测试
- 安全测试
- 代码质量检查

### 2. quick-integration-tests.yml
快速集成测试工作流，用于快速验证：
- 只运行不需要外部服务的集成测试
- 适合PR快速验证

### 3. test.yml
现有的测试工作流，包括：
- 单元测试
- 集成测试
- 安全扫描
- 代码质量检查
- 性能测试

## 触发条件

### 自动触发
- **Push事件**: main, develop分支
- **Pull Request**: main, develop分支
- **定时任务**: 每日UTC时间执行

### 手动触发
- **workflow_dispatch**: 支持手动触发

## 环境变量

### 全局环境变量
```yaml
env:
  PYTHON_VERSION: '3.12'
  ENVIRONMENT: test
  TESTING: true
```

### 服务配置
```yaml
DATABASE_URL: postgresql://testuser:testpass@localhost:5432/test_db
REDIS_URL: redis://localhost:6379/1
```

## 测试分类

### 1. 基础集成测试
**标记**: `integration and not database and not redis and not api`

**内容**:
- 示例数据测试
- Mock服务测试
- 测试工具测试
- 参数化测试

**运行时间**: ~30秒

### 2. 数据库集成测试
**标记**: `database`

**依赖**: PostgreSQL服务

**内容**:
- 数据库连接测试
- 数据库操作测试
- 数据库迁移测试

**运行时间**: ~2分钟

### 3. Redis集成测试
**标记**: `redis`

**依赖**: Redis服务

**内容**:
- Redis连接测试
- Redis操作测试
- 缓存功能测试

**运行时间**: ~1分钟

### 4. 完整集成测试
**标记**: `integration`

**依赖**: PostgreSQL + Redis服务

**内容**:
- 所有集成测试
- 覆盖率报告
- 性能指标

**运行时间**: ~5分钟

### 5. 单元测试
**路径**: `tests/core/`, `tests/api/`, `tests/utils/`

**Python版本**: 3.11, 3.12, 3.14

**内容**:
- 核心功能测试
- API路由测试
- 工具函数测试

**运行时间**: ~3分钟

## 使用指南

### 本地验证

#### 1. 验证基础集成测试
```bash
# 设置环境
python tests/integration/setup_integration_test_env.py --setup

# 运行基础集成测试
pytest tests/integration/ -m "integration and not database and not redis and not api" -v
```

#### 2. 验证数据库测试
```bash
# 启动PostgreSQL
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=test_db \
  postgres:15

# 运行数据库测试
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/test_db \
pytest tests/integration/ -m "database" -v
```

#### 3. 验证Redis测试
```bash
# 启动Redis
docker run -d -p 6379:6379 redis:7

# 运行Redis测试
REDIS_URL=redis://localhost:6379/1 \
pytest tests/integration/ -m "redis" -v
```

### GitHub Actions使用

#### 1. 手动触发工作流
1. 进入GitHub仓库
2. 点击"Actions"标签
3. 选择工作流
4. 点击"Run workflow"
5. 选择分支并运行

#### 2. 查看测试结果
1. 进入GitHub仓库
2. 点击"Actions"标签
3. 选择工作流运行
4. 查看测试结果和日志
5. 下载测试报告

#### 3. 下载测试报告
1. 进入工作流运行页面
2. 滚动到"Artifacts"部分
3. 下载所需的报告

## 测试报告

### 报告类型

#### 1. 测试结果报告
- **文件名**: test-results.xml
- **格式**: JUnit XML
- **内容**: 测试用例结果

#### 2. 覆盖率报告
- **文件名**: coverage.xml, htmlcov/
- **格式**: XML, HTML
- **内容**: 代码覆盖率数据

#### 3. 安全扫描报告
- **文件名**: bandit-report.json, bandit-report.html
- **格式**: JSON, HTML
- **内容**: 安全漏洞扫描结果

#### 4. 性能报告
- **文件名**: benchmark-results.json
- **格式**: JSON
- **内容**: 性能基准测试结果

### 报告保留期
- **保留期**: 30天
- **自动清理**: GitHub自动清理过期报告

## 故障排除

### 常见问题

#### 1. 数据库连接失败
**问题**: PostgreSQL连接超时

**解决方案**:
- 检查PostgreSQL服务状态
- 验证连接字符串
- 检查网络连接

#### 2. Redis连接失败
**问题**: Redis连接超时

**解决方案**:
- 检查Redis服务状态
- 验证连接字符串
- 检查端口配置

#### 3. 测试超时
**问题**: 测试执行超时

**解决方案**:
- 增加超时时间
- 优化测试性能
- 检查是否有死锁

#### 4. 依赖安装失败
**问题**: pip install失败

**解决方案**:
- 更新pip版本
- 清理pip缓存
- 检查requirements.txt

## 最佳实践

### 1. 测试标记使用
```python
@pytest.mark.integration
async def test_my_feature():
    pass

@pytest.mark.database
async def test_database_feature():
    pass

@pytest.mark.redis
async def test_redis_feature():
    pass
```

### 2. 测试隔离
```python
@pytest.fixture
async def clean_test_data():
    # 准备测试数据
    yield
    # 清理测试数据
```

### 3. 环境变量管理
```python
@pytest.fixture(scope="session")
def test_environment():
    # 加载测试环境变量
    yield
    # 清理环境
```

### 4. Mock服务使用
```python
@pytest.fixture
def mock_external_service():
    # 配置Mock
    yield mock
    # 清理Mock
```

## 性能优化

### 1. 并行测试
```bash
pytest -n auto
```

### 2. 测试缓存
- GitHub Actions自动缓存pip包
- 减少依赖安装时间

### 3. 选择性测试
```bash
# 只运行失败的测试
pytest --lf

# 只运行特定标记的测试
pytest -m integration
```

## 安全考虑

### 1. 敏感信息保护
- 使用GitHub Secrets存储敏感信息
- 不要在代码中硬编码密钥
- 使用环境变量传递配置

### 2. 依赖安全
- 定期更新依赖
- 使用safety检查漏洞
- 使用bandit扫描代码

### 3. 访问控制
- 限制工作流触发权限
- 使用分支保护规则
- 审查PR变更

## 监控和告警

### 1. 测试失败告警
- GitHub Actions自动通知
- Slack集成（可选）
- 邮件通知（可选）

### 2. 性能监控
- 测试执行时间
- 资源使用情况
- 失败率统计

### 3. 趋势分析
- 覆盖率趋势
- 测试通过率趋势
- 性能趋势

## 持续改进

### 1. 定期审查
- 每月审查CI/CD配置
- 优化测试执行时间
- 更新依赖版本

### 2. 反馈循环
- 收集团队反馈
- 改进测试策略
- 优化工作流配置

### 3. 文档更新
- 及时更新文档
- 记录变更历史
- 分享最佳实践

## 参考资源

### GitHub Actions文档
- [GitHub Actions文档](https://docs.github.com/en/actions)
- [Workflow语法](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)

### 测试工具文档
- [Pytest文档](https://docs.pytest.org/)
- [pytest-asyncio文档](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)

### CI/CD最佳实践
- [CI/CD最佳实践](https://www.atlassian.com/continuous-delivery/principles/continuous-integration-vs-delivery-vs-deployment)
- [测试策略](https://martinfowler.com/articles/practical-test-pyramid.html)

## 总结

CI/CD环境配置为AIOps Agent项目提供了：
- ✅ 自动化测试执行
- ✅ 多环境支持
- ✅ 测试报告生成
- ✅ 安全扫描集成
- ✅ 代码质量检查
- ✅ 性能监控

通过合理使用这些工具，可以确保代码质量和项目稳定性。
