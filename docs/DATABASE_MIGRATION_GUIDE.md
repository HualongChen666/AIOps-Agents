# Database Migration Guide
数据库迁移指南

## 概述

本文档描述了AIOps SRE Agent从JSON文件存储到数据库存储的迁移过程，包括迁移策略、实施步骤和验证方法。

## 迁移策略

### 双写策略

采用双写策略确保数据迁移过程中的数据安全：

1. **同时写入**：数据同时写入JSON文件和数据库
2. **渐进式迁移**：逐步将各个模块迁移到数据库
3. **回退机制**：保留JSON文件作为备份
4. **一致性验证**：定期验证JSON和数据库数据一致性

### 迁移模块

#### 已完成迁移的模块

1. **业务影响高级路由** (Business Impact Advanced Router)
   - 表：`business_impact_analysis`, `business_impact_dependencies`, `business_impact_reports`
   - 状态：✅ 已完成
   - 迁移脚本：`010_add_business_impact_models.py`

2. **混沌工程高级路由** (Chaos Engineering Advanced Router)
   - 表：`chaos_experiments`, `chaos_scenarios`, `chaos_faults`
   - 状态：✅ 已完成
   - 迁移脚本：`011_add_chaos_engineering_models.py`

3. **AI高级路由** (AI Advanced Router)
   - 表：18个AI相关表
   - 状态：✅ 已完成（已有数据库模型）
   - 迁移脚本：`007_add_ai_advanced_models.py`

4. **工作流高级路由** (Workflow Advanced Router)
   - 表：`workflows`, `workflow_executions`
   - 状态：✅ 已完成（已有数据库模型）

5. **其他高级路由**
   - 状态：✅ 已完成（已有数据库模型）

## 数据库模型

### 业务影响模型

#### BusinessImpactAnalysisDB
```python
class BusinessImpactAnalysisDB(Base):
    """业务影响分析表"""
    __tablename__ = "business_impact_analysis"
    
    id = Column(String(50), primary_key=True)
    service_name = Column(String(200), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False, default="full")
    time_range = Column(String(50), nullable=False, default="1h")
    include_dependencies = Column(Boolean, nullable=False, default=True)
    include_ux_metrics = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### BusinessImpactDependencyDB
```python
class BusinessImpactDependencyDB(Base):
    """业务影响依赖关系表"""
    __tablename__ = "business_impact_dependencies"
    
    id = Column(String(50), primary_key=True)
    source_service = Column(String(200), nullable=False, index=True)
    target_service = Column(String(200), nullable=False, index=True)
    dependency_type = Column(String(50), nullable=False, default="api_call")
    criticality = Column(String(50), nullable=False, default="medium", index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### BusinessImpactReportDB
```python
class BusinessImpactReportDB(Base):
    """业务影响报告表"""
    __tablename__ = "business_impact_reports"
    
    id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    service_names = Column(JSON, nullable=False)
    time_range = Column(String(50), nullable=False, default="24h")
    include_recommendations = Column(Boolean, nullable=False, default=True)
    summary = Column(JSON, nullable=True)
    service_data = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 混沌工程模型

#### ChaosExperimentDB
```python
class ChaosExperimentDB(Base):
    """混沌工程实验表"""
    __tablename__ = "chaos_experiments"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    experiment_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=True)
    severity = Column(String(50), nullable=False, default="medium", index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    tags = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### ChaosScenarioDB
```python
class ChaosScenarioDB(Base):
    """混沌工程场景表"""
    __tablename__ = "chaos_scenarios"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    fault_types = Column(JSON, nullable=False)
    target_services = Column(JSON, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    auto_rollback = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### ChaosFaultDB
```python
class ChaosFaultDB(Base):
    """混沌工程故障表"""
    __tablename__ = "chaos_faults"
    
    id = Column(String(50), primary_key=True)
    fault_type = Column(String(50), nullable=False, index=True)
    target = Column(String(200), nullable=False)
    parameters = Column(JSON, nullable=False)
    severity = Column(String(50), nullable=False, default="medium")
    status = Column(String(50), nullable=False, default="pending")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

## 迁移步骤

### 1. 数据库准备

```bash
# 配置数据库连接
export DATABASE_URL=sqlite:///data/aiops.db

# 运行迁移
python -m alembic upgrade head
```

### 2. 数据迁移

```bash
# 运行数据一致性验证
python scripts/validate_business_impact_migration.py
```

### 3. 双写实现

在路由中实现双写逻辑：

```python
from core.auth_db import get_session
from core.models import BusinessImpactAnalysisDB

def _save_analysis_to_db(db: Session, analysis: Dict[str, Any]) -> None:
    """保存分析到数据库"""
    try:
        db_analysis = BusinessImpactAnalysisDB(
            id=analysis["id"],
            service_name=analysis["service_name"],
            # ... 其他字段
        )
        db.merge(db_analysis)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save to database: {str(e)}")

# 在API端点中使用
@router.post("/analysis")
async def create_analysis(request: CreateAnalysisRequest):
    # 保存到JSON文件
    _save_json_file(ANALYSIS_FILE, analyses)
    
    # 双写到数据库
    db = get_session()
    try:
        _save_analysis_to_db(db, analysis)
    except Exception as e:
        # 记录错误但继续使用JSON存储
        pass
    finally:
        db.close()
```

## 测试

### 数据库迁移测试

```bash
# 运行数据库迁移测试
python -m pytest tests/test_database_migration.py -v
```

### 双写逻辑测试

```bash
# 运行双写逻辑测试
python -m pytest tests/test_dual_write_logic.py -v
```

### 数据一致性测试

```bash
# 运行数据一致性测试
python -m pytest tests/test_data_consistency.py -v
```

### 安全审计测试

```bash
# 运行安全审计测试
python -m pytest tests/test_security_audit.py -v
```

### 性能基准测试

```bash
# 运行性能基准测试
python -m pytest tests/test_performance_benchmark.py -v
```

## 验证

### 数据一致性验证

使用验证脚本检查JSON文件和数据库的一致性：

```bash
python scripts/validate_business_impact_migration.py
```

### 索引验证

验证数据库索引是否正确创建：

```python
from sqlalchemy import inspect

inspector = inspect(engine)
indexes = inspector.get_indexes("business_impact_analysis")
print(indexes)
```

## 回退计划

如果需要回退到JSON文件存储：

1. 停止双写逻辑
2. 确保JSON文件包含所有最新数据
3. 更新配置以禁用数据库连接
4. 保留数据库作为备份

## 性能优化

### 索引优化

- 为常用查询字段添加索引
- 使用复合索引优化复杂查询
- 定期分析查询性能

### 批量操作

- 使用批量插入减少数据库往返
- 实现批量更新操作
- 优化事务大小

### 连接池

- 配置适当的连接池大小
- 监控连接使用情况
- 实现连接重用机制

## 安全考虑

### 数据加密

- 敏感字段加密存储
- 使用TLS加密数据库连接
- 定期轮换加密密钥

### 访问控制

- 实现基于角色的访问控制
- 启用ABAC权限控制
- 定期审计访问日志

### 备份策略

- 定期备份数据库
- 实现增量备份
- 测试恢复流程

## 监控

### 数据库监控

- 监控数据库连接数
- 跟踪查询性能
- 监控慢查询

### 一致性监控

- 定期运行一致性检查
- 监控双写失败率
- 跟踪数据差异

### 性能监控

- 监控API响应时间
- 跟踪数据库操作时间
- 监控系统资源使用

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库连接字符串
   - 验证数据库服务状态
   - 检查网络连接

2. **迁移脚本失败**
   - 检查Alembic版本
   - 验证数据库权限
   - 检查SQL语法

3. **数据不一致**
   - 运行一致性验证脚本
   - 检查双写逻辑
   - 验证事务处理

### 日志分析

```bash
# 查看数据库迁移日志
tail -f logs/database_migration.log

# 查看双写错误日志
tail -f logs/dual_write_errors.log
```

## 参考资料

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Database Migration Best Practices](https://www.postgresql.org/docs/current/migration.html)

## 更新日志

### 2024-08-27
- 完成业务影响高级路由迁移
- 完成混沌工程高级路由迁移
- 添加数据一致性验证脚本
- 实现双写逻辑
- 完成测试套件