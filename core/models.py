# -*- coding: utf-8 -*-
# core/models.py
# SQLAlchemy ORM Models for AIOps Agent
# All database table definitions for PostgreSQL
# Using SQLAlchemy 1.x style for Python 3.14 compatibility

from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from core.database import Base


class AlertSeverity(str, Enum):
    """告警严重程度枚举"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class AlertStatus(str, Enum):
    """告警状态枚举"""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class RepairStatus(str, Enum):
    """修复状态枚举"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """审批状态枚举"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # admin, user, operator
    disabled = Column(Boolean, default=False, nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # MFA相关
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    recovery_codes = Column(Text, nullable=True)  # JSON string

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Alert(Base):
    """告警表"""

    __tablename__ = "alerts"

    id = Column(String(100), primary_key=True)
    level = Column(String(20), nullable=False, index=True)
    category = Column(String(50), nullable=True, index=True)
    alert_type = Column(String(50), nullable=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # 指标相关
    metric = Column(String(100), nullable=True)
    value = Column(Float, nullable=True)

    # 时间戳
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_time = Column(DateTime(timezone=True), nullable=True)

    # 状态
    status = Column(String(20), default=AlertStatus.PENDING.value, nullable=False, index=True)

    # 主机信息
    host = Column(String(100), nullable=True, index=True)
    platform = Column(String(20), nullable=False, default="windows")

    # 优先级
    priority = Column(String(10), default="P3", nullable=False)  # P0, P1, P2, P3
    bis_score = Column(Float, nullable=True)

    # 附加信息（JSON格式）
    meta_data = Column(JSON, nullable=True)

    # 去重相关
    prev_suppressed = Column(Integer, nullable=True)

    # 审批相关
    approval_id = Column(String(100), nullable=True)

    # 修复相关
    repair_id = Column(String(100), nullable=True)

    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_alerts_detected_at", "detected_at"),
        Index("idx_alerts_level_status", "level", "status"),
        Index("idx_alerts_host_level", "host", "level"),
    )

    def __repr__(self):
        return f"<Alert(id='{self.id}', level='{self.level}', title='{self.title}')>"


class RepairRecord(Base):
    """修复记录表"""

    __tablename__ = "repair_records"

    id = Column(String(100), primary_key=True)

    # 关联告警
    alert_id = Column(String(100), nullable=True, index=True)
    alert_time = Column(DateTime(timezone=True), nullable=True)

    # 修复脚本信息
    script_key = Column(String(100), nullable=False, index=True)
    script_name = Column(String(200), nullable=False)

    # 修复结果
    success = Column(Boolean, nullable=False, index=True)
    status = Column(String(20), default=RepairStatus.SUCCESS.value, nullable=False, index=True)

    # 执行信息
    repair_time = Column(DateTime(timezone=True), nullable=False, index=True)
    repair_duration_sec = Column(Float, nullable=False)

    # 平台
    platform = Column(String(20), nullable=False, default="windows")
    host = Column(String(100), nullable=True)

    # 输出
    output = Column(Text, nullable=False)
    error = Column(Text, nullable=True)
    return_code = Column(Integer, nullable=False)

    # 风险等级
    risk = Column(String(20), nullable=False)  # low, medium, high, critical

    # 参数
    params = Column(JSON, nullable=True)

    # 审批相关
    approval_id = Column(String(100), nullable=True)

    # 执行者
    executor = Column(String(100), nullable=True)  # 用户名或system

    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_repair_records_alert_id", "alert_id"),
        Index("idx_repair_records_success", "success"),
        Index("idx_repair_records_repair_time", "repair_time"),
        Index("idx_repair_records_script_key", "script_key"),
    )

    def __repr__(self):
        return (
            f"<RepairRecord(id='{self.id}', script='{self.script_name}', success={self.success})>"
        )


class PendingApproval(Base):
    """待审批记录表"""

    __tablename__ = "pending_approvals"

    id = Column(String(100), primary_key=True)

    # 关联告警
    alert_id = Column(String(100), nullable=False, index=True)
    alert_json = Column(Text, nullable=False)  # JSON string

    # 修复方案
    rule_name = Column(String(100), nullable=False)
    script_key = Column(String(100), nullable=False)
    proposal = Column(Text, nullable=False)

    # 状态
    status = Column(String(20), default=ApprovalStatus.PENDING.value, nullable=False, index=True)

    # 风险评估
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical

    # 审批人
    approver = Column(String(50), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # 提交时间
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_pending_approvals_alert_id", "alert_id"),
        Index("idx_pending_approvals_status", "status"),
        Index("idx_pending_approvals_submitted_at", "submitted_at"),
    )

    def __repr__(self):
        return (
            f"<PendingApproval(id='{self.id}', status='{self.status}', risk='{self.risk_level}')>"
        )


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 用户信息
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(50), nullable=True)

    # 操作信息
    action = Column(String(50), nullable=False, index=True)  # create, update, delete, execute
    resource_type = Column(String(50), nullable=False, index=True)  # alert, repair, approval
    resource_id = Column(String(100), nullable=True)

    # 请求信息
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # 操作结果
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)

    # 变更详情（JSON格式）
    changes = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 索引
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_resource_type", "resource_type"),
        Index("idx_audit_logs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user='{self.username}')>"


class Metrics(Base):
    """指标数据表"""

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 指标名称
    metric_name = Column(String(100), nullable=False, index=True)

    # 主机信息
    host = Column(String(100), nullable=False, index=True)
    platform = Column(String(20), nullable=False, default="windows")

    # 指标值
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # %, ms, MB, etc.

    # 标签（JSON格式）
    tags = Column(JSON, nullable=True)

    # 时间戳
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_metrics_metric_name", "metric_name"),
        Index("idx_metrics_host", "host"),
        Index("idx_metrics_timestamp", "timestamp"),
        Index("idx_metrics_host_metric", "host", "metric_name"),
    )

    def __repr__(self):
        return (
            f"<Metrics(id={self.id}, metric='{self.metric_name}', "
            f"host='{self.host}', value={self.value})>"
        )


class SystemMetrics(Base):
    """系统指标表"""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 主机信息
    host = Column(String(100), nullable=False, index=True)
    platform = Column(String(20), nullable=False, default="windows")

    # CPU指标
    cpu_usage = Column(Float, nullable=True)
    cpu_cores = Column(Integer, nullable=True)

    # 内存指标
    memory_usage = Column(Float, nullable=True)
    memory_total = Column(Float, nullable=True)
    memory_available = Column(Float, nullable=True)

    # 磁盘指标
    disk_usage = Column(Float, nullable=True)
    disk_total = Column(Float, nullable=True)
    disk_available = Column(Float, nullable=True)

    # 网络指标
    network_in = Column(Float, nullable=True)
    network_out = Column(Float, nullable=True)

    # 时间戳
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_system_metrics_host", "host"),
        Index("idx_system_metrics_timestamp", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<SystemMetrics(id={self.id}, host='{self.host}', "
            f"cpu={self.cpu_usage}%, memory={self.memory_usage}%>"
        )


class Workflow(Base):
    """工作流表"""

    __tablename__ = "workflows"

    id = Column(String(100), primary_key=True)

    # 工作流信息
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 工作流定义（JSON格式）
    definition = Column(JSON, nullable=False)

    # 状态
    status = Column(
        String(20), default="active", nullable=False, index=True
    )  # active, paused, archived

    # 版本
    version = Column(Integer, default=1, nullable=False)

    # 创建者
    created_by = Column(String(50), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_workflows_status", "status"),
        Index("idx_workflows_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<Workflow(id='{self.id}', name='{self.name}', status='{self.status}')>"


class WorkflowExecution(Base):
    """工作流执行记录表"""

    __tablename__ = "workflow_executions"

    id = Column(String(100), primary_key=True)

    # 关联工作流
    workflow_id = Column(String(100), nullable=False, index=True)

    # 执行状态
    status = Column(
        String(20), default="running", nullable=False, index=True
    )  # running, completed, failed, cancelled

    # 执行结果
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # 执行时间
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_sec = Column(Float, nullable=True)

    # 触发信息
    triggered_by = Column(String(50), nullable=True)  # user, system, schedule
    trigger_source = Column(String(100), nullable=True)  # alert_id, manual, cron

    # 执行者
    executor = Column(String(50), nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_workflow_executions_workflow_id", "workflow_id"),
        Index("idx_workflow_executions_status", "status"),
        Index("idx_workflow_executions_started_at", "started_at"),
    )

    def __repr__(self):
        return (
            f"<WorkflowExecution(id='{self.id}', workflow_id='{self.workflow_id}', "
            f"status='{self.status}')>"
        )


class Knowledge(Base):
    """知识库表"""

    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 知识条目
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # 分类
    category = Column(String(50), nullable=True, index=True)
    tags = Column(JSON, nullable=True)  # List of tags

    # 元数据
    source = Column(String(100), nullable=True)  # 来源：manual, ai_generated, incident
    confidence = Column(Float, nullable=True)  # AI生成时的置信度

    # 关联告警
    related_alert_ids = Column(JSON, nullable=True)  # List of alert IDs

    # 创建者
    created_by = Column(String(50), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_knowledge_category", "category"),
        Index("idx_knowledge_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Knowledge(id={self.id}, title='{self.title}', category='{self.category}')>"


class Backup(Base):
    """备份记录表"""

    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 备份类型
    backup_type = Column(String(50), nullable=False, index=True)  # database, config, full

    # 备份信息
    name = Column(String(200), nullable=False)
    path = Column(String(500), nullable=False)
    size_bytes = Column(Integer, nullable=True)

    # 状态
    status = Column(
        String(20), default="completed", nullable=False, index=True
    )  # completed, failed, in_progress

    # 时间戳
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 创建者
    created_by = Column(String(50), nullable=True)

    # 保留策略
    retention_days = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_backups_backup_type", "backup_type"),
        Index("idx_backups_status", "status"),
        Index("idx_backups_started_at", "started_at"),
    )

    def __repr__(self):
        return (
            f"<Backup(id={self.id}, name='{self.name}', type='{self.backup_type}', "
            f"status='{self.status}')>"
        )


class Config(Base):
    """配置表"""

    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 配置键值
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)

    # 配置元数据
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)

    # 敏感标记
    is_sensitive = Column(Boolean, default=False, nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 更新者
    updated_by = Column(String(50), nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_configs_key", "key"),
        Index("idx_configs_category", "category"),
    )

    def __repr__(self):
        return f"<Config(id={self.id}, key='{self.key}', category='{self.category}')>"


# ==================== Performance Metrics Models ====================


class PerformanceMetric(Base):
    """性能指标表"""

    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 测试标识
    test_id = Column(String(100), nullable=False, index=True)
    test_name = Column(String(200), nullable=False)
    test_type = Column(String(50), nullable=False, index=True)  # api, database, ai

    # 组件信息
    component = Column(String(100), nullable=False, index=True)  # api端点、数据库表、AI模型
    operation = Column(String(100), nullable=False)

    # 性能指标
    mean_time_ms = Column(Float, nullable=False)
    min_time_ms = Column(Float, nullable=False)
    max_time_ms = Column(Float, nullable=False)
    p50_time_ms = Column(Float, nullable=True)
    p95_time_ms = Column(Float, nullable=True)
    p99_time_ms = Column(Float, nullable=True)
    std_dev_ms = Column(Float, nullable=True)

    # 吞吐量指标
    throughput_ops = Column(Float, nullable=True)
    qps = Column(Float, nullable=True)

    # 错误率
    error_rate = Column(Float, nullable=True)
    error_count = Column(Integer, nullable=True)
    total_requests = Column(Integer, nullable=False)

    # 资源使用
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_io = Column(Float, nullable=True)
    network_io = Column(Float, nullable=True)

    # AI特定指标
    token_usage = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    model_name = Column(String(100), nullable=True)

    # 数据库特定指标
    data_volume = Column(String(50), nullable=True)  # 1K, 10K, 100K, etc.
    pool_size = Column(Integer, nullable=True)
    connection_count = Column(Integer, nullable=True)

    # 环境信息
    environment = Column(String(50), nullable=False, index=True)  # dev, staging, prod
    git_commit = Column(String(50), nullable=True)
    git_branch = Column(String(50), nullable=True)

    # 时间戳
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # 元数据
    meta_data = Column(JSON, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_performance_metrics_test_id", "test_id"),
        Index("idx_performance_metrics_test_type", "test_type"),
        Index("idx_performance_metrics_component", "component"),
        Index("idx_performance_metrics_timestamp", "timestamp"),
        Index("idx_performance_metrics_environment", "environment"),
    )

    def __repr__(self):
        return f"<PerformanceMetric(id={
            self.id}, test_id='{
            self.test_id}', component='{
            self.component}')>"


class PerformanceBaseline(Base):
    """性能基准表"""

    __tablename__ = "performance_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基准标识
    baseline_id = Column(String(100), unique=True, nullable=False, index=True)
    baseline_name = Column(String(200), nullable=False)
    baseline_type = Column(String(50), nullable=False)  # api, database, ai

    # 组件信息
    component = Column(String(100), nullable=False, index=True)
    operation = Column(String(100), nullable=False)

    # 基准值
    target_p95_ms = Column(Float, nullable=False)
    target_p99_ms = Column(Float, nullable=True)
    target_throughput = Column(Float, nullable=True)
    target_error_rate = Column(Float, nullable=True)

    # 回归阈值
    regression_threshold = Column(Float, default=0.1, nullable=False)  # 10%
    critical_threshold = Column(Float, default=0.3, nullable=False)  # 30%

    # 环境信息
    environment = Column(String(50), nullable=False, index=True)

    # 生效时间
    effective_from = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=True)

    # 创建者
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_performance_baselines_baseline_id", "baseline_id"),
        Index("idx_performance_baselines_component", "component"),
        Index("idx_performance_baselines_environment", "environment"),
        Index("idx_performance_baselines_is_active", "is_active"),
    )

    def __repr__(self):
        return f"<PerformanceBaseline(id={
            self.id}, baseline_id='{
            self.baseline_id}', component='{
            self.component}')>"


class PerformanceTrend(Base):
    """性能趋势表"""

    __tablename__ = "performance_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 趋势标识
    trend_id = Column(String(100), nullable=False, index=True)
    component = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)  # p95_time_ms, throughput, error_rate

    # 趋势数据
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    metric_value = Column(Float, nullable=False)

    # 趋势分析
    trend_direction = Column(String(20), nullable=True)  # up, down, stable
    trend_magnitude = Column(Float, nullable=True)  # 变化幅度
    trend_significance = Column(String(20), nullable=True)  # significant, normal

    # 对比基准
    baseline_value = Column(Float, nullable=True)
    deviation_from_baseline = Column(Float, nullable=True)

    # 环境信息
    environment = Column(String(50), nullable=False, index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_performance_trends_trend_id", "trend_id"),
        Index("idx_performance_trends_component", "component"),
        Index("idx_performance_trends_timestamp", "timestamp"),
        Index("idx_performance_trends_environment", "environment"),
    )

    def __repr__(self):
        return f"<PerformanceTrend(id={
            self.id}, trend_id='{
            self.trend_id}', component='{
            self.component}')>"


class PerformanceRegression(Base):
    """性能回归记录表"""

    __tablename__ = "performance_regressions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 回归标识
    regression_id = Column(String(100), unique=True, nullable=False, index=True)

    # 组件信息
    component = Column(String(100), nullable=False, index=True)
    operation = Column(String(100), nullable=False)

    # 回归详情
    baseline_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    deviation = Column(Float, nullable=False)  # 偏差百分比
    severity = Column(String(20), nullable=False)  # warning, critical

    # 时间信息
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    git_commit = Column(String(50), nullable=True)
    git_branch = Column(String(50), nullable=True)

    # 状态
    status = Column(String(20), default="open", nullable=False)  # open, acknowledged, resolved
    acknowledged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # 环境信息
    environment = Column(String(50), nullable=False, index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_performance_regressions_regression_id", "regression_id"),
        Index("idx_performance_regressions_component", "component"),
        Index("idx_performance_regressions_severity", "severity"),
        Index("idx_performance_regressions_status", "status"),
        Index("idx_performance_regressions_detected_at", "detected_at"),
    )

    def __repr__(self):
        return f"<PerformanceRegression(id={
            self.id}, regression_id='{
            self.regression_id}', component='{
            self.component}')>"
