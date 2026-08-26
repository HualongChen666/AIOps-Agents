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
    dataset_metadata = Column(JSON, nullable=True)

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
    dataset_metadata = Column(JSON, nullable=True)

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
    dataset_metadata = Column(JSON, nullable=True)

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
    dataset_metadata = Column(JSON, nullable=True)

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
    dataset_metadata = Column(JSON, nullable=True)

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


class Snapshot(Base):
    """操作前/后状态快照表（用于回滚与审计）"""

    __tablename__ = "snapshots"

    id = Column(String(100), primary_key=True)

    # 关联告警与修复
    alert_id = Column(String(100), nullable=False, index=True)
    repair_record_id = Column(String(100), nullable=True, index=True)

    # 操作类型: pod_restart, config_mod, scale, network_policy,
    #           service_restart, process_kill, disk_cleanup, network_fix, generic
    operation_type = Column(String(50), nullable=False, index=True)

    # 加密后的 JSON 内容
    pre_state = Column(Text, nullable=False)
    post_state = Column(Text, nullable=True)
    rollback_plan = Column(Text, nullable=True)

    # 快照状态: pending / success / failed / rollback_failed
    status = Column(String(20), default="pending", nullable=False, index=True)

    # 保留策略
    retention_days = Column(Integer, nullable=False, default=7)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_snapshots_alert_id", "alert_id"),
        Index("idx_snapshots_repair_record_id", "repair_record_id"),
        Index("idx_snapshots_operation_type", "operation_type"),
        Index("idx_snapshots_status", "status"),
        Index("idx_snapshots_expires_at", "expires_at"),
    )

    def __repr__(self):
        return (
            f"<Snapshot(id='{self.id}', alert_id='{self.alert_id}', "
            f"operation_type='{self.operation_type}', status='{self.status}')>"
        )


# ==================== Alert Management Models ====================


class AlertConfiguration(Base):
    """告警配置表"""

    __tablename__ = "alert_configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_configurations_key", "config_key"),
        Index("idx_alert_configurations_category", "category"),
    )

    def __repr__(self):
        return f"<AlertConfiguration(id={self.id}, key='{self.config_key}', category='{self.category}')>"


class NotificationChannel(Base):
    """通知通道表"""

    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    channel_type = Column(String(50), nullable=False, index=True)  # email, slack, webhook, sms
    config = Column(JSON, nullable=False)  # channel-specific configuration
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)  # higher priority = used first
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_notification_channels_name", "name"),
        Index("idx_notification_channels_type", "channel_type"),
        Index("idx_notification_channels_enabled", "enabled"),
    )

    def __repr__(self):
        return (
            f"<NotificationChannel(id={self.id}, name='{self.name}', type='{self.channel_type}')>"
        )


class AlertEscalationRule(Base):
    """告警升级规则表"""

    __tablename__ = "alert_escalation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    conditions = Column(JSON, nullable=False)  # escalation conditions
    escalation_levels = Column(JSON, nullable=False)  # escalation levels and targets
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_escalation_rules_name", "name"),
        Index("idx_alert_escalation_rules_rule_id", "rule_id"),
        Index("idx_alert_escalation_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertEscalationRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertSuppressionRule(Base):
    """告警抑制规则表"""

    __tablename__ = "alert_suppression_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    pattern = Column(String(500), nullable=False)  # suppression pattern
    reason = Column(Text, nullable=False)
    suppression_window = Column(Integer, default=300, nullable=False)  # seconds
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_suppression_rules_name", "name"),
        Index("idx_alert_suppression_rules_rule_id", "rule_id"),
        Index("idx_alert_suppression_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertSuppressionRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertForwardingRule(Base):
    """告警转发规则表"""

    __tablename__ = "alert_forwarding_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    conditions = Column(JSON, nullable=False)  # forwarding conditions
    destination = Column(String(200), nullable=False)  # destination endpoint
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_forwarding_rules_name", "name"),
        Index("idx_alert_forwarding_rules_rule_id", "rule_id"),
        Index("idx_alert_forwarding_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertForwardingRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertWebhookConfig(Base):
    """告警Webhook配置表"""

    __tablename__ = "alert_webhook_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    webhook_id = Column(String(100), unique=True, nullable=False, index=True)
    url = Column(String(500), nullable=False)
    method = Column(String(10), default="POST", nullable=False)  # GET, POST, PUT, DELETE
    headers = Column(JSON, nullable=True)  # HTTP headers
    body_template = Column(Text, nullable=True)  # request body template
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    retry_policy = Column(JSON, nullable=True)  # retry configuration
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_webhook_configs_name", "name"),
        Index("idx_alert_webhook_configs_webhook_id", "webhook_id"),
        Index("idx_alert_webhook_configs_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertWebhookConfig(id={self.id}, name='{self.name}', webhook_id='{self.webhook_id}')>"


class AlertDynamicThresholdRule(Base):
    """动态阈值规则表"""

    __tablename__ = "alert_dynamic_threshold_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)  # anomaly_detection, percentile, adaptive
    parameters = Column(JSON, nullable=False)  # algorithm parameters
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_dynamic_threshold_rules_name", "name"),
        Index("idx_alert_dynamic_threshold_rules_rule_id", "rule_id"),
        Index("idx_alert_dynamic_threshold_rules_metric", "metric_name"),
        Index("idx_alert_dynamic_threshold_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertDynamicThresholdRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertDeduplicationRule(Base):
    """告警去重规则表"""

    __tablename__ = "alert_deduplication_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    dedup_fields = Column(JSON, nullable=False)  # fields used for deduplication
    dedup_window = Column(Integer, default=300, nullable=False)  # seconds
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_deduplication_rules_name", "name"),
        Index("idx_alert_deduplication_rules_rule_id", "rule_id"),
        Index("idx_alert_deduplication_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return (
            f"<AlertDeduplicationRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"
        )


class AlertAggregationRule(Base):
    """告警聚合规则表"""

    __tablename__ = "alert_aggregation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    aggregation_fields = Column(JSON, nullable=False)  # fields used for aggregation
    aggregation_window = Column(Integer, default=300, nullable=False)  # seconds
    aggregation_function = Column(String(50), default="count", nullable=False)  # count, sum, avg
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_aggregation_rules_name", "name"),
        Index("idx_alert_aggregation_rules_rule_id", "rule_id"),
        Index("idx_alert_aggregation_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertAggregationRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertRoutingRule(Base):
    """告警路由规则表"""

    __tablename__ = "alert_routing_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    conditions = Column(JSON, nullable=False)  # routing conditions
    destination = Column(String(200), nullable=False)  # routing destination
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_routing_rules_name", "name"),
        Index("idx_alert_routing_rules_rule_id", "rule_id"),
        Index("idx_alert_routing_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertRoutingRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertRule(Base):
    """告警规则表"""

    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    condition = Column(String(50), nullable=False)  # >, <, >=, <=, ==, !=
    threshold = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)  # info, warning, critical, fatal
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_rules_name", "name"),
        Index("idx_alert_rules_rule_id", "rule_id"),
        Index("idx_alert_rules_metric", "metric_name"),
        Index("idx_alert_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AlertRule(id={self.id}, name='{self.name}', rule_id='{self.rule_id}')>"


class AlertIntegration(Base):
    """告警集成配置表"""

    __tablename__ = "alert_integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    integration_type = Column(
        String(50), nullable=False, index=True
    )  # zabbix, cloudwatch, pagerduty, datadog, grafana, prometheus
    name = Column(String(100), unique=True, nullable=False, index=True)
    config = Column(JSON, nullable=False)  # integration-specific configuration
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_alert_integrations_type", "integration_type"),
        Index("idx_alert_integrations_name", "name"),
        Index("idx_alert_integrations_enabled", "enabled"),
    )

    def __repr__(self):
        return (
            f"<AlertIntegration(id={self.id}, type='{self.integration_type}', name='{self.name}')>"
        )


class AlertAcknowledgement(Base):
    """告警确认记录表"""

    __tablename__ = "alert_acknowledgements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(100), nullable=False, index=True)
    acknowledged_by = Column(String(50), nullable=False)
    acknowledged_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    comment = Column(Text, nullable=True)
    status = Column(String(20), default="acknowledged", nullable=False)  # acknowledged, resolved

    __table_args__ = (
        Index("idx_alert_acknowledgements_alert_id", "alert_id"),
        Index("idx_alert_acknowledgements_acknowledged_at", "acknowledged_at"),
    )

    def __repr__(self):
        return f"<AlertAcknowledgement(id={self.id}, alert_id='{self.alert_id}', acknowledged_by='{self.acknowledged_by}')>"


# ==================== Priority Management Models ====================


class PriorityRule(Base):
    """优先级规则表"""

    __tablename__ = "priority_rules"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 规则条件
    conditions = Column(JSON, nullable=False)  # 规则条件配置
    priority_level = Column(String(10), nullable=False)  # P0, P1, P2, P3, P4
    weight = Column(Float, default=1.0, nullable=False)  # 权重

    # 规则状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_priority_rules_name", "name"),
        Index("idx_priority_rules_enabled", "enabled"),
        Index("idx_priority_rules_priority_level", "priority_level"),
    )

    def __repr__(self):
        return (
            f"<PriorityRule(id='{self.id}', name='{self.name}', priority='{self.priority_level}')>"
        )


class PriorityScore(Base):
    """优先级分数表"""

    __tablename__ = "priority_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联告警
    alert_id = Column(String(100), nullable=False, index=True)

    # 优先级分数
    priority_level = Column(String(10), nullable=False)  # P0, P1, P2, P3, P4
    score = Column(Float, nullable=False)  # 0-100
    bis_score = Column(Float, nullable=True)  # 业务影响分数

    # 分数详情
    factors = Column(JSON, nullable=True)  # 各因素分数详情

    # 时间戳
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_priority_scores_alert_id", "alert_id"),
        Index("idx_priority_scores_priority_level", "priority_level"),
        Index("idx_priority_scores_calculated_at", "calculated_at"),
    )

    def __repr__(self):
        return f"<PriorityScore(id={self.id}, alert_id='{self.alert_id}', score={self.score})>"


class PriorityHistory(Base):
    """优先级历史表"""

    __tablename__ = "priority_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联告警
    alert_id = Column(String(100), nullable=False, index=True)

    # 优先级变更
    old_priority = Column(String(10), nullable=True)
    new_priority = Column(String(10), nullable=False)
    old_score = Column(Float, nullable=True)
    new_score = Column(Float, nullable=False)

    # 变更原因
    change_reason = Column(String(200), nullable=True)
    changed_by = Column(String(50), nullable=True)  # 用户名或system

    # 时间戳
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_priority_history_alert_id", "alert_id"),
        Index("idx_priority_history_changed_at", "changed_at"),
    )

    def __repr__(self):
        return f"<PriorityHistory(id={self.id}, alert_id='{self.alert_id}', old='{self.old_priority}', new='{self.new_priority}')>"


# ==================== Realtime Models ====================


class RealtimeStream(Base):
    """实时流表"""

    __tablename__ = "realtime_streams"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 流配置
    stream_type = Column(String(50), nullable=False, index=True)  # sse, websocket, kafka
    source = Column(String(200), nullable=True)  # 数据源
    config = Column(JSON, nullable=False)  # 流配置

    # 流状态
    status = Column(
        String(20), default="active", nullable=False, index=True
    )  # active, paused, stopped

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_realtime_streams_name", "name"),
        Index("idx_realtime_streams_type", "stream_type"),
        Index("idx_realtime_streams_status", "status"),
    )

    def __repr__(self):
        return f"<RealtimeStream(id='{self.id}', name='{self.name}', type='{self.stream_type}')>"


class RealtimeEvent(Base):
    """实时事件表"""

    __tablename__ = "realtime_events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联流
    stream_id = Column(String(100), nullable=True, index=True)

    # 事件数据
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)

    # 时间戳
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_realtime_events_stream_id", "stream_id"),
        Index("idx_realtime_events_type", "event_type"),
        Index("idx_realtime_events_timestamp", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<RealtimeEvent(id={self.id}, stream_id='{self.stream_id}', type='{self.event_type}')>"
        )


class RealtimeSubscription(Base):
    """实时订阅表"""

    __tablename__ = "realtime_subscriptions"

    id = Column(String(100), primary_key=True)

    # 订阅配置
    stream_id = Column(String(100), nullable=False, index=True)
    subscriber_id = Column(String(100), nullable=False, index=True)  # 用户ID或服务ID
    subscription_type = Column(String(50), nullable=False)  # sse, websocket

    # 过滤条件
    filters = Column(JSON, nullable=True)  # 订阅过滤条件

    # 订阅状态
    status = Column(
        String(20), default="active", nullable=False, index=True
    )  # active, paused, cancelled

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_realtime_subscriptions_stream_id", "stream_id"),
        Index("idx_realtime_subscriptions_subscriber_id", "subscriber_id"),
        Index("idx_realtime_subscriptions_status", "status"),
    )

    def __repr__(self):
        return f"<RealtimeSubscription(id='{self.id}', stream_id='{self.stream_id}', subscriber='{self.subscriber_id}')>"


class RealtimeWebhook(Base):
    """实时Webhook表"""

    __tablename__ = "realtime_webhooks"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Webhook配置
    url = Column(String(500), nullable=False)
    method = Column(String(10), default="POST", nullable=False)  # GET, POST, PUT, DELETE
    headers = Column(JSON, nullable=True)  # HTTP headers
    body_template = Column(Text, nullable=True)  # 请求体模板

    # 关联流
    stream_id = Column(String(100), nullable=True, index=True)

    # Webhook状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # 重试策略
    retry_policy = Column(JSON, nullable=True)  # 重试配置

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_realtime_webhooks_name", "name"),
        Index("idx_realtime_webhooks_stream_id", "stream_id"),
        Index("idx_realtime_webhooks_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<RealtimeWebhook(id='{self.id}', name='{self.name}', url='{self.url}')>"


# ==================== Root Cause Analysis Models ====================


class RootCauseHypothesis(Base):
    """根因假设表"""

    __tablename__ = "root_cause_hypotheses"

    id = Column(String(100), primary_key=True)

    # 关联告警
    alert_id = Column(String(100), nullable=False, index=True)

    # 假设内容
    root_cause = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # 置信度和影响
    confidence = Column(Float, nullable=False)  # 0-1
    impact_score = Column(Float, nullable=False)  # 0-1

    # 证据和因果路径
    evidence = Column(JSON, nullable=True)  # 证据列表
    causal_path = Column(JSON, nullable=True)  # 因果路径

    # 验证状态
    verification_status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, verified, rejected
    verification_timestamp = Column(DateTime(timezone=True), nullable=True)

    # 假设状态
    status = Column(String(20), default="active", nullable=False, index=True)  # active, archived

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_root_cause_hypotheses_alert_id", "alert_id"),
        Index("idx_root_cause_hypotheses_verification_status", "verification_status"),
        Index("idx_root_cause_hypotheses_status", "status"),
        Index("idx_root_cause_hypotheses_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<RootCauseHypothesis(id='{self.id}', alert_id='{self.alert_id}', root_cause='{self.root_cause}')>"


class RootCauseExperiment(Base):
    """根因实验表"""

    __tablename__ = "root_cause_experiments"

    id = Column(String(100), primary_key=True)

    # 关联假设
    hypothesis_id = Column(String(100), nullable=False, index=True)

    # 实验配置
    experiment_type = Column(String(50), nullable=False)  # verification, mitigation
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=False)  # 实验参数

    # 实验结果
    result = Column(JSON, nullable=True)  # 实验结果
    success = Column(Boolean, nullable=True)
    conclusion = Column(Text, nullable=True)

    # 实验状态
    status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, running, completed, failed

    # 时间戳
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_root_cause_experiments_hypothesis_id", "hypothesis_id"),
        Index("idx_root_cause_experiments_status", "status"),
        Index("idx_root_cause_experiments_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<RootCauseExperiment(id='{self.id}', hypothesis_id='{self.hypothesis_id}', status='{self.status}')>"


class RootCauseEvidence(Base):
    """根因证据表"""

    __tablename__ = "root_cause_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联假设
    hypothesis_id = Column(String(100), nullable=False, index=True)

    # 证据内容
    evidence_type = Column(String(50), nullable=False, index=True)  # metric, log, trace, topology
    evidence_data = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)

    # 证据强度
    strength = Column(Float, nullable=False)  # 0-1

    # 时间戳
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_root_cause_evidence_hypothesis_id", "hypothesis_id"),
        Index("idx_root_cause_evidence_type", "evidence_type"),
        Index("idx_root_cause_evidence_collected_at", "collected_at"),
    )

    def __repr__(self):
        return f"<RootCauseEvidence(id={self.id}, hypothesis_id='{self.hypothesis_id}', type='{self.evidence_type}')>"


class RootCauseConclusion(Base):
    """根因结论表"""

    __tablename__ = "root_cause_conclusions"

    id = Column(String(100), primary_key=True)

    # 关联告警
    alert_id = Column(String(100), nullable=False, index=True)

    # 结论内容
    root_cause = Column(String(500), nullable=False)
    summary = Column(Text, nullable=False)
    detailed_analysis = Column(Text, nullable=True)

    # 置信度
    confidence = Column(Float, nullable=False)  # 0-1

    # 关联假设
    verified_hypothesis_id = Column(String(100), nullable=True, index=True)

    # 推荐操作
    recommended_actions = Column(JSON, nullable=True)  # 推荐操作列表

    # 结论状态
    status = Column(
        String(20), default="draft", nullable=False, index=True
    )  # draft, final, archived

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    dataset_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_root_cause_conclusions_alert_id", "alert_id"),
        Index("idx_root_cause_conclusions_status", "status"),
        Index("idx_root_cause_conclusions_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<RootCauseConclusion(id='{self.id}', alert_id='{self.alert_id}', root_cause='{self.root_cause}')>"


# ============================================================================
# AI Functionality Models
# ============================================================================


class FineTuningJob(Base):
    """AI微调任务表"""

    __tablename__ = "fine_tuning_jobs"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    model_name = Column(String(100), nullable=False)
    dataset_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    parameters = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_fine_tuning_jobs_status", "status"),
        Index("idx_fine_tuning_jobs_model_name", "model_name"),
        Index("idx_fine_tuning_jobs_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<FineTuningJob(id={self.id}, name='{self.name}', status='{self.status}')>"


class TrainingDataset(Base):
    """训练数据集表"""

    __tablename__ = "training_datasets"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(String(50), nullable=False, index=True)
    size = Column(Integer, nullable=True)
    file_path = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_training_datasets_data_type", "data_type"),
        Index("idx_training_datasets_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<TrainingDataset(id={self.id}, name='{self.name}', type='{self.data_type}')>"


class ModelDeployment(Base):
    """模型部署表"""

    __tablename__ = "model_deployments"

    id = Column(String(100), primary_key=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    environment = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    endpoint = Column(String(500), nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deployed_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_model_deployments_environment", "environment"),
        Index("idx_model_deployments_status", "status"),
        Index("idx_model_deployments_model_name", "model_name"),
    )

    def __repr__(self):
        return f"<ModelDeployment(id={self.id}, model='{self.model_name}', env='{self.environment}')>"


# ============================================================================
# Compliance Audit Models
# ============================================================================


class ComplianceAudit(Base):
    """合规审计表"""

    __tablename__ = "compliance_audits"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    audit_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    scope = Column(JSON, nullable=True)
    findings = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    completed_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_compliance_audits_type", "audit_type"),
        Index("idx_compliance_audits_status", "status"),
        Index("idx_compliance_audits_scheduled_date", "scheduled_date"),
    )

    def __repr__(self):
        return f"<ComplianceAudit(id={self.id}, name='{self.name}', type='{self.audit_type}')>"


# ============================================================================
# Builder Models
# ============================================================================


class BuilderTemplate(Base):
    """构建器模板表"""

    __tablename__ = "builder_templates"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    template_data = Column(JSON, nullable=False)
    components = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_builder_templates_category", "category"),
        Index("idx_builder_templates_is_public", "is_public"),
    )

    def __repr__(self):
        return f"<BuilderTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"


class BuilderProject(Base):
    """构建器项目表"""

    __tablename__ = "builder_projects"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    template_id = Column(String(100), nullable=True)
    project_data = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_builder_projects_status", "status"),
        Index("idx_builder_projects_template_id", "template_id"),
    )

    def __repr__(self):
        return f"<BuilderProject(id={self.id}, name='{self.name}', status='{self.status}')>"


class BuilderComponent(Base):
    """构建器组件表"""

    __tablename__ = "builder_components"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    component_type = Column(String(50), nullable=False, index=True)
    config = Column(JSON, nullable=False)
    properties = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_builder_components_type", "component_type"),
    )

    def __repr__(self):
        return f"<BuilderComponent(id={self.id}, name='{self.name}', type='{self.component_type}')>"


# ==================== Asset Management Models ====================


class AssetInventoryMetadata(Base):
    """资产库存元数据表"""

    __tablename__ = "asset_inventory_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, nullable=False, index=True)
    inventory_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_asset_inventory_metadata_asset_id", "asset_id"),
    )

    def __repr__(self):
        return f"<AssetInventoryMetadata(id={self.id}, asset_id={self.asset_id})>"


class AssetRelationshipDB(Base):
    """资产关系表"""

    __tablename__ = "asset_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, index=True)
    properties = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_asset_relationships_source_id", "source_id"),
        Index("idx_asset_relationships_target_id", "target_id"),
        Index("idx_asset_relationships_type", "relationship_type"),
    )

    def __repr__(self):
        return f"<AssetRelationshipDB(id={self.id}, source_id={self.source_id}, target_id={self.target_id}, type='{self.relationship_type}')>"


class AssetLifecycleDB(Base):
    """资产生命周期表"""

    __tablename__ = "asset_lifecycles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, nullable=False, index=True)
    stage = Column(String(50), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_asset_lifecycles_asset_id", "asset_id"),
        Index("idx_asset_lifecycles_stage", "stage"),
        Index("idx_asset_lifecycles_status", "status"),
    )

    def __repr__(self):
        return f"<AssetLifecycleDB(id={self.id}, asset_id={self.asset_id}, stage='{self.stage}', status='{self.status}')>"


class AssetDependencyDB(Base):
    """资产依赖表"""

    __tablename__ = "asset_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, nullable=False, index=True)
    dependency_type = Column(String(50), nullable=False, index=True)
    dependency_details = Column(JSON, nullable=False)
    criticality = Column(String(20), nullable=False, default="medium", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_asset_dependencies_asset_id", "asset_id"),
        Index("idx_asset_dependencies_type", "dependency_type"),
        Index("idx_asset_dependencies_criticality", "criticality"),
    )

    def __repr__(self):
        return f"<AssetDependencyDB(id={self.id}, asset_id={self.asset_id}, type='{self.dependency_type}', criticality='{self.criticality}')>"


# ==================== Capacity Planning Models ====================


class CapacityPlanDB(Base):
    """容量计划表"""

    __tablename__ = "capacity_plans"

    id = Column(String(20), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)
    service = Column(String(255), nullable=False, index=True)
    current_capacity = Column(Float, nullable=False)
    projected_capacity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    horizon = Column(String(50), nullable=False)
    target_date = Column(DateTime(timezone=True), nullable=True)
    threshold = Column(Float, nullable=False)
    recommended_action = Column(Text, nullable=False)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(50), nullable=False, default="system")
    status = Column(String(50), nullable=False, default="draft", index=True)
    plan_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_plans_resource_type", "resource_type"),
        Index("idx_capacity_plans_service", "service"),
        Index("idx_capacity_plans_status", "status"),
    )

    def __repr__(self):
        return f"<CapacityPlanDB(id={self.id}, name='{self.name}', service='{self.service}')>"


class OptimizationResultDB(Base):
    """优化结果表"""

    __tablename__ = "optimization_results"

    id = Column(String(20), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_types = Column(JSON, nullable=False)
    strategy = Column(String(50), nullable=False)
    current_usage = Column(JSON, nullable=False)
    optimized_usage = Column(JSON, nullable=False)
    savings = Column(Float, nullable=False)
    implementation_steps = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(50), nullable=False, default="system")
    status = Column(String(50), nullable=False, default="pending", index=True)
    opt_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_optimization_results_service", "service"),
        Index("idx_optimization_results_status", "status"),
    )

    def __repr__(self):
        return f"<OptimizationResultDB(id={self.id}, service='{self.service}', strategy='{self.strategy}')>"


class RightsizingRecommendationDB(Base):
    """右缩建议表"""

    __tablename__ = "rightsizing_recommendations"

    id = Column(String(20), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    current_spec = Column(JSON, nullable=False)
    recommended_spec = Column(JSON, nullable=False)
    action = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(String(50), nullable=False)
    estimated_monthly_savings = Column(Float, nullable=False)
    performance_impact = Column(Text, nullable=False)
    implementation_complexity = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rec_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_rightsizing_recommendations_service", "service"),
        Index("idx_rightsizing_recommendations_resource_type", "resource_type"),
    )

    def __repr__(self):
        return f"<RightsizingRecommendationDB(id={self.id}, service='{self.service}', type='{self.resource_type}')>"


# ==================== Cost Management Models ====================


class CostBudgetDB(Base):
    """成本预算表"""

    __tablename__ = "cost_budgets"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    service = Column(String(255), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    spent = Column(Float, nullable=False, default=0.0)
    remaining = Column(Float, nullable=False)
    period = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="on_track", index=True)
    alerts_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    budget_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_budgets_service", "service"),
        Index("idx_cost_budgets_status", "status"),
    )

    def __repr__(self):
        return f"<CostBudgetDB(id={self.id}, name='{self.name}', service='{self.service}')>"


class CostOptimizationDB(Base):
    """成本优化建议表"""

    __tablename__ = "cost_optimizations"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    optimization_type = Column(String(50), nullable=False)
    potential_savings = Column(Float, nullable=False)
    implementation_effort = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    opt_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_optimizations_service", "service"),
        Index("idx_cost_optimizations_priority", "priority"),
        Index("idx_cost_optimizations_status", "status"),
    )

    def __repr__(self):
        return f"<CostOptimizationDB(id={self.id}, service='{self.service}', type='{self.optimization_type}')>"


class CostAnomalyDB(Base):
    """成本异常表"""

    __tablename__ = "cost_anomalies"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    anomaly_type = Column(String(50), nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    severity = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    affected_amount = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="open", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    anomaly_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_anomalies_service", "service"),
        Index("idx_cost_anomalies_severity", "severity"),
        Index("idx_cost_anomalies_status", "status"),
    )

    def __repr__(self):
        return f"<CostAnomalyDB(id={self.id}, service='{self.service}', type='{self.anomaly_type}')>"


class CostAlertDB(Base):
    """成本告警表"""

    __tablename__ = "cost_alerts"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    alert_type = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    notification_channels = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    alert_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_alerts_service", "service"),
        Index("idx_cost_alerts_status", "status"),
    )

    def __repr__(self):
        return f"<CostAlertDB(id={self.id}, name='{self.name}', service='{self.service}')>"


class CostReportDB(Base):
    """成本报告表"""

    __tablename__ = "cost_reports"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    total_cost = Column(Float, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), nullable=False, default="completed", index=True)
    report_data = Column(JSON, nullable=False)
    report_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_reports_type", "report_type"),
        Index("idx_cost_reports_status", "status"),
    )

    def __repr__(self):
        return f"<CostReportDB(id={self.id}, name='{self.name}', type='{self.report_type}')>"


# ==================== Change Management Models ====================


class ChangeApprovalDB(Base):
    """变更审批表"""

    __tablename__ = "change_approvals"

    id = Column(String(20), primary_key=True, nullable=False)
    request_id = Column(String(50), nullable=False, index=True)
    approver = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    comments = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_change_approvals_request_id", "request_id"),
        Index("idx_change_approvals_status", "status"),
    )

    def __repr__(self):
        return f"<ChangeApprovalDB(id={self.id}, request_id='{self.request_id}', approver='{self.approver}')>"


class ChangeScheduleDB(Base):
    """变更调度表"""

    __tablename__ = "change_schedules"

    id = Column(String(20), primary_key=True, nullable=False)
    request_id = Column(String(50), nullable=False, index=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    maintenance_window = Column(String(50), nullable=False)
    timezone = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="scheduled", index=True)
    schedule_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_change_schedules_request_id", "request_id"),
        Index("idx_change_schedules_status", "status"),
    )

    def __repr__(self):
        return f"<ChangeScheduleDB(id={self.id}, request_id='{self.request_id}', status='{self.status}')>"


class ChangeRollbackPlanDB(Base):
    """变更回滚计划表"""

    __tablename__ = "change_rollback_plans"

    id = Column(String(20), primary_key=True, nullable=False)
    request_id = Column(String(50), nullable=False, index=True)
    rollback_steps = Column(JSON, nullable=False)
    data_consistency_checks = Column(JSON, nullable=False)
    rollback_triggers = Column(JSON, nullable=False)
    validation_after_rollback = Column(JSON, nullable=False)
    estimated_rollback_time = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="ready", index=True)
    rollback_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_change_rollback_plans_request_id", "request_id"),
        Index("idx_change_rollback_plans_status", "status"),
    )

    def __repr__(self):
        return f"<ChangeRollbackPlanDB(id={self.id}, request_id='{self.request_id}', status='{self.status}')>"
