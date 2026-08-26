# 数据库模型清单报告

## 执行摘要

基于对core/models.py的分析，发现项目已有45个模型（包括枚举类），其中41个是SQLAlchemy ORM模型。大部分告警相关模型已存在，但缺少AI功能、合规审计、构建器等关键模型。

## 已有模型统计

**总模型数**: 45个
**SQLAlchemy ORM模型**: 41个
**枚举类**: 4个

## 已有模型分类

### 1. 用户和认证
- User - 用户表

### 2. 告警管理 (18个模型)
- Alert - 告警表
- AlertConfiguration - 告警配置表
- NotificationChannel - 通知通道表
- AlertEscalationRule - 告警升级规则表
- AlertSuppressionRule - 告警抑制规则表
- AlertForwardingRule - 告警转发规则表
- AlertWebhookConfig - 告警Webhook配置表
- AlertDynamicThresholdRule - 告警动态阈值规则表
- AlertDeduplicationRule - 告警去重规则表
- AlertAggregationRule - 告警聚合规则表
- AlertRoutingRule - 告警路由规则表
- AlertRule - 告警规则表
- AlertIntegration - 告警集成表
- AlertAcknowledgement - 告警确认表
- PriorityRule - 优先级规则表
- PriorityScore - 优先级分数表
- PriorityHistory - 优先级历史表

### 3. 修复和审批
- RepairRecord - 修复记录表
- PendingApproval - 待审批表

### 4. 审计和日志
- AuditLog - 审计日志表

### 5. 指标和性能
- Metrics - 指标表
- SystemMetrics - 系统指标表
- PerformanceMetric - 性能指标表
- PerformanceBaseline - 性能基线表
- PerformanceTrend - 性能趋势表
- PerformanceRegression - 性能回归表

### 6. 工作流
- Workflow - 工作流表
- WorkflowExecution - 工作流执行表

### 7. 知识库
- Knowledge - 知识表

### 8. 备份和配置
- Backup - 备份表
- Config - 配置表
- Snapshot - 快照表

### 9. 实时数据
- RealtimeStream - 实时流表
- RealtimeEvent - 实时事件表
- RealtimeSubscription - 实时订阅表
- RealtimeWebhook - 实时Webhook表

### 10. 根因分析
- RootCauseHypothesis - 根因假设表
- RootCauseExperiment - 根因实验表
- RootCauseEvidence - 根因证据表
- RootCauseConclusion - 根因结论表

## 缺失模型

### 1. AI功能相关
- FineTuningJob - AI微调任务表
- TrainingDataset - 训练数据集表
- ModelDeployment - 模型部署表

### 2. 合规审计相关
- ComplianceAudit - 合规审计表

### 3. 构建器相关
- BuilderTemplate - 构建器模板表
- BuilderProject - 构建器项目表
- BuilderComponent - 构建器组件表

## 模型设计建议

### FineTuningJob模型
```python
class FineTuningJob(Base):
    """AI微调任务表"""
    __tablename__ = "fine_tuning_jobs"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    model_name = Column(String(100), nullable=False)
    dataset_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    parameters = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)
```

### TrainingDataset模型
```python
class TrainingDataset(Base):
    """训练数据集表"""
    __tablename__ = "training_datasets"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(String(50), nullable=False)
    size = Column(Integer, nullable=True)
    file_path = Column(String(500), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)
```

### ModelDeployment模型
```python
class ModelDeployment(Base):
    """模型部署表"""
    __tablename__ = "model_deployments"
    
    id = Column(String(100), primary_key=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    environment = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    endpoint = Column(String(500), nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deployed_by = Column(String(50), nullable=True)
```

### ComplianceAudit模型
```python
class ComplianceAudit(Base):
    """合规审计表"""
    __tablename__ = "compliance_audits"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    audit_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    scope = Column(JSON, nullable=True)
    findings = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)
```

### BuilderTemplate模型
```python
class BuilderTemplate(Base):
    """构建器模板表"""
    __tablename__ = "builder_templates"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    template_data = Column(JSON, nullable=False)
    components = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)
```

### BuilderProject模型
```python
class BuilderProject(Base):
    """构建器项目表"""
    __tablename__ = "builder_projects"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    template_id = Column(String(100), nullable=True)
    project_data = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)
```

### BuilderComponent模型
```python
class BuilderComponent(Base):
    """构建器组件表"""
    __tablename__ = "builder_components"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    component_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False)
    properties = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)
```

## 下一步行动

1. 在core/models.py中添加7个缺失的模型
2. 创建Alembic迁移脚本
3. 测试模型创建和验证

## 证据链

- 模型统计: 通过grep命令统计45个模型
- 模型分析: 通过read工具分析模型定义
- 缺失模型识别: 对比计划需求和现有模型

## 对应测试

- 验证模型清单准确性: 通过代码分析验证
- 检查模型定义完整性: 通过SQLAlchemy验证
