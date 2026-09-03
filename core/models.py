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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(), nullable=True)

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
    detected_at = Column(DateTime(), nullable=False, index=True)
    metric_time = Column(DateTime(), nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_alerts_level_status", "level", "status"),
        Index("idx_alerts_detected_at", "detected_at"),
        Index("idx_alerts_host_detected_at", "host", "detected_at"),
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
    alert_time = Column(DateTime(), nullable=True)

    # 修复脚本信息
    script_key = Column(String(100), nullable=False, index=True)
    script_name = Column(String(200), nullable=False)

    # 修复结果
    success = Column(Boolean, nullable=False, index=True)
    status = Column(String(20), default=RepairStatus.SUCCESS.value, nullable=False, index=True)

    # 执行信息
    repair_time = Column(DateTime(), nullable=False, index=True)
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
    created_at = Column(DateTime(), server_default=func.now())

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
    approved_at = Column(DateTime(), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # 提交时间
    submitted_at = Column(DateTime(), server_default=func.now())

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
    created_at = Column(DateTime(), server_default=func.now(), index=True)

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
    timestamp = Column(DateTime(), nullable=False, index=True)

    # 创建时间
    created_at = Column(DateTime(), server_default=func.now())

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
    timestamp = Column(DateTime(), nullable=False, index=True)

    # 创建时间
    created_at = Column(DateTime(), server_default=func.now())

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
    started_at = Column(DateTime(), server_default=func.now())
    completed_at = Column(DateTime(), nullable=True)
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
    started_at = Column(DateTime(), server_default=func.now())
    completed_at = Column(DateTime(), nullable=True)

    # 创建者
    created_by = Column(String(50), nullable=True)

    # 保留策略
    retention_days = Column(Integer, nullable=True)
    expires_at = Column(DateTime(), nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
        DateTime(), server_default=func.now(), nullable=False, index=True
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
    effective_from = Column(DateTime(), server_default=func.now(), nullable=False)
    effective_until = Column(DateTime(), nullable=True)

    # 创建者
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())

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
        DateTime(), server_default=func.now(), nullable=False, index=True
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
    detected_at = Column(DateTime(), server_default=func.now(), nullable=False)
    git_commit = Column(String(50), nullable=True)
    git_branch = Column(String(50), nullable=True)

    # 状态
    status = Column(String(20), default="open", nullable=False)  # open, acknowledged, resolved
    acknowledged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime(), nullable=True)
    resolved_at = Column(DateTime(), nullable=True)

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
    expires_at = Column(DateTime(), nullable=False, index=True)
    completed_at = Column(DateTime(), nullable=True)

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 创建时间
    created_at = Column(DateTime(), server_default=func.now())

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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


# ==================== Infrastructure Models ====================


class InfrastructureResourceDB(Base):
    """基础设施资源表"""

    __tablename__ = "infrastructure_resources"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    region = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="running", nullable=False, index=True)
    cpu_cores = Column(Integer, nullable=False)
    memory_gb = Column(Integer, nullable=False)
    disk_gb = Column(Integer, nullable=False)
    tags = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_infrastructure_resources_type", "resource_type"),
        Index("idx_infrastructure_resources_provider", "provider"),
        Index("idx_infrastructure_resources_region", "region"),
        Index("idx_infrastructure_resources_status", "status"),
    )

    def __repr__(self):
        return f"<InfrastructureResourceDB(id='{self.id}', name='{self.name}', type='{self.resource_type}')>"


class InfrastructureProvisioningTaskDB(Base):
    """基础设施资源配置任务表"""

    __tablename__ = "infrastructure_provisioning_tasks"

    id = Column(String(100), primary_key=True)
    resource_id = Column(String(100), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    resource_type = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    logs = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_infrastructure_provisioning_resource_id", "resource_id"),
        Index("idx_infrastructure_provisioning_status", "status"),
    )

    def __repr__(self):
        return f"<InfrastructureProvisioningTaskDB(id='{self.id}', name='{self.name}', status='{self.status}')>"


class InfrastructureKafkaMessageDB(Base):
    """Kafka消息记录表"""

    __tablename__ = "infrastructure_kafka_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(200), nullable=False, index=True)
    key = Column(String(500), nullable=False)
    value = Column(JSON, nullable=False)
    headers = Column(JSON, nullable=True)
    status = Column(String(20), default="sent", nullable=False, index=True)  # sent, failed, pending
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(), server_default=func.now(), index=True)
    created_at = Column(DateTime(), server_default=func.now())

    __table_args__ = (
        Index("idx_infrastructure_kafka_topic", "topic"),
        Index("idx_infrastructure_kafka_status", "status"),
        Index("idx_infrastructure_kafka_sent_at", "sent_at"),
    )

    def __repr__(self):
        return f"<InfrastructureKafkaMessageDB(id={self.id}, topic='{self.topic}', status='{self.status}')>"


class InfrastructureFlinkJobDB(Base):
    """Flink作业记录表"""

    __tablename__ = "infrastructure_flink_jobs"

    id = Column(String(100), primary_key=True)
    job_name = Column(String(200), nullable=False, unique=True, index=True)
    job_type = Column(String(50), nullable=False, index=True)  # metrics_aggregation, anomaly_detection, etc.
    parallelism = Column(Integer, default=2, nullable=False)
    status = Column(String(20), default="created", nullable=False, index=True)  # created, running, stopped, failed
    config = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(), nullable=True)
    stopped_at = Column(DateTime(), nullable=True)

    __table_args__ = (
        Index("idx_infrastructure_flink_job_name", "job_name"),
        Index("idx_infrastructure_flink_job_type", "job_type"),
        Index("idx_infrastructure_flink_status", "status"),
    )

    def __repr__(self):
        return f"<InfrastructureFlinkJobDB(id='{self.id}', name='{self.job_name}', status='{self.status}')>"


class InfrastructureStorageDB(Base):
    """存储配置记录表"""

    __tablename__ = "infrastructure_storage"

    id = Column(String(100), primary_key=True)
    storage_type = Column(String(50), nullable=False, index=True)  # s3, minio, local
    endpoint = Column(String(500), nullable=False)
    bucket_name = Column(String(200), nullable=False)
    access_key = Column(String(200), nullable=False)
    secret_key = Column(String(200), nullable=False)  # Should be encrypted in production
    region = Column(String(50), nullable=True)
    status = Column(String(20), default="active", nullable=False, index=True)
    config = Column(JSON, nullable=True)
    health_status = Column(String(20), default="unknown", nullable=False)  # healthy, unhealthy, unknown
    last_health_check = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_infrastructure_storage_type", "storage_type"),
        Index("idx_infrastructure_storage_status", "status"),
    )

    def __repr__(self):
        return f"<InfrastructureStorageDB(id='{self.id}', type='{self.storage_type}', status='{self.status}')>"


class InfrastructureConfigDB(Base):
    """配置中心记录表"""

    __tablename__ = "infrastructure_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    config_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy reserved name
    category = Column(String(50), nullable=True, index=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_infrastructure_config_key", "key"),
        Index("idx_infrastructure_config_category", "category"),
    )

    def __repr__(self):
        return f"<InfrastructureConfigDB(id={self.id}, key='{self.key}', version={self.version})>"


class InfrastructureDataFlowDB(Base):
    """数据流记录表"""

    __tablename__ = "infrastructure_data_flows"

    id = Column(String(100), primary_key=True)
    flow_name = Column(String(200), nullable=False, unique=True, index=True)
    flow_type = Column(String(50), nullable=False, index=True)  # l1l2, streaming, batch
    status = Column(String(20), default="stopped", nullable=False, index=True)  # running, stopped, error
    total_processed = Column(Integer, default=0, nullable=False)
    total_analyzed = Column(Integer, default=0, nullable=False)
    total_errors = Column(Integer, default=0, nullable=False)
    avg_processing_time_ms = Column(Float, default=0.0, nullable=False)
    config = Column(JSON, nullable=True)
    started_at = Column(DateTime(), nullable=True)
    stopped_at = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_infrastructure_data_flow_name", "flow_name"),
        Index("idx_infrastructure_data_flow_type", "flow_type"),
        Index("idx_infrastructure_data_flow_status", "status"),
    )

    def __repr__(self):
        return f"<InfrastructureDataFlowDB(id='{self.id}', name='{self.flow_name}', status='{self.status}')>"


class InfrastructureMonitoringDB(Base):
    """监控基础设施记录表"""

    __tablename__ = "infrastructure_monitoring"

    id = Column(String(100), primary_key=True)
    component_name = Column(String(200), nullable=False, unique=True, index=True)
    component_type = Column(String(50), nullable=False, index=True)  # prometheus, grafana, loki, tempo
    status = Column(String(20), default="active", nullable=False, index=True)
    endpoint = Column(String(500), nullable=True)
    config = Column(JSON, nullable=True)
    health_status = Column(String(20), default="unknown", nullable=False)
    last_health_check = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_infrastructure_monitoring_name", "component_name"),
        Index("idx_infrastructure_monitoring_type", "component_type"),
        Index("idx_infrastructure_monitoring_status", "status"),
    )

    def __repr__(self):
        return f"<InfrastructureMonitoringDB(id='{self.id}', name='{self.component_name}', status='{self.status}')>"


# ==================== ITSM Models ====================


class ITSMIncidentDB(Base):
    """ITSM事件表"""

    __tablename__ = "itsm_incidents"

    id = Column(String(100), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium", nullable=False, index=True)
    status = Column(String(20), default="open", nullable=False, index=True)
    assigned_to = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False, index=True)
    impact = Column(String(20), default="medium", nullable=False)
    urgency = Column(String(20), default="medium", nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_itsm_incidents_priority", "priority"),
        Index("idx_itsm_incidents_status", "status"),
        Index("idx_itsm_incidents_category", "category"),
    )

    def __repr__(self):
        return f"<ITSMIncidentDB(id='{self.id}', title='{self.title}', status='{self.status}')>"


class ITSMProblemDB(Base):
    """ITSM问题表"""

    __tablename__ = "itsm_problems"

    id = Column(String(100), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="open", nullable=False, index=True)
    priority = Column(String(20), default="medium", nullable=False)
    root_cause = Column(Text, nullable=True)
    related_incidents = Column(JSON, nullable=True)
    workarounds = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(), nullable=True)

    __table_args__ = (
        Index("idx_itsm_problems_status", "status"),
    )

    def __repr__(self):
        return f"<ITSMProblemDB(id='{self.id}', title='{self.title}', status='{self.status}')>"


class ITSMChangeDB(Base):
    """ITSM变更表"""

    __tablename__ = "itsm_changes"

    id = Column(String(100), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    priority = Column(String(20), default="medium", nullable=False)
    change_type = Column(String(50), nullable=False)
    risk_level = Column(String(20), default="medium", nullable=False)
    scheduled_start = Column(DateTime(), nullable=True)
    scheduled_end = Column(DateTime(), nullable=True)
    implemented_at = Column(DateTime(), nullable=True)
    created_by = Column(String(100), nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_itsm_changes_status", "status"),
    )

    def __repr__(self):
        return f"<ITSMChangeDB(id='{self.id}', title='{self.title}', status='{self.status}')>"


class ITSMServiceCatalogDB(Base):
    """ITSM服务目录表"""

    __tablename__ = "itsm_service_catalog"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    service_type = Column(String(50), nullable=False)
    availability = Column(String(20), default="24x7", nullable=False)
    sla_percentage = Column(Float, default=99.9, nullable=False)
    owner = Column(String(100), nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_itsm_service_catalog_category", "category"),
    )

    def __repr__(self):
        return f"<ITSMServiceCatalogDB(id='{self.id}', name='{self.name}', category='{self.category}')>"


class ITSLADB(Base):
    """ITSLA表"""

    __tablename__ = "itsm_slas"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    service_id = Column(String(100), nullable=True, index=True)
    response_time_minutes = Column(Integer, nullable=False)
    resolution_time_minutes = Column(Integer, nullable=False)
    availability_percentage = Column(Float, default=99.9, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_itsm_slas_service_id", "service_id"),
    )

    def __repr__(self):
        return f"<ITSLADB(id='{self.id}', name='{self.name}')>"


class ITSMKnowledgeBaseDB(Base):
    """ITSM知识库表"""

    __tablename__ = "itsm_knowledge_base"

    id = Column(String(100), primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    tags = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_itsm_knowledge_base_category", "category"),
    )

    def __repr__(self):
        return f"<ITSMKnowledgeBaseDB(id='{self.id}', title='{self.title}', category='{self.category}')>"


# ==================== Localization Models ====================


class LocalizationLanguageDB(Base):
    """本地化语言表"""

    __tablename__ = "localization_languages"

    id = Column(String(100), primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    native_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_localization_languages_code", "code"),
        Index("idx_localization_languages_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<LocalizationLanguageDB(id='{self.id}', code='{self.code}', name='{self.name}')>"


class LocalizationResourceDB(Base):
    """本地化资源表"""

    __tablename__ = "localization_resources"

    id = Column(String(100), primary_key=True)
    language_code = Column(String(20), nullable=False, index=True)
    namespace = Column(String(100), nullable=False, index=True)
    key = Column(String(200), nullable=False)
    value = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_localization_resources_language_code", "language_code"),
        Index("idx_localization_resources_namespace", "namespace"),
        Index("idx_localization_resources_key", "key"),
    )

    def __repr__(self):
        return f"<LocalizationResourceDB(id='{self.id}', key='{self.key}', language='{self.language_code}')>"


class LocalizationTranslationDB(Base):
    """本地化翻译表"""

    __tablename__ = "localization_translations"

    id = Column(String(100), primary_key=True)
    source_language = Column(String(20), nullable=False, index=True)
    target_language = Column(String(20), nullable=False, index=True)
    namespace = Column(String(100), nullable=False)
    key = Column(String(200), nullable=False)
    source_value = Column(Text, nullable=False)
    target_value = Column(Text, nullable=False)
    status = Column(String(20), default="draft", nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_localization_translations_source", "source_language"),
        Index("idx_localization_translations_target", "target_language"),
    )

    def __repr__(self):
        return f"<LocalizationTranslationDB(id='{self.id}', key='{self.key}')>"


class LocalizationAdapterDB(Base):
    """本地化适配器表"""

    __tablename__ = "localization_adapters"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    config = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_localization_adapters_type", "type"),
        Index("idx_localization_adapters_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<LocalizationAdapterDB(id='{self.id}', name='{self.name}', type='{self.type}')>"


# ==================== Maturity Models ====================


class MaturityAssessmentDB(Base):
    """成熟度评估表"""

    __tablename__ = "maturity_assessments"

    id = Column(String(100), primary_key=True)
    assessment_name = Column(String(200), nullable=False)
    status = Column(String(20), default="in_progress", nullable=False, index=True)
    overall_score = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    level_name = Column(String(100), nullable=False)
    dimensions = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    assessed_at = Column(DateTime(), server_default=func.now())
    assessed_by = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_maturity_assessments_status", "status"),
    )

    def __repr__(self):
        return f"<MaturityAssessmentDB(id='{self.id}', name='{self.assessment_name}', status='{self.status}')>"


class AlertAcknowledgement(Base):
    """告警确认记录表"""

    __tablename__ = "alert_acknowledgements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(100), nullable=False, index=True)
    acknowledged_by = Column(String(50), nullable=False)
    acknowledged_at = Column(
        DateTime(), server_default=func.now(), nullable=False, index=True
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    calculated_at = Column(DateTime(), server_default=func.now(), index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    changed_at = Column(DateTime(), server_default=func.now(), index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    timestamp = Column(DateTime(), server_default=func.now(), index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    verification_timestamp = Column(DateTime(), nullable=True)

    # 假设状态
    status = Column(String(20), default="active", nullable=False, index=True)  # active, archived

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    started_at = Column(DateTime(), nullable=True)
    completed_at = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    collected_at = Column(DateTime(), server_default=func.now(), index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    scheduled_date = Column(DateTime(), nullable=True)
    completed_date = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
    start_date = Column(DateTime(), nullable=True)
    end_date = Column(DateTime(), nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

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
    target_date = Column(DateTime(), nullable=True)
    threshold = Column(Float, nullable=False)
    recommended_action = Column(Text, nullable=False)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(), server_default=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
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
    detected_at = Column(DateTime(), nullable=False)
    severity = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    affected_amount = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="open", index=True)
    created_at = Column(DateTime(), server_default=func.now())
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
    created_at = Column(DateTime(), server_default=func.now())
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
    period_start = Column(DateTime(), nullable=False)
    period_end = Column(DateTime(), nullable=False)
    total_cost = Column(Float, nullable=False)
    generated_at = Column(DateTime(), server_default=func.now())
    status = Column(String(50), nullable=False, default="completed", index=True)
    report_data = Column(JSON, nullable=False)
    report_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cost_reports_type", "report_type"),
        Index("idx_cost_reports_status", "status"),
    )

    def __repr__(self):
        return f"<CostReportDB(id={self.id}, name='{self.name}', type='{self.report_type}')>"


# ==================== Capacity Planning Extended Models ====================


class CapacityForecastDB(Base):
    """容量预测表"""

    __tablename__ = "capacity_forecasts"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    forecast_type = Column(String(50), nullable=False)
    current_value = Column(Float, nullable=False)
    forecast_7d = Column(Float, nullable=False)
    forecast_30d = Column(Float, nullable=False)
    forecast_90d = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    trend = Column(String(50), nullable=False)
    forecast_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    forecast_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_forecasts_service", "service"),
        Index("idx_capacity_forecasts_resource_type", "resource_type"),
        Index("idx_capacity_forecasts_forecast_type", "forecast_type"),
    )

    def __repr__(self):
        return f"<CapacityForecastDB(id={self.id}, service='{self.service}', type='{self.resource_type}')>"


class CapacityThresholdDB(Base):
    """容量阈值表"""

    __tablename__ = "capacity_thresholds"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    warning_threshold = Column(Float, nullable=False)
    critical_threshold = Column(Float, nullable=False)
    alert_enabled = Column(Boolean, nullable=False, default=True)
    notification_channels = Column(JSON, nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    threshold_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_thresholds_service", "service"),
        Index("idx_capacity_thresholds_resource_type", "resource_type"),
    )

    def __repr__(self):
        return f"<CapacityThresholdDB(id={self.id}, service='{self.service}', type='{self.resource_type}')>"


class CapacityAlertDB(Base):
    """容量告警表"""

    __tablename__ = "capacity_alerts"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False, index=True)
    current_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="open", index=True)
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime(), nullable=True)
    resolved_at = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now())
    alert_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_alerts_service", "service"),
        Index("idx_capacity_alerts_resource_type", "resource_type"),
        Index("idx_capacity_alerts_severity", "severity"),
        Index("idx_capacity_alerts_status", "status"),
    )

    def __repr__(self):
        return f"<CapacityAlertDB(id={self.id}, service='{self.service}', type='{self.resource_type}')>"


class CapacityScenarioDB(Base):
    """容量场景表"""

    __tablename__ = "capacity_scenarios"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    scenario_type = Column(String(50), nullable=False)
    services = Column(JSON, nullable=False)
    growth_factors = Column(JSON, nullable=False)
    time_horizon = Column(Integer, nullable=False)
    baseline_metrics = Column(JSON, nullable=False)
    projected_metrics = Column(JSON, nullable=False)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    status = Column(String(50), nullable=False, default="draft", index=True)
    scenario_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_scenarios_type", "scenario_type"),
        Index("idx_capacity_scenarios_status", "status"),
    )

    def __repr__(self):
        return f"<CapacityScenarioDB(id={self.id}, name='{self.name}', type='{self.scenario_type}')>"


class CapacitySimulationDB(Base):
    """容量模拟表"""

    __tablename__ = "capacity_simulations"

    id = Column(String(50), primary_key=True, nullable=False)
    scenario_id = Column(String(50), nullable=False, index=True)
    simulation_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    resource_requirements = Column(JSON, nullable=False)
    cost_impact = Column(Float, nullable=False)
    performance_impact = Column(JSON, nullable=False)
    risk_assessment = Column(Text, nullable=False)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    simulation_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_simulations_scenario", "scenario_id"),
        Index("idx_capacity_simulations_type", "simulation_type"),
    )

    def __repr__(self):
        return f"<CapacitySimulationDB(id={self.id}, scenario_id='{self.scenario_id}')>"


class CapacityResourcePoolDB(Base):
    """资源池表"""

    __tablename__ = "capacity_resource_pools"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    pool_type = Column(String(50), nullable=False)
    total_capacity = Column(Float, nullable=False)
    allocated_capacity = Column(Float, nullable=False)
    available_capacity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    services = Column(JSON, nullable=False)
    allocation_policy = Column(String(50), nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    pool_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_resource_pools_type", "pool_type"),
    )

    def __repr__(self):
        return f"<CapacityResourcePoolDB(id={self.id}, name='{self.name}', type='{self.pool_type}')>"


class CapacityReservationDB(Base):
    """资源预留表"""

    __tablename__ = "capacity_reservations"

    id = Column(String(50), primary_key=True, nullable=False)
    pool_id = Column(String(50), nullable=False, index=True)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    reserved_amount = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    start_date = Column(DateTime(), nullable=False)
    end_date = Column(DateTime(), nullable=False)
    purpose = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    reservation_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_reservations_pool", "pool_id"),
        Index("idx_capacity_reservations_service", "service"),
        Index("idx_capacity_reservations_status", "status"),
    )

    def __repr__(self):
        return f"<CapacityReservationDB(id={self.id}, service='{self.service}', pool_id='{self.pool_id}')>"


class CapacityUtilizationDB(Base):
    """资源利用率表"""

    __tablename__ = "capacity_utilization"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(), nullable=False, index=True)
    utilization_percent = Column(Float, nullable=False)
    peak_utilization = Column(Float, nullable=False)
    average_utilization = Column(Float, nullable=False)
    min_utilization = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    utilization_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(), server_default=func.now())

    __table_args__ = (
        Index("idx_capacity_utilization_service", "service"),
        Index("idx_capacity_utilization_resource_type", "resource_type"),
        Index("idx_capacity_utilization_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<CapacityUtilizationDB(id={self.id}, service='{self.service}', type='{self.resource_type}')>"


class CapacityTrendDB(Base):
    """趋势分析表"""

    __tablename__ = "capacity_trends"

    id = Column(String(50), primary_key=True, nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    trend_type = Column(String(50), nullable=False)
    period_start = Column(DateTime(), nullable=False)
    period_end = Column(DateTime(), nullable=False)
    growth_rate = Column(Float, nullable=False)
    trend_direction = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    seasonal_pattern = Column(JSON, nullable=False)
    anomaly_flags = Column(JSON, nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    trend_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_trends_service", "service"),
        Index("idx_capacity_trends_resource_type", "resource_type"),
        Index("idx_capacity_trends_type", "trend_type"),
    )

    def __repr__(self):
        return f"<CapacityTrendDB(id={self.id}, service='{self.service}', type='{self.resource_type}')>"


class CapacityBenchmarkDB(Base):
    """基准测试表"""

    __tablename__ = "capacity_benchmarks"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    benchmark_type = Column(String(50), nullable=False)
    service = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    baseline_metrics = Column(JSON, nullable=False)
    target_metrics = Column(JSON, nullable=False)
    current_metrics = Column(JSON, nullable=False)
    compliance_score = Column(Float, nullable=False)
    last_assessment = Column(DateTime(), nullable=False)
    next_assessment = Column(DateTime(), nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    benchmark_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_capacity_benchmarks_service", "service"),
        Index("idx_capacity_benchmarks_type", "benchmark_type"),
    )

    def __repr__(self):
        return f"<CapacityBenchmarkDB(id={self.id}, name='{self.name}', service='{self.service}')>"


# ==================== Change Management Models ====================


class ChangeApprovalDB(Base):
    """变更审批表"""

    __tablename__ = "change_approvals"

    id = Column(String(20), primary_key=True, nullable=False)
    request_id = Column(String(50), nullable=False, index=True)
    approver = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    comments = Column(Text, nullable=True)
    approved_at = Column(DateTime(), nullable=True)
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
    scheduled_start = Column(DateTime(), nullable=False)
    scheduled_end = Column(DateTime(), nullable=False)
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


# ==================== AI Advanced Models ====================


class AIFineTuningJobDB(Base):
    """AI微调任务表"""

    __tablename__ = "ai_fine_tuning_jobs"

    id = Column(String(50), primary_key=True, nullable=False)
    model_name = Column(String(255), nullable=False)
    dataset = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    progress = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    job_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_fine_tuning_jobs_status", "status"),
    )

    def __repr__(self):
        return f"<AIFineTuningJobDB(id={self.id}, model='{self.model_name}', status='{self.status}')>"


class AIRunbookDB(Base):
    """AI运行手册表"""

    __tablename__ = "ai_runbooks"

    id = Column(String(50), primary_key=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    runbook_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AIRunbookDB(id={self.id}, title='{self.title}')>"


class AIAnalysisReportDB(Base):
    """AI分析报告表"""

    __tablename__ = "ai_analysis_reports"

    id = Column(String(50), primary_key=True, nullable=False)
    analysis_type = Column(String(50), nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    report_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_analysis_reports_type", "analysis_type"),
    )

    def __repr__(self):
        return f"<AIAnalysisReportDB(id={self.id}, type='{self.analysis_type}')>"


class AIDSLDefinitionDB(Base):
    """AI DSL定义表"""

    __tablename__ = "ai_dsl_definitions"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    definition = Column(JSON, nullable=False)
    version = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    dsl_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AIDSLDefinitionDB(id={self.id}, name='{self.name}', version='{self.version}')>"


class AIExecutionDB(Base):
    """AI执行记录表"""

    __tablename__ = "ai_executions"

    id = Column(String(50), primary_key=True, nullable=False)
    dsl_id = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="running", index=True)
    results = Column(JSON, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    execution_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_executions_dsl_id", "dsl_id"),
        Index("idx_ai_executions_status", "status"),
    )

    def __repr__(self):
        return f"<AIExecutionDB(id={self.id}, dsl_id='{self.dsl_id}', status='{self.status}')>"


class AIWorkflowDB(Base):
    """AI工作流表"""

    __tablename__ = "ai_workflows"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    nodes = Column(JSON, nullable=False)
    edges = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    workflow_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_workflows_status", "status"),
    )

    def __repr__(self):
        return f"<AIWorkflowDB(id={self.id}, name='{self.name}', status='{self.status}')>"


class AIDeepLearningModelDB(Base):
    """AI深度学习模型表"""

    __tablename__ = "ai_deep_learning_models"

    id = Column(String(50), primary_key=True, nullable=False)
    model_name = Column(String(255), nullable=False)
    architecture = Column(String(50), nullable=False)
    performance_metrics = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    model_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AIDeepLearningModelDB(id={self.id}, name='{self.model_name}', arch='{self.architecture}')>"


class AIAdvancedFeatureDB(Base):
    """AI高级功能表"""

    __tablename__ = "ai_advanced_features"

    id = Column(String(50), primary_key=True, nullable=False)
    feature_name = Column(String(255), nullable=False)
    feature_type = Column(String(50), nullable=False)
    configuration = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="enabled", index=True)
    created_at = Column(DateTime, server_default=func.now())
    feature_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_advanced_features_status", "status"),
    )

    def __repr__(self):
        return f"<AIAdvancedFeatureDB(id={self.id}, name='{self.feature_name}', type='{self.feature_type}')>"


class AIFeedbackDB(Base):
    """AI反馈表"""

    __tablename__ = "ai_feedbacks"

    id = Column(String(50), primary_key=True, nullable=False)
    feedback_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    feedback_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_feedbacks_type", "feedback_type"),
    )

    def __repr__(self):
        return f"<AIFeedbackDB(id={self.id}, type='{self.feedback_type}', rating={self.rating})>"


class AIDocumentIndexDB(Base):
    """AI文档索引表"""

    __tablename__ = "ai_document_indexes"

    id = Column(String(50), primary_key=True, nullable=False)
    index_name = Column(String(255), nullable=False)
    document_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    index_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AIDocumentIndexDB(id={self.id}, name='{self.index_name}', count={self.document_count})>"


class AIPatternDB(Base):
    """AI模式表"""

    __tablename__ = "ai_patterns"

    id = Column(String(50), primary_key=True, nullable=False)
    pattern_name = Column(String(255), nullable=False)
    pattern_type = Column(String(50), nullable=False)
    pattern_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    pattern_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_patterns_type", "pattern_type"),
    )

    def __repr__(self):
        return f"<AIPatternDB(id={self.id}, name='{self.pattern_name}', type='{self.pattern_type}')>"


class AITopologyAnalysisDB(Base):
    """AI拓扑分析表"""

    __tablename__ = "ai_topology_analyses"

    id = Column(String(50), primary_key=True, nullable=False)
    analysis_type = Column(String(50), nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    topology_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_topology_analyses_type", "analysis_type"),
    )

    def __repr__(self):
        return f"<AITopologyAnalysisDB(id={self.id}, type='{self.analysis_type}')>"


class AIRootCauseAnalysisDB(Base):
    """AI根因分析表"""

    __tablename__ = "ai_root_cause_analyses"

    id = Column(String(50), primary_key=True, nullable=False)
    incident_id = Column(String(50), nullable=False)
    root_cause = Column(Text, nullable=False)
    contributing_factors = Column(JSON, nullable=False)
    recommended_actions = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    rca_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_root_cause_analyses_incident", "incident_id"),
    )

    def __repr__(self):
        return f"<AIRootCauseAnalysisDB(id={self.id}, incident='{self.incident_id}')>"


class AIGraphNodeDB(Base):
    """AI图节点表"""

    __tablename__ = "ai_graph_nodes"

    id = Column(String(50), primary_key=True, nullable=False)
    node_type = Column(String(50), nullable=False)
    node_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    node_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_graph_nodes_type", "node_type"),
    )

    def __repr__(self):
        return f"<AIGraphNodeDB(id={self.id}, type='{self.node_type}')>"


class AIGraphEdgeDB(Base):
    """AI图边表"""

    __tablename__ = "ai_graph_edges"

    id = Column(String(50), primary_key=True, nullable=False)
    source_node_id = Column(String(50), nullable=False)
    target_node_id = Column(String(50), nullable=False)
    edge_type = Column(String(50), nullable=False)
    edge_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    edge_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_graph_edges_source", "source_node_id"),
        Index("idx_ai_graph_edges_target", "target_node_id"),
        Index("idx_ai_graph_edges_type", "edge_type"),
    )

    def __repr__(self):
        return f"<AIGraphEdgeDB(id={self.id}, source='{self.source_node_id}', target='{self.target_node_id}', type='{self.edge_type}')>"


class AIKnowledgeBaseDB(Base):
    """AI知识库表"""

    __tablename__ = "ai_knowledge_bases"

    id = Column(String(50), primary_key=True, nullable=False)
    kb_name = Column(String(255), nullable=False)
    kb_type = Column(String(50), nullable=False)
    document_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    kb_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_knowledge_bases_type", "kb_type"),
    )

    def __repr__(self):
        return f"<AIKnowledgeBaseDB(id={self.id}, name='{self.kb_name}', type='{self.kb_type}')>"


class AILoadBalancerConfigDB(Base):
    """AI负载均衡配置表"""

    __tablename__ = "ai_load_balancer_configs"

    id = Column(String(50), primary_key=True, nullable=False)
    config_name = Column(String(255), nullable=False)
    strategy = Column(String(50), nullable=False)
    targets = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    config_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_load_balancer_configs_status", "status"),
    )

    def __repr__(self):
        return f"<AILoadBalancerConfigDB(id={self.id}, name='{self.config_name}', strategy='{self.strategy}')>"


class AIFusionConfigDB(Base):
    """AI融合配置表"""

    __tablename__ = "ai_fusion_configs"

    id = Column(String(50), primary_key=True, nullable=False)
    config_name = Column(String(255), nullable=False)
    fusion_strategy = Column(String(50), nullable=False)
    sources = Column(JSON, nullable=False)
    weights = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    config_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_fusion_configs_status", "status"),
    )

    def __repr__(self):
        return f"<AIFusionConfigDB(id={self.id}, name='{self.config_name}', strategy='{self.fusion_strategy}')>"


class AICostSuggestionDB(Base):
    """AI成本建议表"""

    __tablename__ = "ai_cost_suggestions"

    id = Column(String(50), primary_key=True, nullable=False)
    suggestion_type = Column(String(50), nullable=False)
    potential_savings = Column(Float, nullable=False)
    details = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, server_default=func.now())
    cost_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_cost_suggestions_status", "status"),
    )

    def __repr__(self):
        return f"<AICostSuggestionDB(id={self.id}, type='{self.suggestion_type}', savings={self.potential_savings})>"


class AIRoutingRuleDB(Base):
    """AI路由规则表"""

    __tablename__ = "ai_routing_rules"

    id = Column(String(50), primary_key=True, nullable=False)
    rule_name = Column(String(255), nullable=False)
    condition = Column(JSON, nullable=False)
    action = Column(JSON, nullable=False)
    priority = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    rule_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_routing_rules_status", "status"),
    )

    def __repr__(self):
        return f"<AIRoutingRuleDB(id={self.id}, name='{self.rule_name}', priority={self.priority})>"


class AIVectorizerConfigDB(Base):
    """AI向量化配置表"""

    __tablename__ = "ai_vectorizer_configs"

    id = Column(String(50), primary_key=True, nullable=False)
    config_name = Column(String(255), nullable=False)
    embedding_model = Column(String(255), nullable=False)
    dimensions = Column(Integer, nullable=False)
    batch_size = Column(Integer, nullable=False, default=100)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    config_metadata = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ai_vectorizer_configs_status", "status"),
    )

    def __repr__(self):
        return f"<AIVectorizerConfigDB(id={self.id}, name='{self.config_name}', model='{self.embedding_model}')>"


class AIVectorizerJobDB(Base):
    """AI向量化任务表"""

    __tablename__ = "ai_vectorizer_jobs"

    id = Column(String(50), primary_key=True, nullable=False)
    config_id = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    total_items = Column(Integer, nullable=False, default=0)
    processed_items = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    job_metadata = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ai_vectorizer_jobs_status", "status"),
        Index("idx_ai_vectorizer_jobs_config_id", "config_id"),
    )

    def __repr__(self):
        return f"<AIVectorizerJobDB(id={self.id}, config_id='{self.config_id}', status='{self.status}')>"


class AICapabilityEvaluationDB(Base):
    """AI模型能力评估结果表"""

    __tablename__ = "ai_capability_evaluations"

    id = Column(String(50), primary_key=True, nullable=False)
    model_id = Column(String(255), nullable=False, index=True)
    model_name = Column(String(255), nullable=False)
    capabilities = Column(JSON, nullable=False)
    overall_score = Column(Float, nullable=False)
    evaluation_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_ai_capability_evaluations_model_id", "model_id"),
        Index("idx_ai_capability_evaluations_overall_score", "overall_score"),
    )

    def __repr__(self):
        return f"<AICapabilityEvaluationDB(id={self.id}, model='{self.model_name}', score={self.overall_score})>"


class AIEvaluationTaskDB(Base):
    """AI评估任务表"""

    __tablename__ = "ai_evaluation_tasks"

    id = Column(String(50), primary_key=True, nullable=False)
    task_name = Column(String(255), nullable=False)
    task_type = Column(String(50), nullable=False, index=True)
    model_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    progress = Column(Float, nullable=False, default=0.0)
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    task_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ai_evaluation_tasks_type", "task_type"),
        Index("idx_ai_evaluation_tasks_status", "status"),
        Index("idx_ai_evaluation_tasks_model_id", "model_id"),
    )

    def __repr__(self):
        return f"<AIEvaluationTaskDB(id={self.id}, name='{self.task_name}', status='{self.status}')>"


class AIRetrieverConfigDB(Base):
    """AI检索器配置表"""

    __tablename__ = "ai_retriever_configs"

    id = Column(String(50), primary_key=True, nullable=False)
    config_name = Column(String(255), nullable=False)
    retriever_type = Column(String(50), nullable=False)
    embedding_model = Column(String(255), nullable=False)
    vector_store_config = Column(JSON, nullable=False)
    retrieval_params = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    config_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_ai_retriever_configs_status", "status"),
    )

    def __repr__(self):
        return f"<AIRetrieverConfigDB(id={self.id}, name='{self.config_name}', type='{self.retriever_type}')>"


class AICrossLayerTrackingConfigDB(Base):
    """跨层追踪配置表"""

    __tablename__ = "ai_cross_layer_tracking_configs"

    id = Column(String(50), primary_key=True, nullable=False)
    config_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    layers = Column(JSON, nullable=False, default=list)
    sampling_rate = Column(Float, nullable=False, default=1.0)
    retention_days = Column(Integer, nullable=False, default=30)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    config_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_cross_layer_tracking_enabled", "enabled"),
        Index("idx_cross_layer_tracking_status", "status"),
    )

    def __repr__(self):
        return f"<AICrossLayerTrackingConfigDB(id={self.id}, name='{self.config_name}', enabled={self.enabled})>"


# ==================== Collaboration Management Models ====================


class CollaborationTeamDB(Base):
    """Collaboration team table"""

    __tablename__ = "collaboration_teams"

    id = Column(String(50), primary_key=True, nullable=False)
    team_name = Column(String(255), nullable=False)
    team_description = Column(Text, nullable=True)
    team_status = Column(String(50), nullable=False, default="active")
    team_lead_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    team_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_collaboration_teams_status", "team_status"),
    )

    def __repr__(self):
        return f"<CollaborationTeamDB(id={self.id}, name='{self.team_name}', status='{self.team_status}')>"


class CollaborationMemberDB(Base):
    """Collaboration member table"""

    __tablename__ = "collaboration_members"

    id = Column(String(50), primary_key=True, nullable=False)
    team_id = Column(String(50), nullable=False)
    member_name = Column(String(255), nullable=False)
    member_email = Column(String(255), nullable=True)
    member_role = Column(String(50), nullable=False)
    member_status = Column(String(50), nullable=False, default="active")
    joined_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    member_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_collaboration_members_team_id", "team_id"),
        Index("idx_collaboration_members_status", "member_status"),
    )

    def __repr__(self):
        return f"<CollaborationMemberDB(id={self.id}, name='{self.member_name}', role='{self.member_role}')>"


class CollaborationPermissionDB(Base):
    """Collaboration permission table"""

    __tablename__ = "collaboration_permissions"

    id = Column(String(50), primary_key=True, nullable=False)
    team_id = Column(String(50), nullable=False)
    member_id = Column(String(50), nullable=False)
    permission_type = Column(String(50), nullable=False)
    permission_level = Column(String(50), nullable=False)
    granted_at = Column(DateTime(), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(), nullable=True)
    permission_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_collaboration_permissions_team_id", "team_id"),
        Index("idx_collaboration_permissions_member_id", "member_id"),
    )

    def __repr__(self):
        return f"<CollaborationPermissionDB(id={self.id}, type='{self.permission_type}', level='{self.permission_level}')>"


class CollaborationActivityDB(Base):
    """Collaboration activity table"""

    __tablename__ = "collaboration_activities"

    id = Column(String(50), primary_key=True, nullable=False)
    team_id = Column(String(50), nullable=False)
    member_id = Column(String(50), nullable=True)
    activity_type = Column(String(50), nullable=False)
    activity_description = Column(Text, nullable=True)
    activity_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    activity_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_collaboration_activities_team_id", "team_id"),
        Index("idx_collaboration_activities_member_id", "member_id"),
        Index("idx_collaboration_activities_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<CollaborationActivityDB(id={self.id}, type='{self.activity_type}', team_id='{self.team_id}')>"


# ==================== Plugin Marketplace Models ====================


class PluginListingDB(Base):
    """Plugin marketplace listing table"""

    __tablename__ = "plugin_listings"

    id = Column(String(50), primary_key=True, nullable=False)
    plugin_id = Column(String(50), nullable=False)
    plugin_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default="general")
    tags = Column(JSON, nullable=True)
    price = Column(Float, nullable=True)
    quality = Column(String(50), nullable=False, default="community")
    download_url = Column(String(500), nullable=False)
    screenshot_urls = Column(JSON, nullable=True)
    documentation_url = Column(String(500), nullable=True)
    repository_url = Column(String(500), nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    rating = Column(Float, nullable=False, default=0.0)
    review_count = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    listing_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_plugin_listings_plugin_id", "plugin_id"),
        Index("idx_plugin_listings_category", "category"),
        Index("idx_plugin_listings_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<PluginListingDB(id={self.id}, name='{self.plugin_name}', version='{self.version}')>"


class PluginReviewDB(Base):
    """Plugin review table"""

    __tablename__ = "plugin_reviews"

    id = Column(String(50), primary_key=True, nullable=False)
    plugin_id = Column(String(50), nullable=False)
    reviewer_id = Column(String(50), nullable=False)
    reviewer_name = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    review_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_plugin_reviews_plugin_id", "plugin_id"),
        Index("idx_plugin_reviews_reviewer_id", "reviewer_id"),
    )

    def __repr__(self):
        return f"<PluginReviewDB(id={self.id}, plugin_id='{self.plugin_id}', rating={self.rating})>"


class PluginCategoryDB(Base):
    """Plugin category table"""

    __tablename__ = "plugin_categories"

    id = Column(String(50), primary_key=True, nullable=False)
    category_name = Column(String(255), nullable=False)
    category_description = Column(Text, nullable=True)
    parent_category_id = Column(String(50), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    category_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_plugin_categories_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<PluginCategoryDB(id={self.id}, name='{self.category_name}')>"


class InstalledPluginDB(Base):
    """Installed plugin table"""

    __tablename__ = "installed_plugins"

    id = Column(String(50), primary_key=True, nullable=False)
    plugin_id = Column(String(50), nullable=False)
    installed_version = Column(String(50), nullable=False)
    installation_date = Column(DateTime(), server_default=func.now(), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    configuration = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    installation_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_installed_plugins_plugin_id", "plugin_id"),
        Index("idx_installed_plugins_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<InstalledPluginDB(id={self.id}, plugin_id='{self.plugin_id}', version='{self.installed_version}')>"


# Business Impact Models
class BusinessImpactAnalysisDB(Base):
    """业务影响分析表"""

    __tablename__ = "business_impact_analysis"

    id = Column(String(50), primary_key=True, nullable=False)
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

    __table_args__ = (
        Index("idx_business_impact_analysis_service_name", "service_name"),
        Index("idx_business_impact_analysis_status", "status"),
        Index("idx_business_impact_analysis_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<BusinessImpactAnalysisDB(id={self.id}, service_name='{self.service_name}', status='{self.status}')>"


class BusinessImpactDependencyDB(Base):
    """业务影响依赖关系表"""

    __tablename__ = "business_impact_dependencies"

    id = Column(String(50), primary_key=True, nullable=False)
    source_service = Column(String(200), nullable=False, index=True)
    target_service = Column(String(200), nullable=False, index=True)
    dependency_type = Column(String(50), nullable=False, default="api_call")
    criticality = Column(String(50), nullable=False, default="medium", index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_business_impact_dependencies_source", "source_service"),
        Index("idx_business_impact_dependencies_target", "target_service"),
        Index("idx_business_impact_dependencies_criticality", "criticality"),
    )

    def __repr__(self):
        return f"<BusinessImpactDependencyDB(id={self.id}, source='{self.source_service}', target='{self.target_service}')>"


class BusinessImpactReportDB(Base):
    """业务影响报告表"""

    __tablename__ = "business_impact_reports"

    id = Column(String(50), primary_key=True, nullable=False)
    title = Column(String(200), nullable=False)
    service_names = Column(JSON, nullable=False)
    time_range = Column(String(50), nullable=False, default="24h")
    include_recommendations = Column(Boolean, nullable=False, default=True)
    summary = Column(JSON, nullable=True)
    service_data = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_business_impact_reports_title", "title"),
        Index("idx_business_impact_reports_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<BusinessImpactReportDB(id={self.id}, title='{self.title}')>"


# Chaos Engineering Models
class ChaosExperimentDB(Base):
    """混沌工程实验表"""

    __tablename__ = "chaos_experiments"

    id = Column(String(50), primary_key=True, nullable=False)
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

    __table_args__ = (
        Index("idx_chaos_experiments_name", "name"),
        Index("idx_chaos_experiments_status", "status"),
        Index("idx_chaos_experiments_severity", "severity"),
        Index("idx_chaos_experiments_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ChaosExperimentDB(id={self.id}, name='{self.name}', status='{self.status}')>"


class ChaosScenarioDB(Base):
    """混沌工程场景表"""

    __tablename__ = "chaos_scenarios"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    experiments = Column(JSON, nullable=False)  # 包含的实验ID列表
    enabled = Column(Boolean, nullable=False, default=True, index=True)  # 是否启用
    schedule = Column(String(100), nullable=True)  # 调度配置（cron表达式）
    # 保留原有字段以兼容旧数据
    fault_types = Column(JSON, nullable=True)  # 废弃字段，保留用于兼容
    target_services = Column(JSON, nullable=True)  # 废弃字段，保留用于兼容
    duration_seconds = Column(Integer, nullable=True)  # 废弃字段，保留用于兼容
    auto_rollback = Column(Boolean, nullable=True, default=True)  # 废弃字段，保留用于兼容
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_chaos_scenarios_name", "name"),
        Index("idx_chaos_scenarios_enabled", "enabled"),
        Index("idx_chaos_scenarios_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ChaosScenarioDB(id={self.id}, name='{self.name}', enabled={self.enabled})>"


class ChaosFaultDB(Base):
    """混沌工程故障表"""

    __tablename__ = "chaos_faults"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, index=True)  # 故障名称
    fault_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)  # 故障描述
    target = Column(String(200), nullable=False)
    parameters = Column(JSON, nullable=False)
    severity = Column(String(50), nullable=False, default="medium")
    status = Column(String(50), nullable=False, default="pending")
    result = Column(JSON, nullable=True)
    recovery_strategy = Column(String(200), nullable=True)  # 恢复策略
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_chaos_faults_name", "name"),
        Index("idx_chaos_faults_fault_type", "fault_type"),
        Index("idx_chaos_faults_status", "status"),
        Index("idx_chaos_faults_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ChaosFaultDB(id={self.id}, name='{self.name}', fault_type='{self.fault_type}', target='{self.target}')>"


# ==================== Service Monitoring Models ====================


class ServiceMonitorAlertDB(Base):
    """服务监控告警表"""

    __tablename__ = "service_monitor_alerts"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    service_name = Column(String(200), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    condition = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    severity = Column(String(50), nullable=False, default="warning")
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    notification_channels = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_service_monitor_alerts_service", "service_name"),
        Index("idx_service_monitor_alerts_severity", "severity"),
    )

    def __repr__(self):
        return f"<ServiceMonitorAlertDB(id='{self.id}', name='{self.name}', service='{self.service_name}')>"


class ServiceMonitorDashboardDB(Base):
    """服务监控仪表板表"""

    __tablename__ = "service_monitor_dashboards"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    widgets = Column(JSON, nullable=False)
    refresh_interval_seconds = Column(Integer, nullable=False, default=30)
    is_public = Column(Boolean, nullable=False, default=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_service_monitor_dashboards_name", "name"),
    )

    def __repr__(self):
        return f"<ServiceMonitorDashboardDB(id='{self.id}', name='{self.name}')>"


# ==================== SLO Models ====================


class SLODefinitionDB(Base):
    """SLO定义表"""

    __tablename__ = "slo_definitions"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    metric_type = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    operator = Column(String(50), nullable=False, default="gte")
    window = Column(String(50), nullable=False, default="30d")
    alerting = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_slo_definitions_name", "name"),
        Index("idx_slo_definitions_metric_type", "metric_type"),
    )

    def __repr__(self):
        return f"<SLODefinitionDB(id='{self.id}', name='{self.name}', metric_type='{self.metric_type}')>"


class SLOObjectiveDB(Base):
    """SLO目标表"""

    __tablename__ = "slo_objectives"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    service = Column(String(200), nullable=False)
    metric = Column(String(100), nullable=False)
    target = Column(Float, nullable=False)
    window = Column(String(50), nullable=False, default="30d")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_slo_objectives_service", "service"),
        Index("idx_slo_objectives_name", "name"),
    )

    def __repr__(self):
        return f"<SLOObjectiveDB(id='{self.id}', name='{self.name}', service='{self.service}')>"


class SLOAlertDB(Base):
    """SLO告警表"""

    __tablename__ = "slo_alerts"

    id = Column(String(100), primary_key=True)
    slo_id = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_slo_alerts_slo_id", "slo_id"),
        Index("idx_slo_alerts_severity", "severity"),
    )

    def __repr__(self):
        return f"<SLOAlertDB(id='{self.id}', slo_id='{self.slo_id}', severity='{self.severity}')>"


# ==================== Tenant Models ====================


class TenantConfigDB(Base):
    """租户配置表"""

    __tablename__ = "tenant_configs"

    tenant_id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    domain = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(50), nullable=True, default="#0066cc")
    secondary_color = Column(String(50), nullable=True, default="#004499")
    custom_css = Column(Text, nullable=True)
    custom_js = Column(Text, nullable=True)
    branding_enabled = Column(Boolean, nullable=False, default=False)
    sso_enabled = Column(Boolean, nullable=False, default=False)
    sso_provider = Column(String(50), nullable=True)
    sso_config = Column(JSON, nullable=True)
    audit_logging_enabled = Column(Boolean, nullable=False, default=True)
    data_retention_days = Column(Integer, nullable=False, default=90)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_tenant_configs_name", "name"),
    )

    def __repr__(self):
        return f"<TenantConfigDB(tenant_id='{self.tenant_id}', name='{self.name}')>"


class TenantSettingsDB(Base):
    """租户设置表"""

    __tablename__ = "tenant_settings"

    tenant_id = Column(String(100), primary_key=True)
    notification_enabled = Column(Boolean, nullable=False, default=True)
    notification_channels = Column(JSON, nullable=True)
    alert_thresholds = Column(JSON, nullable=True)
    maintenance_windows = Column(JSON, nullable=True)
    backup_schedule = Column(String(50), nullable=True)
    security_policies = Column(JSON, nullable=True)
    compliance_settings = Column(JSON, nullable=True)
    integration_settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<TenantSettingsDB(tenant_id='{self.tenant_id}')>"


class TenantMemberDB(Base):
    """租户成员表"""

    __tablename__ = "tenant_members"

    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    full_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_tenant_members_tenant_id", "tenant_id"),
        Index("idx_tenant_members_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<TenantMemberDB(id='{self.id}', tenant_id='{self.tenant_id}', role='{self.role}')>"


# ==================== Test Automation Models ====================


class TestSuiteDB(Base):
    """测试套件表"""

    __tablename__ = "test_suites"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    test_type = Column(String(50), nullable=False)
    framework = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    schedule = Column(String(100), nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_test_suites_name", "name"),
        Index("idx_test_suites_status", "status"),
    )

    def __repr__(self):
        return f"<TestSuiteDB(id='{self.id}', name='{self.name}', status='{self.status}')>"


class TestExecutionDB(Base):
    """测试执行表"""

    __tablename__ = "test_executions"

    id = Column(String(100), primary_key=True)
    suite_id = Column(String(100), nullable=False)
    suite_name = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_tests = Column(Integer, nullable=False)
    passed_tests = Column(Integer, nullable=False, default=0)
    failed_tests = Column(Integer, nullable=False, default=0)
    skipped_tests = Column(Integer, nullable=False, default=0)
    trigger_type = Column(String(50), nullable=False, default="manual")
    environment = Column(String(50), nullable=True)
    triggered_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_test_executions_suite_id", "suite_id"),
        Index("idx_test_executions_status", "status"),
    )

    def __repr__(self):
        return f"<TestExecutionDB(id='{self.id}', suite_id='{self.suite_id}', status='{self.status}')>"


# ==================== Test Coverage Models ====================


class TestCoverageReportDB(Base):
    """测试覆盖率报告表"""

    __tablename__ = "test_coverage_reports"

    id = Column(String(100), primary_key=True)
    report_name = Column(String(200), nullable=False)
    overall_coverage = Column(Float, nullable=False, default=0.0)
    overall_level = Column(String(50), nullable=False, default="poor")
    total_modules = Column(Integer, nullable=False, default=0)
    summary = Column(JSON, nullable=True)
    modules = Column(JSON, nullable=True)
    trends = Column(JSON, nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_test_coverage_reports_name", "report_name"),
    )

    def __repr__(self):
        return f"<TestCoverageReportDB(id='{self.id}', report_name='{self.report_name}', coverage={self.overall_coverage})>"


class TestCoverageTargetDB(Base):
    """测试覆盖率目标表"""

    __tablename__ = "test_coverage_targets"

    id = Column(String(100), primary_key=True)
    target_name = Column(String(200), nullable=False)
    module_id = Column(String(100), nullable=True)
    module_name = Column(String(200), nullable=True)
    target_percentage = Column(Float, nullable=False, default=0.0)
    current_percentage = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="not_met")
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_test_coverage_targets_module", "module_id"),
        Index("idx_test_coverage_targets_status", "status"),
    )

    def __repr__(self):
        return f"<TestCoverageTargetDB(id='{self.id}', target_name='{self.target_name}', target={self.target_percentage}%>"


class TestCoverageComparisonDB(Base):
    """测试覆盖率对比表"""

    __tablename__ = "test_coverage_comparisons"

    id = Column(String(100), primary_key=True)
    report_a_id = Column(String(100), nullable=False)
    report_a_name = Column(String(200), nullable=False)
    report_b_id = Column(String(100), nullable=False)
    report_b_name = Column(String(200), nullable=False)
    overall_change = Column(Float, nullable=False, default=0.0)
    module_changes = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)
    comparison_date = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_test_coverage_comparisons_date", "comparison_date"),
    )

    def __repr__(self):
        return f"<TestCoverageComparisonDB(id='{self.id}', change={self.overall_change}%>"


# Dashboard Models
class DashboardWidgetDB(Base):
    """Dashboard widget table"""

    __tablename__ = "dashboard_widgets"

    id = Column(String(50), primary_key=True, nullable=False)
    widget_type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    data_source = Column(String(500), nullable=True)
    refresh_interval = Column(Integer, nullable=False, default=30)
    position = Column(JSON, nullable=True)
    size = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=False)

    __table_args__ = (
        Index("idx_dashboard_widgets_type", "widget_type"),
        Index("idx_dashboard_widgets_enabled", "enabled"),
        Index("idx_dashboard_widgets_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<DashboardWidgetDB(id={self.id}, title='{self.title}', type='{self.widget_type}')>"


class DashboardLayoutDB(Base):
    """Dashboard layout table"""

    __tablename__ = "dashboard_layouts"

    id = Column(String(50), primary_key=True, nullable=False)
    layout_name = Column(String(200), nullable=False)
    layout_type = Column(String(50), nullable=False, default="grid")
    widgets = Column(JSON, nullable=True)
    columns = Column(Integer, nullable=False, default=12)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_dashboard_layouts_name", "layout_name"),
        Index("idx_dashboard_layouts_type", "layout_type"),
        Index("idx_dashboard_layouts_default", "is_default"),
    )

    def __repr__(self):
        return f"<DashboardLayoutDB(id={self.id}, name='{self.layout_name}', type='{self.layout_type}')>"


# Database Advanced Models
class DatabaseOptimizationDB(Base):
    """Database optimization table"""

    __tablename__ = "database_optimizations"

    id = Column(String(50), primary_key=True, nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    query_optimizations = Column(Integer, nullable=False, default=0)
    connection_optimizations = Column(Integer, nullable=False, default=0)
    cache_optimizations = Column(Integer, nullable=False, default=0)
    performance_improvement = Column(Float, nullable=False, default=0.0)
    target_tables = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_database_optimizations_status", "status"),
        Index("idx_database_optimizations_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<DatabaseOptimizationDB(id={self.id}, status='{self.status}')>"


class DatabaseIndexDB(Base):
    """Database index table"""

    __tablename__ = "database_indexes"

    id = Column(String(50), primary_key=True, nullable=False)
    index_name = Column(String(200), nullable=False)
    table_name = Column(String(200), nullable=False, index=True)
    columns = Column(JSON, nullable=False)
    index_type = Column(String(50), nullable=False, default="btree")
    is_unique = Column(Boolean, nullable=False, default=False)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_database_indexes_name", "index_name"),
        Index("idx_database_indexes_table", "table_name"),
    )

    def __repr__(self):
        return f"<DatabaseIndexDB(id={self.id}, name='{self.index_name}', table='{self.table_name}')>"


class DatabaseBackupDB(Base):
    """Database backup table"""

    __tablename__ = "database_backups"

    id = Column(String(50), primary_key=True, nullable=False)
    database_name = Column(String(200), nullable=False, index=True)
    backup_type = Column(String(50), nullable=False, default="full")
    size_bytes = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    compression = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_database_backups_database", "database_name"),
        Index("idx_database_backups_status", "status"),
        Index("idx_database_backups_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<DatabaseBackupDB(id={self.id}, database='{self.database_name}', status='{self.status}')>"


class DatabaseMigrationDB(Base):
    """Database migration table"""

    __tablename__ = "database_migrations"

    id = Column(String(50), primary_key=True, nullable=False)
    migration_name = Column(String(200), nullable=False)
    database_name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    script = Column(Text, nullable=True)
    rollback_script = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    executed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_database_migrations_database", "database_name"),
        Index("idx_database_migrations_status", "status"),
        Index("idx_database_migrations_version", "version"),
    )

    def __repr__(self):
        return f"<DatabaseMigrationDB(id={self.id}, name='{self.migration_name}', version='{self.version}')>"


# Documentation Models
class DocumentationDocumentDB(Base):
    """Documentation document table"""

    __tablename__ = "documentation_documents"

    id = Column(String(50), primary_key=True, nullable=False)
    title = Column(String(200), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    version = Column(String(50), nullable=False, default="1.0")
    status = Column(String(50), nullable=False, default="draft", index=True)
    doc_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_documentation_documents_title", "title"),
        Index("idx_documentation_documents_type", "doc_type"),
        Index("idx_documentation_documents_status", "status"),
        Index("idx_documentation_documents_author", "author"),
    )

    def __repr__(self):
        return f"<DocumentationDocumentDB(id={self.id}, title='{self.title}', type='{self.doc_type}')>"


class DocumentationTemplateDB(Base):
    """Documentation template table"""

    __tablename__ = "documentation_templates"

    id = Column(String(50), primary_key=True, nullable=False)
    template_name = Column(String(200), nullable=False)
    doc_type = Column(String(50), nullable=False, index=True)
    template_content = Column(Text, nullable=False)
    template_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_documentation_templates_name", "template_name"),
        Index("idx_documentation_templates_type", "doc_type"),
    )

    def __repr__(self):
        return f"<DocumentationTemplateDB(id={self.id}, name='{self.template_name}', type='{self.doc_type}')>"


class DocumentationVersionDB(Base):
    """Documentation version table"""

    __tablename__ = "documentation_versions"

    id = Column(String(50), primary_key=True, nullable=False)
    document_id = Column(String(50), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    changes = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_documentation_versions_document", "document_id"),
        Index("idx_documentation_versions_version", "version"),
    )

    def __repr__(self):
        return f"<DocumentationVersionDB(id={self.id}, document_id='{self.document_id}', version='{self.version}')>"


class DocumentationReviewDB(Base):
    """Documentation review table"""

    __tablename__ = "documentation_reviews"

    id = Column(String(50), primary_key=True, nullable=False)
    document_id = Column(String(50), nullable=False, index=True)
    reviewer = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_documentation_reviews_document", "document_id"),
        Index("idx_documentation_reviews_reviewer", "reviewer"),
        Index("idx_documentation_reviews_status", "status"),
    )

    def __repr__(self):
        return f"<DocumentationReviewDB(id={self.id}, document_id='{self.document_id}', reviewer='{self.reviewer}')>"


# Enterprise Models
class EnterpriseTenantDB(Base):
    """Enterprise tenant table"""

    __tablename__ = "enterprise_tenants"

    id = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(200), nullable=False, index=True)
    domain = Column(String(200), nullable=False, unique=True)
    plan = Column(String(50), nullable=False, default="standard", index=True)
    max_users = Column(Integer, nullable=False, default=100)
    status = Column(String(50), nullable=False, default="active", index=True)
    tenant_settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_enterprise_tenants_name", "name"),
        Index("idx_enterprise_tenants_plan", "plan"),
        Index("idx_enterprise_tenants_status", "status"),
    )

    def __repr__(self):
        return f"<EnterpriseTenantDB(id={self.id}, name='{self.name}', domain='{self.domain}')>"


class EnterpriseUserDB(Base):
    """Enterprise user table"""

    __tablename__ = "enterprise_users"

    id = Column(String(50), primary_key=True, nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    role_id = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_enterprise_users_tenant", "tenant_id"),
        Index("idx_enterprise_users_username", "username"),
        Index("idx_enterprise_users_email", "email"),
        Index("idx_enterprise_users_status", "status"),
    )

    def __repr__(self):
        return f"<EnterpriseUserDB(id={self.id}, username='{self.username}', tenant_id='{self.tenant_id}')>"


class EnterpriseRoleDB(Base):
    """Enterprise role table"""

    __tablename__ = "enterprise_roles"

    id = Column(String(50), primary_key=True, nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)
    role_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_enterprise_roles_tenant", "tenant_id"),
        Index("idx_enterprise_roles_name", "role_name"),
    )

    def __repr__(self):
        return f"<EnterpriseRoleDB(id={self.id}, name='{self.role_name}', tenant_id='{self.tenant_id}')>"


class EnterprisePermissionDB(Base):
    """Enterprise permission table"""

    __tablename__ = "enterprise_permissions"

    id = Column(String(50), primary_key=True, nullable=False)
    permission_name = Column(String(100), nullable=False, unique=True)
    resource_type = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_enterprise_permissions_name", "permission_name"),
        Index("idx_enterprise_permissions_resource", "resource_type"),
    )

    def __repr__(self):
        return f"<EnterprisePermissionDB(id={self.id}, name='{self.permission_name}', resource='{self.resource_type}')>"


class EnterpriseAuditLogDB(Base):
    """Enterprise audit log table"""

    __tablename__ = "enterprise_audit_logs"

    id = Column(String(50), primary_key=True, nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(50), nullable=False)
    outcome = Column(String(50), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    data_classification = Column(String(50), nullable=True)
    audit_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_enterprise_audit_logs_tenant", "tenant_id"),
        Index("idx_enterprise_audit_logs_user", "user_id"),
        Index("idx_enterprise_audit_logs_action", "action"),
        Index("idx_enterprise_audit_logs_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<EnterpriseAuditLogDB(id={self.id}, tenant_id='{self.tenant_id}', action='{self.action}')>"


class EnterpriseSettingsDB(Base):
    """Enterprise settings table"""

    __tablename__ = "enterprise_settings"

    id = Column(String(50), primary_key=True, nullable=False)
    setting_key = Column(String(200), nullable=False, unique=True)
    setting_value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_enterprise_settings_key", "setting_key"),
    )

    def __repr__(self):
        return f"<EnterpriseSettingsDB(id={self.id}, key='{self.setting_key}')>"


# ==================== GraphQL Models ====================


class GraphQLQueryConfig(Base):
    """GraphQL查询配置表"""

    __tablename__ = "graphql_query_configs"

    id = Column(String(100), primary_key=True)
    
    # 配置信息
    config_name = Column(String(200), nullable=False, index=True)
    query_template = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    
    # 权限配置
    required_roles = Column(JSON, nullable=True)  # List of roles allowed to execute
    required_permissions = Column(JSON, nullable=True)  # List of permissions required
    
    # 性能配置
    max_complexity = Column(Integer, nullable=True)
    max_depth = Column(Integer, nullable=True)
    timeout_ms = Column(Integer, nullable=True)
    
    # 缓存配置
    cache_enabled = Column(Boolean, default=False, nullable=False)
    cache_ttl_seconds = Column(Integer, nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # 创建和更新信息
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)
    
    # 索引
    __table_args__ = (
        Index("idx_graphql_query_configs_name", "config_name"),
        Index("idx_graphql_query_configs_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<GraphQLQueryConfig(id='{self.id}', name='{self.config_name}', active={self.is_active})>"


class GraphQLQueryHistory(Base):
    """GraphQL查询历史表"""

    __tablename__ = "graphql_query_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 查询信息
    query_id = Column(String(100), nullable=True, index=True)  # Reference to GraphQLQueryConfig
    query_string = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    operation_name = Column(String(100), nullable=True)
    
    # 执行信息
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(50), nullable=True)
    tenant_id = Column(String(50), nullable=True, index=True)
    
    # 性能信息
    execution_time_ms = Column(Float, nullable=True)
    complexity_score = Column(Integer, nullable=True)
    depth = Column(Integer, nullable=True)
    
    # 结果信息
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    result_size_bytes = Column(Integer, nullable=True)
    
    # 请求信息
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # 索引
    __table_args__ = (
        Index("idx_graphql_query_history_query_id", "query_id"),
        Index("idx_graphql_query_history_user_id", "user_id"),
        Index("idx_graphql_query_history_tenant_id", "tenant_id"),
        Index("idx_graphql_query_history_success", "success"),
        Index("idx_graphql_query_history_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<GraphQLQueryHistory(id={self.id}, success={self.success}, time_ms={self.execution_time_ms})>"


class GraphQLPerformanceStats(Base):
    """GraphQL性能统计表"""

    __tablename__ = "graphql_performance_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 统计维度
    stat_type = Column(String(50), nullable=False, index=True)  # query, field, operation
    stat_key = Column(String(200), nullable=False, index=True)  # query name, field name, operation name
    tenant_id = Column(String(50), nullable=True, index=True)
    
    # 时间窗口
    window_start = Column(DateTime, nullable=False, index=True)
    window_end = Column(DateTime, nullable=False, index=True)
    
    # 执行统计
    total_executions = Column(Integer, nullable=False, default=0)
    successful_executions = Column(Integer, nullable=False, default=0)
    failed_executions = Column(Integer, nullable=False, default=0)
    
    # 性能统计
    avg_execution_time_ms = Column(Float, nullable=True)
    min_execution_time_ms = Column(Float, nullable=True)
    max_execution_time_ms = Column(Float, nullable=True)
    p50_execution_time_ms = Column(Float, nullable=True)
    p95_execution_time_ms = Column(Float, nullable=True)
    p99_execution_time_ms = Column(Float, nullable=True)
    
    # 复杂度统计
    avg_complexity = Column(Float, nullable=True)
    avg_depth = Column(Integer, nullable=True)
    
    # 数据量统计
    avg_result_size_bytes = Column(Float, nullable=True)
    total_result_size_bytes = Column(Integer, nullable=False, default=0)
    
    # 错误统计
    error_rate = Column(Float, nullable=True)
    common_errors = Column(JSON, nullable=True)  # Map of error_code -> count
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 索引
    __table_args__ = (
        Index("idx_graphql_performance_stats_type_key", "stat_type", "stat_key"),
        Index("idx_graphql_performance_stats_tenant", "tenant_id"),
        Index("idx_graphql_performance_stats_window", "window_start", "window_end"),
    )
    
    def __repr__(self):
        return f"<GraphQLPerformanceStats(id={self.id}, type='{self.stat_type}', key='{self.stat_key}')>"


# ==================== Service Mesh Models ====================


class MeshConfiguration(Base):
    """Service Mesh Configuration Table"""

    __tablename__ = "mesh_configurations"

    id = Column(String(100), primary_key=True)

    # Configuration details
    name = Column(String(200), nullable=False, index=True)
    mesh_type = Column(String(50), nullable=False, index=True)  # istio, linkerd, consul
    namespace = Column(String(100), nullable=False)
    profile = Column(String(50), nullable=False)

    # Feature flags
    auto_injection_enabled = Column(Boolean, nullable=False)
    mtls_enabled = Column(Boolean, nullable=False)

    # Resource configuration
    resource_limits = Column(JSON, nullable=True)

    # Status
    status = Column(String(20), nullable=False, index=True)  # active, inactive, error
    mesh_id = Column(String(100), nullable=False, index=True)

    # Metadata
    config_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_mesh_configurations_name", "name"),
        Index("idx_mesh_configurations_mesh_type", "mesh_type"),
        Index("idx_mesh_configurations_status", "status"),
        Index("idx_mesh_configurations_mesh_id", "mesh_id"),
    )

    def __repr__(self):
        return f"<MeshConfiguration(id='{self.id}', name='{self.name}', mesh_type='{self.mesh_type}')>"


class TrafficRule(Base):
    """Service Mesh Traffic Rule Table"""

    __tablename__ = "traffic_rules"

    id = Column(String(100), primary_key=True)

    # Rule details
    name = Column(String(200), nullable=False, index=True)
    service_name = Column(String(200), nullable=False, index=True)

    # Traffic configuration
    match_conditions = Column(JSON, nullable=False)
    destination = Column(JSON, nullable=False)
    weight = Column(Integer, nullable=False)  # 0-100
    timeout_seconds = Column(Integer, nullable=False)

    # Advanced features
    retry_policy = Column(JSON, nullable=True)
    fault_injection = Column(JSON, nullable=True)

    # Status
    enabled = Column(Boolean, nullable=False, index=True)

    # Metadata
    rule_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_traffic_rules_name", "name"),
        Index("idx_traffic_rules_service_name", "service_name"),
        Index("idx_traffic_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<TrafficRule(id='{self.id}', name='{self.name}', service='{self.service_name}')>"


class SecurityPolicy(Base):
    """Service Mesh Security Policy Table"""

    __tablename__ = "security_policies"

    id = Column(String(100), primary_key=True)

    # Policy details
    name = Column(String(200), nullable=False, index=True)
    policy_type = Column(String(50), nullable=False, index=True)  # authentication, authorization, security
    target_service = Column(String(200), nullable=False, index=True)

    # mTLS configuration
    mtls_mode = Column(String(20), nullable=False)  # STRICT, PERMISSIVE, DISABLE

    # Principal management
    allowed_principals = Column(JSON, nullable=True)  # List of allowed principals
    denied_principals = Column(JSON, nullable=True)  # List of denied principals

    # JWT validation
    jwt_validation = Column(JSON, nullable=True)

    # Status
    enabled = Column(Boolean, nullable=False, index=True)

    # Metadata
    policy_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_security_policies_name", "name"),
        Index("idx_security_policies_policy_type", "policy_type"),
        Index("idx_security_policies_target_service", "target_service"),
        Index("idx_security_policies_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<SecurityPolicy(id='{self.id}', name='{self.name}', type='{self.policy_type}')>"


class ObservabilityConfig(Base):
    """Service Mesh Observability Configuration Table"""

    __tablename__ = "observability_configs"

    id = Column(String(100), primary_key=True)

    # Configuration details
    name = Column(String(200), nullable=False, index=True)

    # Feature flags
    tracing_enabled = Column(Boolean, nullable=False)
    metrics_enabled = Column(Boolean, nullable=False)
    access_logging_enabled = Column(Boolean, nullable=False)

    # Sampling configuration
    sampling_rate = Column(Float, nullable=False)  # 0.0-1.0

    # Integration flags
    prometheus_enabled = Column(Boolean, nullable=False)
    grafana_enabled = Column(Boolean, nullable=False)

    # Status
    enabled = Column(Boolean, nullable=False, index=True)

    # Metadata
    config_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_observability_configs_name", "name"),
        Index("idx_observability_configs_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<ObservabilityConfig(id='{self.id}', name='{self.name}')>"


class Policy(Base):
    """Service Mesh Generic Policy Table"""

    __tablename__ = "policies"

    id = Column(String(100), primary_key=True)

    # Policy details
    name = Column(String(200), nullable=False, index=True)
    policy_type = Column(String(50), nullable=False, index=True)
    target_service = Column(String(200), nullable=False, index=True)

    # Policy rules
    rules = Column(JSON, nullable=False)

    # Status
    enabled = Column(Boolean, nullable=False, index=True)

    # Metadata
    policy_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_policies_name", "name"),
        Index("idx_policies_policy_type", "policy_type"),
        Index("idx_policies_target_service", "target_service"),
        Index("idx_policies_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<Policy(id='{self.id}', name='{self.name}', type='{self.policy_type}')>"


# ==================== Integration Ecosystem Models ====================


class IntegrationDB(Base):
    """Integration configuration table for the integration ecosystem"""

    __tablename__ = "integrations"

    id = Column(String(100), primary_key=True)
    
    # Integration identification
    integration_type = Column(String(50), nullable=False, index=True)  # monitoring, cloud, cicd, itsm, notification, webhook, custom
    name = Column(String(200), nullable=False, index=True)
    
    # Configuration
    config = Column(JSON, nullable=False)  # Integration-specific configuration
    
    # Status
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    status = Column(String(20), default="inactive", nullable=False, index=True)  # active, inactive, error, configuring
    
    # Testing information
    last_tested = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    integration_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_integrations_type", "integration_type"),
        Index("idx_integrations_name", "name"),
        Index("idx_integrations_enabled", "enabled"),
        Index("idx_integrations_status", "status"),
        Index("idx_integrations_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<IntegrationDB(id='{self.id}', type='{self.integration_type}', name='{self.name}', status='{self.status}')>"


class WebhookDB(Base):
    """Webhook registration table for the integration ecosystem"""

    __tablename__ = "webhooks"

    id = Column(String(100), primary_key=True)
    
    # Webhook identification
    source = Column(String(100), nullable=False, index=True)  # Source system identifier
    event_type = Column(String(100), nullable=False, index=True)  # Type of events to receive
    endpoint = Column(String(500), nullable=False)  # Webhook endpoint URL
    
    # Security
    secret = Column(String(255), nullable=True)  # Webhook secret for signature validation
    
    # Status
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadata
    webhook_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_webhooks_source", "source"),
        Index("idx_webhooks_event_type", "event_type"),
        Index("idx_webhooks_enabled", "enabled"),
        Index("idx_webhooks_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<WebhookDB(id='{self.id}', source='{self.source}', event_type='{self.event_type}', enabled={self.enabled})>"


class WebhookEventDB(Base):
    """Webhook event history table for the integration ecosystem"""

    __tablename__ = "webhook_events"

    id = Column(String(100), primary_key=True)
    
    # Event identification
    webhook_id = Column(String(100), nullable=False, index=True)  # Reference to WebhookDB
    source = Column(String(100), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Event data
    payload = Column(JSON, nullable=False)  # Event payload
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Processing result
    processing_result = Column(JSON, nullable=True)  # Processing result details
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_webhook_events_webhook_id", "webhook_id"),
        Index("idx_webhook_events_source", "source"),
        Index("idx_webhook_events_event_type", "event_type"),
        Index("idx_webhook_events_processed", "processed"),
        Index("idx_webhook_events_timestamp", "timestamp"),
    )
    
    def __repr__(self):
        return f"<WebhookEventDB(id='{self.id}', webhook_id='{self.webhook_id}', processed={self.processed})>"


class IntegrationNotificationChannelDB(Base):
    """Notification channel table for the integration ecosystem"""

    __tablename__ = "integration_notification_channels"

    id = Column(String(100), primary_key=True)
    
    # Channel identification
    name = Column(String(200), nullable=False, unique=True, index=True)
    channel_type = Column(String(50), nullable=False, index=True)  # slack, teams, dingtalk, wechat, email, webhook
    
    # Channel configuration
    config = Column(JSON, nullable=False)  # Channel-specific configuration
    
    # Status
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)  # Higher priority = used first
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_integration_notification_channels_name", "name"),
        Index("idx_integration_notification_channels_type", "channel_type"),
        Index("idx_integration_notification_channels_enabled", "enabled"),
    )
    
    def __repr__(self):
        return f"<IntegrationNotificationChannelDB(id='{self.id}', name='{self.name}', type='{self.channel_type}', enabled={self.enabled})>"


class IntegrationNotificationMessageDB(Base):
    """Notification message table for the integration ecosystem"""

    __tablename__ = "integration_notification_messages"

    id = Column(String(100), primary_key=True)
    
    # Message identification
    channel_id = Column(String(100), nullable=False, index=True)  # Reference to IntegrationNotificationChannelDB
    recipient = Column(String(255), nullable=False)
    
    # Message content
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(20), default="normal", nullable=False)  # normal, high, urgent
    
    # Processing status
    sent = Column(Boolean, default=False, nullable=False, index=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Metadata
    message_metadata = Column(JSON, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_integration_notification_messages_channel_id", "channel_id"),
        Index("idx_integration_notification_messages_sent", "sent"),
        Index("idx_integration_notification_messages_timestamp", "timestamp"),
    )
    
    def __repr__(self):
        return f"<IntegrationNotificationMessageDB(id='{self.id}', channel_id='{self.channel_id}', sent={self.sent})>"


# ============================================================================
# Database Monitoring Models
# ============================================================================


class DatabaseMetricThresholdDB(Base):
    """数据库指标阈值配置表"""

    __tablename__ = "database_metric_thresholds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_type = Column(String(50), unique=True, nullable=False, index=True)  # query_time, connection_count, etc.
    warning_threshold = Column(Float, nullable=False)
    critical_threshold = Column(Float, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_database_metric_thresholds_metric_type", "metric_type"),
        Index("idx_database_metric_thresholds_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<DatabaseMetricThresholdDB(id={self.id}, metric_type='{self.metric_type}', enabled={self.enabled})>"


class DatabaseMonitoringConfigDB(Base):
    """数据库监控配置表"""

    __tablename__ = "database_monitoring_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    collection_interval = Column(Integer, default=60, nullable=False)  # seconds
    retention_days = Column(Integer, default=30, nullable=False)
    enable_realtime = Column(Boolean, default=True, nullable=False)
    enable_slow_query_log = Column(Boolean, default=True, nullable=False)
    slow_query_threshold = Column(Float, default=1.0, nullable=False)  # seconds
    enable_connection_monitoring = Column(Boolean, default=True, nullable=False)
    max_connections_threshold = Column(Integer, default=100, nullable=False)
    enable_deadlock_detection = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(50), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_database_monitoring_configs_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<DatabaseMonitoringConfigDB(id={self.id}, enabled={self.enabled}, collection_interval={self.collection_interval})>"


class DatabasePerformanceBaselineDB(Base):
    """数据库性能基线表"""

    __tablename__ = "database_performance_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    baseline_name = Column(String(200), unique=True, nullable=False, index=True)
    established_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    avg_query_time = Column(Float, nullable=False)  # milliseconds
    p95_query_time = Column(Float, nullable=False)  # milliseconds
    p99_query_time = Column(Float, nullable=False)  # milliseconds
    avg_connection_count = Column(Float, nullable=False)
    peak_connection_count = Column(Integer, nullable=False)
    cache_hit_ratio = Column(Float, nullable=False)
    database_size_mb = Column(Float, nullable=False)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_database_performance_baselines_name", "baseline_name"),
        Index("idx_database_performance_baselines_established_at", "established_at"),
    )

    def __repr__(self):
        return f"<DatabasePerformanceBaselineDB(id={self.id}, baseline_name='{self.baseline_name}')>"


class DatabaseAlertRuleDB(Base):
    """数据库告警规则表"""

    __tablename__ = "database_alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    rule_name = Column(String(200), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)  # query_time, connection_count, etc.
    condition = Column(Text, nullable=False)  # e.g., "query_time > 500"
    severity = Column(String(20), nullable=False, index=True)  # info, warning, error, critical
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    notification_channels = Column(JSON, nullable=True)  # List of channels: ["email", "slack"]
    cooldown_minutes = Column(Integer, default=5, nullable=False)
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_database_alert_rules_rule_id", "rule_id"),
        Index("idx_database_alert_rules_metric_type", "metric_type"),
        Index("idx_database_alert_rules_severity", "severity"),
        Index("idx_database_alert_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<DatabaseAlertRuleDB(id={self.id}, rule_id='{self.rule_id}', enabled={self.enabled})>"


class DatabaseMonitoringStatusDB(Base):
    """数据库监控状态表"""

    __tablename__ = "database_monitoring_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitoring_enabled = Column(Boolean, default=True, nullable=False, index=True)
    last_collection_time = Column(DateTime, nullable=True, index=True)
    active_alerts = Column(Integer, default=0, nullable=False)
    total_metrics_collected = Column(Integer, default=0, nullable=False)
    database_health = Column(String(20), default="healthy", nullable=False)  # healthy, degraded, critical
    uptime_percentage = Column(Float, default=100.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_database_monitoring_status_enabled", "monitoring_enabled"),
        Index("idx_database_monitoring_status_last_collection", "last_collection_time"),
    )

    def __repr__(self):
        return f"<DatabaseMonitoringStatusDB(id={self.id}, monitoring_enabled={self.monitoring_enabled}, health='{self.database_health}')>"


# ==================== Security Management Models ====================


class SecurityKey(Base):
    """密钥管理表"""

    __tablename__ = "security_keys"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    key_type = Column(String(50), nullable=False, index=True)  # api_key, secret_key, jwt, ssh, certificate
    algorithm = Column(String(50), nullable=False, default="RSA")
    key_size = Column(Integer, nullable=False, default=2048)
    
    # 加密存储的密钥值
    encrypted_key_value = Column(Text, nullable=False)
    encrypted_key_iv = Column(String(100), nullable=False)
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, inactive, expired, revoked
    auto_renew = Column(Boolean, default=False, nullable=False)
    
    # 时间信息
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(), nullable=True, index=True)
    last_rotated_at = Column(DateTime(), nullable=True)
    last_used_at = Column(DateTime(), nullable=True)
    
    # 使用信息
    usage = Column(JSON, nullable=True)  # List of usage contexts
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_security_keys_name", "name"),
        Index("idx_security_keys_type", "key_type"),
        Index("idx_security_keys_status", "status"),
        Index("idx_security_keys_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<SecurityKey(id='{self.id}', name='{self.name}', type='{self.key_type}', status='{self.status}')>"


class MfaMethod(Base):
    """MFA方法表"""

    __tablename__ = "mfa_methods"

    id = Column(String(100), primary_key=True)
    method_type = Column(String(50), nullable=False, index=True)  # totp, sms, email, hardware_token, biometric
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # 配置
    config = Column(JSON, nullable=False)  # Method-specific configuration
    secret = Column(Text, nullable=True)  # Encrypted secret for TOTP
    
    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    required = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1-10
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_mfa_methods_type", "method_type"),
        Index("idx_mfa_methods_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<MfaMethod(id='{self.id}', type='{self.method_type}', name='{self.name}', enabled={self.enabled})>"


class AbacPolicy(Base):
    """ABAC策略表"""

    __tablename__ = "abac_policies"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    effect = Column(String(20), nullable=False, default="allow")  # allow, deny
    
    # 策略条件
    subjects = Column(JSON, nullable=True)  # Subject conditions
    resources = Column(JSON, nullable=True)  # Resource conditions
    actions = Column(JSON, nullable=True)  # Action conditions
    environment = Column(JSON, nullable=True)  # Environment conditions
    
    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_abac_policies_name", "name"),
        Index("idx_abac_policies_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<AbacPolicy(id='{self.id}', name='{self.name}', effect='{self.effect}', enabled={self.enabled})>"


class RbacRole(Base):
    """RBAC角色表"""

    __tablename__ = "rbac_roles"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # 权限
    permissions = Column(JSON, nullable=False)  # List of permissions
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, inactive
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_rbac_roles_name", "name"),
        Index("idx_rbac_roles_status", "status"),
    )

    def __repr__(self):
        return f"<RbacRole(id='{self.id}', name='{self.name}', status='{self.status}')>"


class RateLimitRule(Base):
    """速率限制规则表"""

    __tablename__ = "rate_limit_rules"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    endpoint = Column(String(256), nullable=False, index=True)
    
    # 限制配置
    limit = Column(Integer, nullable=False)  # Requests per window
    window_seconds = Column(Integer, default=60, nullable=False)  # Time window in seconds
    burst_limit = Column(Integer, nullable=True)  # Burst limit
    
    # 策略
    strategy = Column(String(50), default="fixed_window", nullable=False)  # fixed_window, sliding_window, token_bucket
    
    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_rate_limit_rules_name", "name"),
        Index("idx_rate_limit_rules_endpoint", "endpoint"),
        Index("idx_rate_limit_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<RateLimitRule(id='{self.id}', name='{self.name}', endpoint='{self.endpoint}', limit={self.limit})>"


class HttpsCertificate(Base):
    """HTTPS证书表"""

    __tablename__ = "https_certificates"

    id = Column(String(100), primary_key=True)
    domain = Column(String(256), nullable=False, index=True)
    
    # 证书信息
    certificate_pem = Column(Text, nullable=False)
    private_key_encrypted = Column(Text, nullable=False)
    private_key_iv = Column(String(100), nullable=False)
    issuer = Column(String(256), nullable=True)
    algorithm = Column(String(50), nullable=False, default="RSA")
    
    # 有效期
    issued_at = Column(DateTime(), nullable=False)
    expires_at = Column(DateTime(), nullable=False, index=True)
    
    # 状态
    status = Column(String(20), nullable=False, default="valid", index=True)  # valid, expired, revoked
    auto_renew = Column(Boolean, default=False, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_https_certificates_domain", "domain"),
        Index("idx_https_certificates_status", "status"),
        Index("idx_https_certificates_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<HttpsCertificate(id='{self.id}', domain='{self.domain}', status='{self.status}')>"


class SnapshotEncryption(Base):
    """快照加密表"""

    __tablename__ = "snapshot_encryptions"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    source = Column(String(256), nullable=False)
    
    # 加密信息
    encryption_algorithm = Column(String(50), nullable=False, default="AES-256")
    key_id = Column(String(100), nullable=True)  # Reference to SecurityKey
    
    # 快照数据
    pre_state_encrypted = Column(Text, nullable=False)
    pre_state_iv = Column(String(100), nullable=False)
    post_state_encrypted = Column(Text, nullable=True)
    post_state_iv = Column(String(100), nullable=True)
    rollback_plan = Column(Text, nullable=True)
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, archived
    
    # 保留策略
    retention_days = Column(Integer, nullable=False, default=7)
    expires_at = Column(DateTime(), nullable=False, index=True)
    completed_at = Column(DateTime(), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_snapshot_encryptions_name", "name"),
        Index("idx_snapshot_encryptions_status", "status"),
        Index("idx_snapshot_encryptions_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<SnapshotEncryption(id='{self.id}', name='{self.name}', status='{self.status}')>"


class DataEncryptionKey(Base):
    """数据加密密钥表"""

    __tablename__ = "data_encryption_keys"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    
    # 密钥信息
    key_encrypted = Column(Text, nullable=False)
    key_iv = Column(String(100), nullable=False)
    algorithm = Column(String(50), nullable=False, default="AES-256")
    key_size = Column(Integer, nullable=False, default=256)
    
    # 用途
    purpose = Column(String(50), nullable=False)  # database, file, field
    scope = Column(String(256), nullable=True)  # Specific scope (e.g., table name)
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, disabled, rotated
    
    # 轮换
    rotation_enabled = Column(Boolean, default=False, nullable=False)
    rotation_interval_days = Column(Integer, nullable=True)
    last_rotated_at = Column(DateTime(), nullable=True)
    next_rotation_at = Column(DateTime(), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_data_encryption_keys_name", "name"),
        Index("idx_data_encryption_keys_status", "status"),
        Index("idx_data_encryption_keys_purpose", "purpose"),
    )

    def __repr__(self):
        return f"<DataEncryptionKey(id='{self.id}', name='{self.name}', purpose='{self.purpose}', status='{self.status}')>"


class PrivacySubject(Base):
    """隐私主体表"""

    __tablename__ = "privacy_subjects"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    subject_type = Column(String(50), nullable=False, index=True)  # user, customer
    
    # 隐私信息
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    identifier = Column(String(255), nullable=True)  # Unique identifier
    
    # 同意
    consent_level = Column(String(20), nullable=False, default="partial")  # full, partial, none
    consent_given_at = Column(DateTime(), nullable=True)
    consent_updated_at = Column(DateTime(), nullable=True)
    
    # 数据处理
    data_categories = Column(JSON, nullable=True)  # List of data categories
    processing_purposes = Column(JSON, nullable=True)  # List of purposes
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_privacy_subjects_name", "name"),
        Index("idx_privacy_subjects_type", "subject_type"),
    )

    def __repr__(self):
        return f"<PrivacySubject(id='{self.id}', name='{self.name}', type='{self.subject_type}')>"


class CompliancePolicy(Base):
    """合规策略表"""

    __tablename__ = "compliance_policies"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    framework = Column(String(50), nullable=False, index=True)  # GDPR, HIPAA, SOC2, ISO27001
    
    # 策略内容
    description = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=False)  # List of requirements
    controls = Column(JSON, nullable=True)  # List of controls
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, inactive
    
    # 审计
    last_audit_date = Column(DateTime(), nullable=True)
    next_audit_date = Column(DateTime(), nullable=True)
    audit_frequency_days = Column(Integer, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_compliance_policies_name", "name"),
        Index("idx_compliance_policies_framework", "framework"),
        Index("idx_compliance_policies_status", "status"),
    )

    def __repr__(self):
        return f"<CompliancePolicy(id='{self.id}', name='{self.name}', framework='{self.framework}', status='{self.status}')>"


class ComplianceStandard(Base):
    """合规检查标准表"""

    __tablename__ = "compliance_standards"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    category = Column(String(50), nullable=False, default="general")
    
    # 标准内容
    description = Column(Text, nullable=False)
    check_criteria = Column(JSON, nullable=False)  # Check criteria
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, inactive
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_compliance_standards_name", "name"),
        Index("idx_compliance_standards_category", "category"),
        Index("idx_compliance_standards_status", "status"),
    )

    def __repr__(self):
        return f"<ComplianceStandard(id='{self.id}', name='{self.name}', category='{self.category}', status='{self.status}')>"


class DatabaseSecurityInstance(Base):
    """数据库安全实例表"""

    __tablename__ = "database_security_instances"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    instance_type = Column(String(50), nullable=False, index=True)  # postgresql, mysql
    host = Column(String(256), nullable=False)
    port = Column(Integer, nullable=True)
    
    # 安全配置
    encryption_enabled = Column(Boolean, default=False, nullable=False)
    ssl_enabled = Column(Boolean, default=False, nullable=False)
    audit_enabled = Column(Boolean, default=False, nullable=False)
    
    # 访问控制
    allowed_ips = Column(JSON, nullable=True)  # List of allowed IPs
    allowed_users = Column(JSON, nullable=True)  # List of allowed users
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, inactive
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_database_security_instances_name", "name"),
        Index("idx_database_security_instances_type", "instance_type"),
        Index("idx_database_security_instances_status", "status"),
    )

    def __repr__(self):
        return f"<DatabaseSecurityInstance(id='{self.id}', name='{self.name}', type='{self.instance_type}', status='{self.status}')>"


class ApiSecurityEndpoint(Base):
    """API安全端点表"""

    __tablename__ = "api_security_endpoints"

    id = Column(String(100), primary_key=True)
    path = Column(String(256), nullable=False, index=True)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, etc.
    
    # 安全配置
    authentication_required = Column(Boolean, default=True, nullable=False)
    authorization_required = Column(Boolean, default=True, nullable=False)
    rate_limit_enabled = Column(Boolean, default=True, nullable=False)
    rate_limit_rule_id = Column(String(100), nullable=True)
    
    # 访问控制
    allowed_roles = Column(JSON, nullable=True)  # List of allowed roles
    allowed_permissions = Column(JSON, nullable=True)  # List of required permissions
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, disabled
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_api_security_endpoints_path", "path"),
        Index("idx_api_security_endpoints_status", "status"),
    )

    def __repr__(self):
        return f"<ApiSecurityEndpoint(id='{self.id}', path='{self.path}', method='{self.method}', status='{self.status}')>"


class InputValidationRule(Base):
    """输入验证规则表"""

    __tablename__ = "input_validation_rules"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    field = Column(String(128), nullable=False, index=True)
    
    # 验证规则
    validation_type = Column(String(50), nullable=False)  # regex, length, type, range, custom
    validation_pattern = Column(String(500), nullable=True)  # Regex pattern
    min_length = Column(Integer, nullable=True)
    max_length = Column(Integer, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    allowed_values = Column(JSON, nullable=True)  # List of allowed values
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_input_validation_rules_name", "name"),
        Index("idx_input_validation_rules_field", "field"),
        Index("idx_input_validation_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<InputValidationRule(id='{self.id}', name='{self.name}', field='{self.field}', enabled={self.enabled})>"


class PenetrationTestProject(Base):
    """渗透测试项目表"""

    __tablename__ = "penetration_test_projects"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    target = Column(String(256), nullable=False)
    
    # 测试配置
    test_type = Column(String(50), nullable=False)  # black_box, white_box, gray_box
    scope = Column(JSON, nullable=True)  # Test scope
    methodology = Column(String(50), nullable=True)  # OWASP, NIST, custom
    
    # 状态
    status = Column(String(20), nullable=False, default="scheduled", index=True)  # scheduled, in_progress, completed, cancelled
    start_date = Column(DateTime(), nullable=True)
    end_date = Column(DateTime(), nullable=True)
    
    # 结果
    findings = Column(JSON, nullable=True)  # List of findings
    risk_score = Column(Float, nullable=True)  # Overall risk score
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_penetration_test_projects_name", "name"),
        Index("idx_penetration_test_projects_status", "status"),
    )

    def __repr__(self):
        return f"<PenetrationTestProject(id='{self.id}', name='{self.name}', status='{self.status}')>"


class SecurityTest(Base):
    """安全测试表"""

    __tablename__ = "security_tests"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    test_type = Column(String(50), nullable=False, index=True)  # sast, dast, sca, dependency_check
    
    # 测试配置
    target = Column(String(256), nullable=True)
    parameters = Column(JSON, nullable=True)  # Test parameters
    
    # 状态
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    started_at = Column(DateTime(), nullable=True)
    completed_at = Column(DateTime(), nullable=True)
    
    # 结果
    results = Column(JSON, nullable=True)  # Test results
    vulnerabilities_found = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    high_count = Column(Integer, default=0, nullable=False)
    medium_count = Column(Integer, default=0, nullable=False)
    low_count = Column(Integer, default=0, nullable=False)
    
    # 错误
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_security_tests_name", "name"),
        Index("idx_security_tests_type", "test_type"),
        Index("idx_security_tests_status", "status"),
    )

    def __repr__(self):
        return f"<SecurityTest(id='{self.id}', name='{self.name}', type='{self.test_type}', status='{self.status}')>"


class VulnerabilityTicket(Base):
    """漏洞工单表"""

    __tablename__ = "vulnerability_tickets"

    id = Column(String(100), primary_key=True)
    title = Column(String(128), nullable=False, index=True)
    
    # 漏洞信息
    cve_id = Column(String(50), nullable=True, index=True)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    cvss_score = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    
    # 受影响资源
    affected_components = Column(JSON, nullable=True)  # List of affected components
    
    # 状态
    status = Column(String(20), nullable=False, default="open", index=True)  # open, in_progress, resolved, closed
    assigned_to = Column(String(50), nullable=True)
    
    # 修复
    fix_status = Column(String(20), nullable=True)  # not_started, in_progress, completed, verified
    fix_description = Column(Text, nullable=True)
    
    # 时间信息
    detected_at = Column(DateTime(), nullable=False, index=True)
    resolved_at = Column(DateTime(), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_vulnerability_tickets_title", "title"),
        Index("idx_vulnerability_tickets_severity", "severity"),
        Index("idx_vulnerability_tickets_status", "status"),
        Index("idx_vulnerability_tickets_cve_id", "cve_id"),
        Index("idx_vulnerability_tickets_detected_at", "detected_at"),
    )

    def __repr__(self):
        return f"<VulnerabilityTicket(id='{self.id}', title='{self.title}', severity='{self.severity}', status='{self.status}')>"


class ThreatIntelligence(Base):
    """威胁情报表"""

    __tablename__ = "threat_intelligence"

    id = Column(String(100), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    threat_type = Column(String(50), nullable=False, index=True)  # malware, exploit, phishing, ddos
    
    # 威胁信息
    description = Column(Text, nullable=False)
    indicators = Column(JSON, nullable=True)  # IOCs (Indicators of Compromise)
    source = Column(String(256), nullable=True)
    
    # 严重程度
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    confidence = Column(Float, nullable=False)  # 0-1
    
    # 状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active, expired, false_positive
    
    # 时间信息
    first_seen = Column(DateTime(), nullable=True)
    last_seen = Column(DateTime(), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_threat_intelligence_name", "name"),
        Index("idx_threat_intelligence_type", "threat_type"),
        Index("idx_threat_intelligence_status", "status"),
    )

    def __repr__(self):
        return f"<ThreatIntelligence(id='{self.id}', name='{self.name}', type='{self.threat_type}', status='{self.status}')>"


class VulnerabilityScan(Base):
    """漏洞扫描表"""

    __tablename__ = "vulnerability_scans"

    id = Column(String(100), primary_key=True)
    target = Column(String(256), nullable=False, index=True)
    scan_type = Column(String(50), nullable=False)  # full, quick, custom
    
    # 扫描配置
    parameters = Column(JSON, nullable=True)  # Scan parameters
    
    # 状态
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    started_at = Column(DateTime(), nullable=True)
    completed_at = Column(DateTime(), nullable=True)
    
    # 结果
    results = Column(JSON, nullable=True)  # Scan results
    vulnerabilities_found = Column(Integer, default=0, nullable=False)
    
    # 错误
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_vulnerability_scans_target", "target"),
        Index("idx_vulnerability_scans_status", "status"),
    )

    def __repr__(self):
        return f"<VulnerabilityScan(id='{self.id}', target='{self.target}', status='{self.status}')>"


class AuditReport(Base):
    """审计报告表"""

    __tablename__ = "audit_reports"

    id = Column(String(100), primary_key=True)
    title = Column(String(128), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # security, compliance, access
    
    # 报告内容
    description = Column(Text, nullable=True)
    findings = Column(JSON, nullable=True)  # List of findings
    recommendations = Column(JSON, nullable=True)  # List of recommendations
    
    # 范围
    scope = Column(JSON, nullable=True)  # Audit scope
    time_range_start = Column(DateTime(), nullable=True)
    time_range_end = Column(DateTime(), nullable=True)
    
    # 状态
    status = Column(String(20), nullable=False, default="draft", index=True)  # draft, published, archived
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(DateTime(), nullable=True)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_audit_reports_title", "title"),
        Index("idx_audit_reports_type", "report_type"),
        Index("idx_audit_reports_status", "status"),
    )

    def __repr__(self):
        return f"<AuditReport(id='{self.id}', title='{self.title}', type='{self.report_type}', status='{self.status}')>"


class SecurityOperationRecord(Base):
    """安全操作记录表"""

    __tablename__ = "security_operation_records"

    id = Column(String(100), primary_key=True)
    operation = Column(String(100), nullable=False, index=True)  # deploy, configure, delete, etc.
    
    # 操作详情
    operation_type = Column(String(50), nullable=False)  # manual, automated, system
    target_resource = Column(String(256), nullable=True)
    parameters = Column(JSON, nullable=True)
    
    # 执行信息
    executor = Column(String(50), nullable=True)  # User or system
    result = Column(String(20), nullable=False)  # success, failure, partial
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    timestamp = Column(DateTime(), server_default=func.now(), nullable=False, index=True)
    duration_ms = Column(Integer, nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_security_operation_records_operation", "operation"),
        Index("idx_security_operation_records_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<SecurityOperationRecord(id='{self.id}', operation='{self.operation}', result='{self.result}')>"


class CommandRewriteRule(Base):
    """命令改写规则表"""

    __tablename__ = "command_rewrite_rules"

    id = Column(String(100), primary_key=True)
    pattern = Column(String(256), nullable=False, index=True)
    replacement = Column(String(256), nullable=False)
    
    # 规则配置
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=0, nullable=False)
    
    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # 统计
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_command_rewrite_rules_pattern", "pattern"),
        Index("idx_command_rewrite_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<CommandRewriteRule(id='{self.id}', pattern='{self.pattern}', enabled={self.enabled})>"


class CommandGuardRule(Base):
    """命令管控规则表"""

    __tablename__ = "command_guard_rules"

    id = Column(String(100), primary_key=True)
    command = Column(String(256), nullable=False, index=True)
    pattern = Column(String(256), nullable=False)
    
    # 规则配置
    severity = Column(String(20), nullable=False, default="high")  # critical, high, medium, low
    action = Column(String(20), nullable=False, default="block")  # block, warn, allow
    description = Column(Text, nullable=True)
    
    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # 统计
    trigger_count = Column(Integer, default=0, nullable=False)
    last_triggered_at = Column(DateTime(), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(50), nullable=True)
    
    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_command_guard_rules_command", "command"),
        Index("idx_command_guard_rules_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<CommandGuardRule(id='{self.id}', command='{self.command}', enabled={self.enabled})>"


# ==================== Frontend Models ====================


class FrontendComponent(Base):
    """前端组件表"""

    __tablename__ = "frontend_components"

    id = Column(String(100), primary_key=True)

    # 组件信息
    name = Column(String(200), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)

    # 组件配置
    props = Column(JSON, nullable=True)
    code = Column(Text, nullable=False)
    dependencies = Column(JSON, nullable=True)  # List of strings

    # 访问控制
    is_public = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(50), nullable=True)  # user_id

    # 状态
    status = Column(String(20), default="active", nullable=False, index=True)  # active, deprecated, archived

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_frontend_components_name", "name"),
        Index("idx_frontend_components_type", "type"),
        Index("idx_frontend_components_category", "category"),
        Index("idx_frontend_components_status", "status"),
        Index("idx_frontend_components_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<FrontendComponent(id='{self.id}', name='{self.name}', type='{self.type}')>"


class FrontendTheme(Base):
    """前端主题表"""

    __tablename__ = "frontend_themes"

    id = Column(String(100), primary_key=True)

    # 主题信息
    name = Column(String(200), nullable=False, index=True)
    base_theme = Column(String(20), nullable=False, index=True)  # light, dark, auto
    description = Column(Text, nullable=True)

    # 主题配置
    colors = Column(JSON, nullable=False)
    fonts = Column(JSON, nullable=True)
    spacing = Column(JSON, nullable=True)

    # 访问控制
    is_default = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(50), nullable=True)  # user_id

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_frontend_themes_name", "name"),
        Index("idx_frontend_themes_base_theme", "base_theme"),
        Index("idx_frontend_themes_is_default", "is_default"),
        Index("idx_frontend_themes_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<FrontendTheme(id='{self.id}', name='{self.name}', base_theme='{self.base_theme}')>"


class FrontendLayout(Base):
    """前端布局表"""

    __tablename__ = "frontend_layouts"

    id = Column(String(100), primary_key=True)

    # 布局信息
    name = Column(String(200), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # dashboard, page, modal
    description = Column(Text, nullable=True)

    # 布局配置
    structure = Column(JSON, nullable=False)
    breakpoints = Column(JSON, nullable=True)

    # 访问控制
    is_default = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(50), nullable=True)  # user_id

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_frontend_layouts_name", "name"),
        Index("idx_frontend_layouts_type", "type"),
        Index("idx_frontend_layouts_is_default", "is_default"),
        Index("idx_frontend_layouts_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<FrontendLayout(id='{self.id}', name='{self.name}', type='{self.type}')>"


class FrontendUserPreference(Base):
    """前端用户偏好表"""

    __tablename__ = "frontend_user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 用户关联
    user_id = Column(String(50), nullable=False, unique=True, index=True)

    # 偏好设置
    theme = Column(String(20), default="auto", nullable=False)  # light, dark, auto
    language = Column(String(10), default="zh-CN", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    date_format = Column(String(20), default="YYYY-MM-DD", nullable=False)
    time_format = Column(String(20), default="HH:mm:ss", nullable=False)
    view_mode = Column(String(20), default="grid", nullable=False)  # grid, list, compact, detailed

    # 通知设置
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    notification_sound = Column(Boolean, default=False, nullable=False)
    auto_refresh_interval = Column(Integer, default=30, nullable=False)  # seconds

    # 自定义配置
    dashboard_layout = Column(JSON, nullable=True)
    custom_colors = Column(JSON, nullable=True)
    accessibility_settings = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_frontend_user_preferences_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<FrontendUserPreference(id={self.id}, user_id='{self.user_id}', theme='{self.theme}')>"


class FrontendDashboardWidget(Base):
    """前端仪表板小部件表"""

    __tablename__ = "frontend_dashboard_widgets"

    id = Column(String(100), primary_key=True)

    # 仪表板关联
    dashboard_id = Column(String(100), nullable=False, index=True)

    # 小部件信息
    widget_id = Column(String(100), nullable=False, index=True)
    widget_type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)

    # 小部件配置
    position = Column(JSON, nullable=False)  # {x, y, width, height}
    config = Column(JSON, nullable=True)
    data_source = Column(String(200), nullable=True)
    refresh_interval = Column(Integer, default=30, nullable=False)  # seconds

    # 状态
    enabled = Column(Boolean, default=True, nullable=False)

    # 创建者
    created_by = Column(String(50), nullable=True)  # user_id

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_frontend_dashboard_widgets_dashboard_id", "dashboard_id"),
        Index("idx_frontend_dashboard_widgets_widget_id", "widget_id"),
        Index("idx_frontend_dashboard_widgets_widget_type", "widget_type"),
        Index("idx_frontend_dashboard_widgets_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<FrontendDashboardWidget(id='{self.id}', dashboard_id='{self.dashboard_id}', widget_type='{self.widget_type}')>"


class FrontendReportTemplate(Base):
    """前端报告模板表"""

    __tablename__ = "frontend_report_templates"

    id = Column(String(100), primary_key=True)

    # 模板信息
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # 数据源配置
    data_sources = Column(JSON, nullable=False)  # List of strings
    filters = Column(JSON, nullable=True)
    visualization_config = Column(JSON, nullable=True)

    # 输出配置
    format = Column(String(20), default="pdf", nullable=False)  # pdf, html, csv
    schedule = Column(String(100), nullable=True)  # cron expression

    # 创建者
    created_by = Column(String(50), nullable=True)  # user_id

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 索引
    __table_args__ = (
        Index("idx_frontend_report_templates_name", "name"),
        Index("idx_frontend_report_templates_created_by", "created_by"),
    )

    def __repr__(self):
        return f"<FrontendReportTemplate(id='{self.id}', name='{self.name}', format='{self.format}')>"


class FrontendLocalization(Base):
    """前端本地化表"""

    __tablename__ = "frontend_localizations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 语言代码
    language = Column(String(10), nullable=False, index=True)  # en-US, zh-CN

    # 翻译键值对
    translation_key = Column(String(200), nullable=False, index=True)
    translation_value = Column(Text, nullable=False)

    # 元数据
    context = Column(String(100), nullable=True)  # Optional context for translation
    created_by = Column(String(50), nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 唯一约束
    __table_args__ = (
        Index("idx_frontend_localizations_language", "language"),
        Index("idx_frontend_localizations_translation_key", "translation_key"),
    )

    def __repr__(self):
        return f"<FrontendLocalization(id={self.id}, language='{self.language}', key='{self.translation_key}')>"


# ==================== Monitoring Models ====================


class MonitoringAlertRule(Base):
    """监控告警规则表"""

    __tablename__ = "monitoring_alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    rule_name = Column(String(200), nullable=False, index=True)

    # 规则配置
    pattern = Column(String(500), nullable=False)  # 匹配模式
    severity = Column(String(20), nullable=False, index=True)  # critical, warning, info
    status = Column(String(20), default="active", nullable=False, index=True)  # active, inactive

    # 触发统计
    triggered_count = Column(Integer, default=0, nullable=False)
    last_triggered = Column(DateTime(), nullable=True)

    # 通知配置
    notification_channels = Column(JSON, nullable=True)  # List of channels

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_alert_rules_rule_id", "rule_id"),
        Index("idx_monitoring_alert_rules_name", "rule_name"),
        Index("idx_monitoring_alert_rules_severity", "severity"),
        Index("idx_monitoring_alert_rules_status", "status"),
    )

    def __repr__(self):
        return f"<MonitoringAlertRule(id={self.id}, rule_id='{self.rule_id}', name='{self.rule_name}')>"


class MonitoringLogPattern(Base):
    """监控日志模式表"""

    __tablename__ = "monitoring_log_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_id = Column(String(100), unique=True, nullable=False, index=True)

    # 模式配置
    pattern = Column(String(500), nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # error, warning, info

    # 统计信息
    count = Column(Integer, default=0, nullable=False)
    frequency = Column(Float, default=0.0, nullable=False)  # 每分钟出现次数

    # 时间信息
    first_seen = Column(DateTime(), server_default=func.now(), nullable=False)
    last_seen = Column(DateTime(), server_default=func.now(), nullable=False)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_log_patterns_pattern_id", "pattern_id"),
        Index("idx_monitoring_log_patterns_severity", "severity"),
        Index("idx_monitoring_log_patterns_last_seen", "last_seen"),
    )

    def __repr__(self):
        return f"<MonitoringLogPattern(id={self.id}, pattern_id='{self.pattern_id}', severity='{self.severity}')>"


class MonitoringTrace(Base):
    """监控追踪表"""

    __tablename__ = "monitoring_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(100), unique=True, nullable=False, index=True)

    # 追踪信息
    service = Column(String(100), nullable=False, index=True)
    start_time = Column(DateTime(), nullable=False, index=True)
    duration_ms = Column(Integer, nullable=False)
    span_count = Column(Integer, nullable=False)
    root_span = Column(String(100), nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_traces_trace_id", "trace_id"),
        Index("idx_monitoring_traces_service", "service"),
        Index("idx_monitoring_traces_start_time", "start_time"),
    )

    def __repr__(self):
        return f"<MonitoringTrace(id={self.id}, trace_id='{self.trace_id}', service='{self.service}')>"


class MonitoringServiceCall(Base):
    """监控服务调用表"""

    __tablename__ = "monitoring_service_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 调用信息
    from_service = Column(String(100), nullable=False, index=True)
    to_service = Column(String(100), nullable=False, index=True)

    # 统计信息
    call_count = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Float, default=0.0, nullable=False)
    error_rate = Column(Float, default=0.0, nullable=False)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_service_calls_from", "from_service"),
        Index("idx_monitoring_service_calls_to", "to_service"),
    )

    def __repr__(self):
        return f"<MonitoringServiceCall(id={self.id}, from='{self.from_service}', to='{self.to_service}')>"


class MonitoringMetric(Base):
    """监控指标表"""

    __tablename__ = "monitoring_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 指标信息
    metric_name = Column(String(100), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # counter, gauge, histogram, summary
    value = Column(Float, nullable=False)

    # 标签
    labels = Column(JSON, nullable=True)

    # 时间戳
    timestamp = Column(DateTime(), server_default=func.now(), index=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_metrics_name", "metric_name"),
        Index("idx_monitoring_metrics_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<MonitoringMetric(id={self.id}, name='{self.metric_name}', value={self.value})>"


class MonitoringIntegration(Base):
    """监控集成配置表"""

    __tablename__ = "monitoring_integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    integration_id = Column(String(100), unique=True, nullable=False, index=True)
    integration_name = Column(String(200), nullable=False)

    # 集成类型
    integration_type = Column(String(50), nullable=False, index=True)  # prometheus, loki, tempo, elasticsearch, victoriametrics

    # 集成配置
    config = Column(JSON, nullable=False)  # URL, credentials, etc.

    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    health_status = Column(String(20), default="unknown", nullable=False)  # healthy, unhealthy, unknown
    last_health_check = Column(DateTime(), nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_integrations_id", "integration_id"),
        Index("idx_monitoring_integrations_type", "integration_type"),
        Index("idx_monitoring_integrations_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<MonitoringIntegration(id={self.id}, type='{self.integration_type}', name='{self.integration_name}')>"


class MonitoringDashboard(Base):
    """监控仪表板表"""

    __tablename__ = "monitoring_dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dashboard_id = Column(String(100), unique=True, nullable=False, index=True)
    dashboard_name = Column(String(200), nullable=False)

    # 仪表板配置
    panels = Column(JSON, nullable=False)  # Panel configurations
    refresh_interval = Column(String(20), default="30s", nullable=False)  # 30s, 1m, 5m
    time_range = Column(String(20), default="1h", nullable=False)  # 1h, 24h, 7d

    # 状态
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_dashboards_id", "dashboard_id"),
        Index("idx_monitoring_dashboards_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<MonitoringDashboard(id={self.id}, dashboard_id='{self.dashboard_id}', name='{self.dashboard_name}')>"


class MonitoringAnomaly(Base):
    """监控异常表"""

    __tablename__ = "monitoring_anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    anomaly_id = Column(String(100), unique=True, nullable=False, index=True)

    # 异常信息
    metric_name = Column(String(100), nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)

    # 状态
    is_anomaly = Column(Boolean, nullable=False, index=True)
    status = Column(String(20), default="active", nullable=False)  # active, resolved, ignored

    # 时间戳
    detected_at = Column(DateTime(), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_monitoring_anomalies_id", "anomaly_id"),
        Index("idx_monitoring_anomalies_metric", "metric_name"),
        Index("idx_monitoring_anomalies_service", "service_name"),
        Index("idx_monitoring_anomalies_detected_at", "detected_at"),
    )

    def __repr__(self):
        return f"<MonitoringAnomaly(id={self.id}, anomaly_id='{self.anomaly_id}', score={self.anomaly_score})>"


# ==================== Testing Framework Models (New) ====================


class TestingSuiteDB(Base):
    """测试套件表（Testing Framework专用）"""

    __tablename__ = "testing_suites"

    id = Column(String(100), primary_key=True)
    suite_id = Column(String(100), unique=True, nullable=False, index=True)
    suite_name = Column(String(200), nullable=False)
    test_type = Column(String(50), nullable=False, index=True)  # unit, integration, end_to_end, performance, security
    description = Column(Text, nullable=True)
    test_count = Column(Integer, default=0, nullable=False)
    coverage_target = Column(Float, default=80.0, nullable=False)
    status = Column(String(20), default="active", nullable=False, index=True)  # active, archived

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_suites_suite_id", "suite_id"),
        Index("idx_testing_suites_test_type", "test_type"),
        Index("idx_testing_suites_status", "status"),
    )

    def __repr__(self):
        return f"<TestingSuiteDB(id='{self.id}', suite_id='{self.suite_id}', name='{self.suite_name}')>"


class TestingCaseDB(Base):
    """测试用例表（Testing Framework专用）"""

    __tablename__ = "testing_cases"

    id = Column(String(100), primary_key=True)
    test_id = Column(String(100), unique=True, nullable=False, index=True)
    suite_id = Column(String(100), nullable=False, index=True)
    test_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    test_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, running, passed, failed, skipped
    duration = Column(Float, default=0.0, nullable=False)
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    executed_at = Column(DateTime(), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_cases_test_id", "test_id"),
        Index("idx_testing_cases_suite_id", "suite_id"),
        Index("idx_testing_cases_test_type", "test_type"),
        Index("idx_testing_cases_status", "status"),
    )

    def __repr__(self):
        return f"<TestingCaseDB(id='{self.id}', test_id='{self.test_id}', name='{self.test_name}')>"


class TestingReportDB(Base):
    """测试报告表（Testing Framework专用）"""

    __tablename__ = "testing_reports"

    id = Column(String(100), primary_key=True)
    report_id = Column(String(100), unique=True, nullable=False, index=True)
    suite_id = Column(String(100), nullable=False, index=True)
    test_type = Column(String(50), nullable=False, index=True)
    start_time = Column(DateTime(), nullable=False, index=True)
    end_time = Column(DateTime(), nullable=True)
    total_tests = Column(Integer, default=0, nullable=False)
    passed_tests = Column(Integer, default=0, nullable=False)
    failed_tests = Column(Integer, default=0, nullable=False)
    skipped_tests = Column(Integer, default=0, nullable=False)
    coverage = Column(Float, default=0.0, nullable=False)
    duration_sec = Column(Float, nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_reports_report_id", "report_id"),
        Index("idx_testing_reports_suite_id", "suite_id"),
        Index("idx_testing_reports_test_type", "test_type"),
        Index("idx_testing_reports_start_time", "start_time"),
    )

    def __repr__(self):
        return f"<TestingReportDB(id='{self.id}', report_id='{self.report_id}', suite_id='{self.suite_id}')>"


class TestingCoverageDB(Base):
    """测试覆盖率表（Testing Framework专用）"""

    __tablename__ = "testing_coverages"

    id = Column(String(100), primary_key=True)
    module_id = Column(String(100), unique=True, nullable=False, index=True)
    module_name = Column(String(200), nullable=False)
    module_type = Column(String(50), nullable=False, index=True)  # core, integration, ai, api
    total_lines = Column(Integer, nullable=False)
    covered_lines = Column(Integer, nullable=False)
    coverage_percentage = Column(Float, nullable=False)
    coverage_level = Column(String(50), nullable=False, index=True)  # excellent, good, acceptable, needs_improvement

    # 时间戳
    last_updated = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(), server_default=func.now())

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_coverages_module_id", "module_id"),
        Index("idx_testing_coverages_module_type", "module_type"),
        Index("idx_testing_coverages_coverage_level", "coverage_level"),
    )

    def __repr__(self):
        return f"<TestingCoverageDB(id='{self.id}', module_id='{self.module_id}', coverage={self.coverage_percentage}%)>"


class TestingCoverageThresholdDB(Base):
    """覆盖率阈值配置表（Testing Framework专用）"""

    __tablename__ = "testing_coverage_thresholds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_type = Column(String(50), unique=True, nullable=False, index=True)
    minimum_coverage = Column(Float, nullable=False)
    target_coverage = Column(Float, nullable=False)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_coverage_thresholds_module_type", "module_type"),
    )

    def __repr__(self):
        return f"<TestingCoverageThresholdDB(id={self.id}, module_type='{self.module_type}', min={self.minimum_coverage}%)"


class TestingAutomationJobDB(Base):
    """自动化任务表（Testing Framework专用）"""

    __tablename__ = "testing_automation_jobs"

    id = Column(String(100), primary_key=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    job_name = Column(String(200), nullable=False)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="idle", nullable=False, index=True)  # idle, running, completed, failed, cancelled
    trigger_type = Column(String(50), default="manual", nullable=False)  # manual, scheduled, webhook
    start_time = Column(DateTime(), nullable=True, index=True)
    end_time = Column(DateTime(), nullable=True)
    duration_sec = Column(Float, nullable=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_automation_jobs_job_id", "job_id"),
        Index("idx_testing_automation_jobs_job_type", "job_type"),
        Index("idx_testing_automation_jobs_status", "status"),
        Index("idx_testing_automation_jobs_start_time", "start_time"),
    )

    def __repr__(self):
        return f"<TestingAutomationJobDB(id='{self.id}', job_id='{self.job_id}', status='{self.status}')>"


class TestingCICDPipelineConfigDB(Base):
    """CI/CD流水线配置表（Testing Framework专用）"""

    __tablename__ = "testing_cicd_pipeline_configs"

    id = Column(String(100), primary_key=True)
    config_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False, index=True)  # github_actions, gitlab_ci, jenkins
    config_content = Column(Text, nullable=False)  # YAML/JSON配置内容
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_cicd_pipeline_configs_config_id", "config_id"),
        Index("idx_testing_cicd_pipeline_configs_platform", "platform"),
        Index("idx_testing_cicd_pipeline_configs_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<TestingCICDPipelineConfigDB(id='{self.id}', config_id='{self.config_id}', platform='{self.platform}')>"


class TestingNotificationConfigDB(Base):
    """测试通知配置表（Testing Framework专用）"""

    __tablename__ = "testing_notification_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(String(200), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    on_success = Column(Boolean, default=True, nullable=False)
    on_failure = Column(Boolean, default=True, nullable=False)
    channels = Column(JSON, nullable=False)  # List of channels: email, slack, webhook

    # 时间戳
    created_at = Column(DateTime(), server_default=func.now())
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), nullable=True)

    # 元数据
    meta_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_testing_notification_configs_name", "config_name"),
    )

    def __repr__(self):
        return f"<TestingNotificationConfigDB(id={self.id}, name='{self.config_name}', enabled={self.enabled})>"


# ==================== Plugin System Models ====================


class PluginStatus(str, Enum):
    """插件状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"


class Plugin(Base):
    """插件主表"""

    __tablename__ = "plugins"

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    
    # 插件类型
    plugin_type = Column(String(50), nullable=False, index=True)  # collector, analyzer, executor, storage, notifier
    
    # 插件状态
    status = Column(String(20), default=PluginStatus.INACTIVE.value, nullable=False, index=True)
    
    # 插件配置
    config_schema = Column(JSON, nullable=True)  # 配置模式定义
    default_config = Column(JSON, nullable=True)  # 默认配置
    
    # 依赖关系
    dependencies = Column(JSON, nullable=True)  # 依赖的其他插件
    
    # 插件文件信息
    file_path = Column(String(500), nullable=True)
    entry_point = Column(String(200), nullable=True)  # 入口函数
    
    # 元数据
    plugin_metadata = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    installed_at = Column(DateTime(), nullable=True)
    last_loaded_at = Column(DateTime(), nullable=True)
    
    # 创建者
    created_by = Column(String(50), nullable=True)
    
    # 索引
    __table_args__ = (
        Index("idx_plugins_name", "name"),
        Index("idx_plugins_type", "plugin_type"),
        Index("idx_plugins_status", "status"),
        Index("idx_plugins_version", "version"),
    )
    
    def __repr__(self):
        return f"<Plugin(id='{self.id}', name='{self.name}', version='{self.version}', status='{self.status}')>"


class PluginExecution(Base):
    """插件执行记录表"""

    __tablename__ = "plugin_executions"

    id = Column(String(100), primary_key=True)
    plugin_id = Column(String(100), nullable=False, index=True)
    plugin_name = Column(String(200), nullable=False, index=True)
    
    # 执行信息
    execution_type = Column(String(50), nullable=False)  # collect, execute, analyze
    trigger_type = Column(String(50), nullable=False)  # manual, scheduled, event
    
    # 执行参数
    input_data = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    
    # 执行结果
    output_data = Column(JSON, nullable=True)
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # 性能指标
    duration_ms = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    
    # 时间戳
    started_at = Column(DateTime(), nullable=False, index=True)
    completed_at = Column(DateTime(), nullable=True)
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    
    # 执行者
    executed_by = Column(String(50), nullable=True)  # 用户名或system
    
    # 元数据
    execution_metadata = Column(JSON, nullable=True)
    
    # 索引
    __table_args__ = (
        Index("idx_plugin_executions_plugin_id", "plugin_id"),
        Index("idx_plugin_executions_plugin_name", "plugin_name"),
        Index("idx_plugin_executions_success", "success"),
        Index("idx_plugin_executions_started_at", "started_at"),
        Index("idx_plugin_executions_execution_type", "execution_type"),
    )
    
    def __repr__(self):
        return f"<PluginExecution(id='{self.id}', plugin_name='{self.plugin_name}', success={self.success})>"


class PluginConfig(Base):
    """插件配置表"""

    __tablename__ = "plugin_configs"

    id = Column(String(100), primary_key=True)
    plugin_id = Column(String(100), nullable=False, unique=True, index=True)
    plugin_name = Column(String(200), nullable=False, index=True)
    
    # 配置内容
    config_data = Column(JSON, nullable=False)
    config_version = Column(Integer, default=1, nullable=False)
    
    # 配置状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # 配置描述
    description = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 更新者
    updated_by = Column(String(50), nullable=True)
    
    # 元数据
    config_metadata = Column(JSON, nullable=True)
    
    # 索引
    __table_args__ = (
        Index("idx_plugin_configs_plugin_id", "plugin_id"),
        Index("idx_plugin_configs_plugin_name", "plugin_name"),
        Index("idx_plugin_configs_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<PluginConfig(id='{self.id}', plugin_name='{self.plugin_name}', active={self.is_active})>"
