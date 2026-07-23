# Database Performance Tests

## 概述

本目录包含AIOps Agent的数据库性能测试框架，基于pytest-benchmark实现，支持CRUD操作、连接池、事务处理、索引优化等关键场景的性能测试。

## 目录结构

```
tests/performance/database/
├── __init__.py                      # 包初始化文件
├── test_crud_performance.py         # CRUD操作性能测试
├── test_connection_pool_performance.py  # 连接池性能测试
├── test_transaction_performance.py  # 事务处理性能测试
├── test_index_performance.py        # 索引优化效果测试
├── slow_query_analyzer.py           # 慢查询分析工具
├── db_report_generator.py           # 数据库性能报告生成器
├── run_db_performance_test.py       # 命令行运行脚本
└── README.md                        # 本文档
```

## 测试覆盖场景

### 1. CRUD操作性能测试 (test_crud_performance.py)

**SELECT查询测试**:
- 单条记录查询（按ID）
- 带过滤条件的查询
- 多条件过滤查询
- 带排序的查询
- JOIN查询
- COUNT查询
- 聚合查询（AVG, MAX, MIN）
- GROUP BY查询
- 子查询
- 窗口函数
- CTE查询
- JSON字段查询

**INSERT操作测试**:
- 单条插入
- 批量插入10条
- 批量插入100条
- 批量插入1000条

**UPDATE操作测试**:
- 单条更新
- 批量更新10条
- 批量更新100条

**DELETE操作测试**:
- 单条删除
- 批量删除10条
- 批量删除100条

**不同数据量级测试**:
- 1K记录查询
- 10K记录查询
- 100K记录查询

### 2. 连接池性能测试 (test_connection_pool_performance.py)

**连接获取/释放测试**:
- 连接获取性能
- 连接释放性能
- 连接复用性能

**并发连接测试**:
- 10个并发连接
- 50个并发连接
- 100个并发连接

**连接池优化测试**:
- 连接池大小优化（5/10/20/30/40/50）
- 连接等待时间测试
- 连接泄漏检测

**压力测试**:
- 1000请求压力测试
- 持续负载压力测试
- 连接池耗尽恢复测试

**连接池指标测试**:
- 连接池状态测试
- 连接池健康检查

### 3. 事务处理性能测试 (test_transaction_performance.py)

**事务类型测试**:
- 单事务性能
- 事务回滚性能
- 批量事务10条
- 批量事务100条
- 批量事务1000条
- 读写混合事务
- 嵌套事务

**事务隔离级别测试**:
- READ COMMITTED隔离级别
- SERIALIZABLE隔离级别

**事务并发测试**:
- 10个并发事务
- 50个并发事务
- 锁竞争测试
- 死锁检测测试

**性能对比测试**:
- 单条vs批量100条记录性能对比

### 4. 索引优化效果测试 (test_index_performance.py)

**索引性能对比**:
- 有索引vs无索引查询
- 复合索引查询
- 范围查询索引
- 排序索引
- 部分索引
- 覆盖索引

**索引管理测试**:
- 索引创建性能
- 索引删除性能
- 索引重建性能

**索引有效性测试**:
- 索引选择性测试
- 索引使用统计
- 未使用索引检测
- 索引大小分析

**不同数据量级测试**:
- 1K数据量索引性能
- 10K数据量索引性能
- 100K数据量索引性能

### 5. 慢查询分析工具 (slow_query_analyzer.py)

**慢查询分析功能**:
- 分析pg_stat_statements视图
- 分析当前活动查询
- 分析表统计信息
- 生成查询优化建议
- 启用/禁用查询日志

**表健康检查**:
- 全表扫描检测
- 死元组比例检查
- VACUUM/ANALYZE状态检查

## 使用方法

### 运行所有数据库性能测试

```bash
# 进入项目根目录
cd C:\AIOps_Agent_bak

# 运行所有数据库性能测试
pytest tests/performance/database/ -v --benchmark-only

# 生成HTML报告
pytest tests/performance/database/ -v --benchmark-only --benchmark-html=reports/db_benchmark.html
```

### 运行特定测试文件

```bash
# 运行CRUD性能测试
pytest tests/performance/database/test_crud_performance.py -v --benchmark-only

# 运行连接池性能测试
pytest tests/performance/database/test_connection_pool_performance.py -v --benchmark-only

# 运行事务性能测试
pytest tests/performance/database/test_transaction_performance.py -v --benchmark-only

# 运行索引性能测试
pytest tests/performance/database/test_index_performance.py -v --benchmark-only
```

### 运行特定测试用例

```bash
# 运行单个测试
pytest tests/performance/database/test_crud_performance.py::TestSelectPerformance::test_select_single_by_id -v --benchmark-only

# 运行特定测试类
pytest tests/performance/database/test_crud_performance.py::TestSelectPerformance -v --benchmark-only
```

### 使用慢查询分析工具

```python
# 在Python脚本中使用
from tests.performance.database.slow_query_analyzer import analyze_slow_queries, check_table_health

# 分析慢查询
report = await analyze_slow_queries(threshold_ms=100.0)
print(report)

# 检查表健康
health_report = await check_table_health()
print(health_report)
```

### 使用命令行运行脚本

```bash
# 运行数据库性能测试（使用脚本）
python tests/performance/database/run_db_performance_test.py --all

# 运行特定测试类型
python tests/performance/database/run_db_performance_test.py --crud
python tests/performance/database/run_db_performance_test.py --pool
python tests/performance/database/run_db_performance_test.py --transaction
python tests/performance/database/run_db_performance_test.py --index

# 运行慢查询分析
python tests/performance/database/run_db_performance_test.py --analyze-slow-queries

# 生成性能报告
python tests/performance/database/run_db_performance_test.py --generate-report
```

## 性能基准

根据 `docs/performance_baseline.md`，数据库性能基准如下：

### CRUD操作基准

| 操作 | 数据量 | 目标P95(ms) |
|------|--------|-------------|
| SELECT单条 | 1 | 5 |
| SELECT带过滤 | 10 | 20 |
| SELECT复杂查询 | 100 | 100 |
| INSERT单条 | 1 | 10 |
| INSERT批量100 | 100 | 100 |
| UPDATE单条 | 1 | 10 |
| UPDATE批量100 | 100 | 100 |
| DELETE单条 | 1 | 10 |
| DELETE批量100 | 100 | 100 |

### 连接池基准

| 测试项 | 目标P95(ms) |
|--------|-------------|
| 连接获取 | 5 |
| 连接释放 | 2 |
| 10并发连接 | 50 |
| 50并发连接 | 200 |
| 100并发连接 | 500 |

### 事务基准

| 事务类型 | 数据量 | 目标P95(ms) |
|----------|--------|-------------|
| 单事务 | 1 | 15 |
| 批量事务100 | 100 | 150 |
| 批量事务1000 | 1000 | 1000 |
| 并发事务10 | 10 | 100 |

### 索引基准

| 查询类型 | 有索引(ms) | 无索引(ms) | 性能提升 |
|----------|-----------|-----------|----------|
| 主键查询 | 5 | 100 | 95% |
| 范围查询 | 20 | 500 | 96% |
| 排序查询 | 30 | 1000 | 97% |

## 性能优化建议

### 1. 索引优化

- 为频繁查询的字段添加索引
- 使用复合索引优化多条件查询
- 定期分析索引使用情况，删除未使用的索引
- 考虑使用部分索引减少索引大小

### 2. 查询优化

- 避免使用SELECT *，只查询需要的字段
- 使用LIMIT限制返回结果数量
- 避免在WHERE子句中使用函数
- 考虑使用JOIN替代子查询
- 对聚合查询添加索引

### 3. 连接池优化

- 根据并发量调整连接池大小
- 监控连接池使用情况
- 设置合理的连接超时时间
- 启用连接池预检查（pool_pre_ping）

### 4. 事务优化

- 使用批量事务减少事务数量
- 避免长事务
- 合理设置事务隔离级别
- 使用嵌套事务减少锁竞争

### 5. 表维护

- 定期执行VACUUM清理死元组
- 定期执行ANALYZE更新统计信息
- 监控表膨胀情况
- 考虑分区表处理大表

## 报告生成

### HTML报告

生成的HTML报告包含：
- 测试摘要（总测试数、通过/失败、总耗时）
- CRUD操作性能详情
- 连接池性能详情
- 事务性能详情
- 索引性能对比
- 慢查询分析
- 优化建议

### JSON报告

生成的JSON报告包含：
- 元数据（测试时间、数据库、环境）
- 摘要统计
- 详细性能指标
- 慢查询列表
- 优化建议

## CI/CD集成

数据库性能测试可以集成到CI/CD流程中：

```yaml
# .github/workflows/database-performance-test.yml
name: Database Performance Tests

on:
  push:
    branches: [ main, develop ]
  schedule:
    - cron: '0 3 * * *'  # 每天凌晨3点运行

jobs:
  db-performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install pytest pytest-benchmark sqlalchemy asyncpg
      - name: Run database performance tests
        run: |
          pytest tests/performance/database/ -v --benchmark-only --benchmark-json=db_benchmark.json
      - name: Upload benchmark results
        uses: actions/upload-artifact@v3
        with:
          name: db-benchmark-results
          path: db_benchmark.json
```

## 故障排查

### 常见问题

**问题**: 测试连接数据库失败
- **解决**: 检查DATABASE_URL配置，确保数据库可访问

**问题**: pg_stat_statements扩展未启用
- **解决**: 在PostgreSQL中执行 `CREATE EXTENSION pg_stat_statements;`

**问题**: 测试数据过多导致性能下降
- **解决**: 在测试前清理测试数据，使用事务回滚

**问题**: 连接池耗尽
- **解决**: 增加连接池大小或减少并发数

## 依赖项

```txt
pytest>=7.0.0
pytest-benchmark>=4.0.0
sqlalchemy>=2.0.0
asyncpg>=0.27.0
```

## 扩展开发

### 添加新的性能测试

在相应的测试文件中添加新的测试方法：

```python
@pytest.mark.asyncio
async def test_new_performance_scenario(self, db_session, benchmark):
    """新的性能测试场景"""
    async def new_scenario():
        # 实现测试逻辑
        pass
    
    benchmark.pedantic(new_scenario)
```

### 添加新的慢查询分析规则

在 `slow_query_analyzer.py` 的 `generate_optimization_suggestions` 方法中添加新的规则：

```python
# 检查新的查询模式
if "some_pattern" in query_text:
    suggestions.append("新的优化建议")
    priority = "high"
    estimated_improvement += 30.0
```

## 贡献指南

1. 遵循项目代码规范
2. 添加适当的测试用例
3. 更新相关文档
4. 提交Pull Request

## 联系方式

- **数据库性能测试团队**: db-perf-team@example.com
- **技术支持**: support@example.com

## 许可证

MIT License
