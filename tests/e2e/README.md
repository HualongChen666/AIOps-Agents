# E2E Tests Documentation
# E2E测试文档

## 概述

本目录包含10个高质量的端到端（E2E）测试，覆盖系统的主要业务流程和集成场景。这些测试使用真实的HTTP客户端，不使用Mock，确保测试的真实性和可靠性。

## 测试文件

### 1. test_alert_creation_to_processing.py
**告警创建到处理的完整流程**

- 测试完整的告警生命周期：创建→分析→处理→关闭
- 测试告警聚合和关联功能
- 测试告警通知工作流
- 测试告警升级工作流
- 测试告警指标收集和分析

**关键测试类**:
- `TestAlertCreationToProcessingWorkflow`
- `TestAlertMetricsAndAnalytics`

### 2. test_root_cause_analysis.py
**根因分析的端到端流程**

- 测试完整的根因分析管道：数据收集→关联分析→根因识别
- 测试多组件关联分析
- 测试历史模式匹配
- 测试因果链分析
- 测试根因分析置信度验证

**关键测试类**:
- `TestRootCauseAnalysisWorkflow`
- `TestRootCauseReporting`

### 3. test_auto_repair_workflow.py
**自动修复的完整工作流**

- 测试完整的自动修复生命周期：告警→分析→修复→验证
- 测试多阶段修复过程
- 测试修复审批工作流
- 测试修复回滚机制
- 测试修复历史跟踪

**关键测试类**:
- `TestAutoRepairWorkflow`
- `TestRepairSafeguards`

### 4. test_auth_authorization.py
**用户认证和授权流程**

- 测试完整认证工作流：注册→登录→令牌获取→API访问→登出
- 测试基于角色的访问控制
- 测试令牌过期和刷新
- 测试权限层次

**关键测试类**:
- `TestAuthenticationAndAuthorization`

### 5. test_api_performance.py
**API性能测试场景**

- 测试API响应时间基准
- 测试并发请求处理
- 测试API吞吐量测量
- 测试大负载处理
- 测试负载下的错误率
- 测试API资源清理

**关键测试类**:
- `TestAPIPerformance`

### 6. test_database_integration.py
**数据库集成测试**

- 测试数据库连接池
- 测试数据库事务回滚
- 测试数据库查询性能
- 测试数据库连接恢复
- 测试数据库数据完整性
- 测试数据库模式迁移
- 测试数据库备份和恢复

**关键测试类**:
- `TestDatabaseIntegration`

### 7. test_redis_integration.py
**Redis缓存集成测试**

- 测试缓存写入和读取
- 测试缓存过期
- 测试缓存失效
- 测试缓存性能
- 测试缓存命中率
- 测试缓存并发访问
- 测试缓存连接池
- 测试缓存数据序列化

**关键测试类**:
- `TestRedisCacheIntegration`

### 8. test_qdrant_integration.py
**Qdrant向量数据库集成测试**

- 测试向量集合创建
- 测试向量插入和搜索
- 测试向量相似度搜索
- 测试向量过滤
- 测试向量批量操作
- 测试向量更新和删除
- 测试向量操作性能

**关键测试类**:
- `TestQdrantIntegration`

### 9. test_websocket_communication.py
**WebSocket实时通信测试**

- 测试WebSocket连接
- 测试WebSocket告警通知
- 测试多客户端WebSocket连接
- 测试WebSocket心跳机制
- 测试WebSocket重连机制
- 测试WebSocket消息顺序
- 测试WebSocket认证
- 测试WebSocket大消息处理
- 测试WebSocket频道订阅
- 测试WebSocket错误处理

**关键测试类**:
- `TestWebSocketCommunication`

### 10. test_error_recovery_retry.py
**错误恢复和重试测试**

- 测试API超时重试
- 测试数据库连接重试
- 测试熔断器模式
- 测试优雅降级
- 测试指数退避重试
- 测试舱壁模式
- 测试死信队列
- 测试基于健康检查的恢复
- 测试幂等操作
- 测试错误时的事务回滚

**关键测试类**:
- `TestErrorRecoveryAndRetry`

## 环境配置

### 必需的服务

1. **应用服务器**: `http://localhost:8000`
2. **PostgreSQL数据库**: `postgresql://testuser:testpass@localhost:5432/test_db`
3. **Redis缓存**: `redis://localhost:6379/1`
4. **Qdrant向量数据库**: `http://localhost:6333`
5. **WebSocket服务器**: `ws://localhost:8000/ws`

### 环境变量

复制 `.env.example` 到 `.env` 并配置相应的值：

```bash
cp .env.example .env
```

主要环境变量：
- `E2E_BASE_URL`: 应用基础URL
- `E2E_DATABASE_URL`: 数据库连接字符串
- `E2E_REDIS_URL`: Redis连接字符串
- `E2E_QDRANT_URL`: Qdrant连接URL
- `E2E_REQUEST_TIMEOUT`: 请求超时时间（秒）

## 运行测试

### 运行所有E2E测试

```bash
pytest tests/e2e/ -v -m e2e
```

### 运行特定测试文件

```bash
pytest tests/e2e/test_alert_creation_to_processing.py -v
```

### 运行特定测试类

```bash
pytest tests/e2e/test_alert_creation_to_processing.py::TestAlertCreationToProcessingWorkflow -v
```

### 运行特定测试方法

```bash
pytest tests/e2e/test_alert_creation_to_processing.py::TestAlertCreationToProcessingWorkflow::test_complete_alert_lifecycle -v
```

### 并行运行E2E测试

```bash
pytest tests/e2e/ -v -m e2e --e2e-parallel -n 4
```

### 只运行快速测试

```bash
pytest tests/e2e/ -v -m "e2e and not slow"
```

### 生成测试报告

```bash
pytest tests/e2e/ -v -m e2e --html=e2e_report.html --self-contained-html
```

## 测试标记

- `@pytest.mark.e2e`: 标记为E2E测试
- `@pytest.mark.slow`: 标记为慢速测试
- `@pytest.mark.integration`: 标记为集成测试

## 测试依赖

### Python依赖

```bash
pip install pytest pytest-asyncio httpx websockets
```

### 系统依赖

1. **PostgreSQL**: 数据库服务
2. **Redis**: 缓存服务
3. **Qdrant**: 向量数据库服务

### 启动测试环境

使用Docker Compose启动所有依赖服务：

```bash
docker-compose -f docker-compose.test.yml up -d
```

## 测试数据管理

### 测试数据隔离

- 每个测试使用唯一的前缀：`e2e_test_{timestamp}`
- 测试完成后自动清理测试数据
- 支持测试数据隔离配置

### 清理策略

- 默认在每个测试后清理
- 可配置保留测试数据用于调试
- 支持批量清理

## 测试稳定性

### 超时设置

- 单个请求超时：30秒
- 操作超时：60秒
- 测试超时：300秒

### 重试机制

- 失败的测试会自动重试
- 支持指数退避策略
- 可配置最大重试次数

### 错误处理

- 测试失败时提供详细日志
- 支持失败截图（UI测试）
- 自动收集系统状态信息

## 故障排查

### 常见问题

1. **连接被拒绝**
   - 确保所有服务已启动
   - 检查端口配置是否正确
   - 验证防火墙设置

2. **超时错误**
   - 增加超时时间配置
   - 检查服务性能
   - 优化测试数据量

3. **认证失败**
   - 检测试试用户凭证
   - 验证认证服务状态
   - 确认令牌有效性

### 调试模式

```bash
pytest tests/e2e/ -v -m e2e -s --log-cli-level=DEBUG
```

## CI/CD集成

### GitHub Actions示例

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
      
      redis:
        image: redis:6
        ports:
          - 6379:6379
      
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx websockets
      
      - name: Run E2E tests
        run: pytest tests/e2e/ -v -m e2e
```

## 最佳实践

### 编写E2E测试

1. **独立性**: 每个测试应该独立运行，不依赖其他测试
2. **清理**: 测试完成后清理所有创建的资源
3. **超时**: 为每个操作设置合理的超时时间
4. **重试**: 为可能失败的操作添加重试逻辑
5. **日志**: 记录足够的调试信息

### 维护E2E测试

1. **定期更新**: 随着API变化更新测试
2. **性能监控**: 监控测试执行时间
3. **稳定性**: 确保测试稳定可靠
4. **文档更新**: 保持文档与测试同步

## 贡献指南

### 添加新的E2E测试

1. 在相应的测试文件中添加新的测试方法
2. 使用适当的测试标记
3. 添加测试文档
4. 确保测试独立性和清理逻辑
5. 运行测试验证

### 修改现有测试

1. 理解测试目的和场景
2. 保持测试的独立性
3. 更新相关文档
4. 验证修改后的测试

## 性能基准

### 预期执行时间

- 快速测试：< 30秒
- 标准测试：30-120秒
- 慢速测试：> 120秒

### 并发执行

- 默认串行执行
- 支持最多4个并发工作进程
- 注意资源限制和竞争条件

## 许可证

与主项目相同的许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues
- 邮件：dev@example.com
- Slack：#e2e-tests