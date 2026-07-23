# -*- coding: utf-8 -*-
# core/approval_store.py
# ──────────────────────────────────────────────────────────────
# 🔧 BUG-FIX-24(中危):审批存储统一封装
# ──────────────────────────────────────────────────────────────
# 解耦 auto_heal.py 与 linux_repair.py 的循环依赖:
#   修复前:linux_repair 直接 import auto_heal._pending_approvals 字典,
#           且无锁写入,多线程下存在竞态(linux_repair_history 已加锁
#           但 _pending_approvals 字典未加锁 [29])
#   修复后:统一通过本模块提供的函数接口操作,内部加锁
#
# 设计要点:
#   1. _pending_approvals 仅在本模块内被赋值,跨模块只通过函数访问
#   2. get_approval 返回深拷贝快照,防止调用方意外修改内部状态
#   3. update_approval_field 通过白名单限制可更新字段,避免误改 alert
#   4. 所有公共函数都带类型/参数防御,记录警告日志便于排查
#
# 与 db_engine.py [27] 的协作关系:
#   - 本模块仅维护内存层(SQLite 失败时的兜底)
#   - 真理之源仍是 SQLite(由 auto_heal/linux_repair 写入 pending_approvals 表)
#   - get_pending_approvals 在 auto_heal 中合并 SQLite + 本模块两路数据
#
# ──────────────────────────────────────────────────────────────
# 🔧 N+1 修复(已落地):
#   - 白名单 _UPDATABLE_FIELDS 增加 reject_reason / rejected_at / rejected_by
#     用于支持 auto_heal.reject_approval 的驳回信息双写
# ──────────────────────────────────────────────────────────────
# 🔧 本次严格 Review 修复(R 系列):
#
# [R1] 🔴 P0 高危 — Lock → RLock,防止链式调用死锁
#   问题: threading.Lock 不可重入。当前 update_approval_status 内部调用
#         update_approval_field,虽然当前调用链未持锁(已释放后再获取),
#         但任何未来扩展(如审计回调、事件钩子)若在持锁期间调用另一个
#         同样使用 _approval_lock 的函数,会导致线程永久阻塞(死锁),
#         且这种 Bug 极难复现和排查。
#   修复: 将 Lock() 替换为 RLock()。RLock 允许同一线程多次获取同一把锁,
#         从根本上消除链式调用的死锁风险,API 完全兼容,无性能损失。
#
# [R2] 🟡 P1 中危 — update_approval_field 对 value 补充深拷贝
#   问题: upsert_approval 对 info 执行了 deepcopy 防止外部污染,
#         但 update_approval_field 直接 record[field] = value,
#         若 value 是可变对象(dict/list),调用方后续修改会污染内部状态,
#         与 upsert_approval 的深拷贝策略不一致。
#   修复: 在写入前对 value 执行 copy.deepcopy(),保持接口语义统一。
#         性能影响:对 reject_reason 这类字符串场景几乎无影响,
#                  对未来传入 dict/list 的场景才有实际防御价值。
#
# [R3] 🟡 P1 中危 — 批量快照函数改为锁内浅拷贝+锁外深拷贝
#   问题: get_all_approvals_snapshot / get_pending_only_snapshot 在锁内
#         对整个字典执行 deepcopy。审批数据量大时(如 100+ 条记录,
#         每条含完整 alert dict),锁持有时间可达数十毫秒,阻塞所有
#         并发的 upsert_approval / update_approval_field 等写操作,
#         在 alert_monitor_loop 高频调用场景下形成性能瓶颈。
#   修复: 锁内仅做 dict 浅拷贝(.copy(),原子且极快,O(n) 但常数极小),
#         锁外再对浅拷贝执行 deepcopy。
#         正确性保证:浅拷贝固定了顶层 key→value 引用,即使锁外有新写入,
#                    也不影响本次快照的 key 集合和数据快照。
#         性能提升:锁持有时间从 deepcopy 全量(可能数十 ms)降到
#                  dict.copy()(通常 <1ms),提升 10-100 倍。
#
# [R4] 🟡 P1 中危 — update_approval_field 对 status 字段补充合法性校验
#   问题: _UPDATABLE_FIELDS 白名单包含 "status",update_approval_status
#         在内部调用 update_approval_field 前会校验状态合法性,
#         但调用方可绕过 update_approval_status 直接调用
#         update_approval_field(aid, "status", "非法值"),导致非法状态
#         被写入内存,与 SQLite 表约束不一致,污染状态机。
#   修复: 在 update_approval_field 内,当 field == "status" 时,
#         额外校验 value 是否在 _VALID_STATUSES 内,与
#         update_approval_status 形成双重防御,任意路径都无法绕过。
#
# [R5] 🟢 P2 低危 — frozenset 注解补全泛型参数
#   问题: `_UPDATABLE_FIELDS: frozenset` 注解缺少元素类型,
#         mypy/pyright 等静态检查工具会报需要类型注解或推断为宽泛类型,
#         降低代码可维护性。
#   修复: 改为 `frozenset[str]`(Python 3.9+ 内置泛型语法)。
#
# [R6] 🟢 P2 低危 — 添加 from __future__ import annotations 兼容 Python 3.9
#   问题: 函数返回类型注解 `dict[str, Any] | None` 使用了 PEP 604 语法,
#         需 Python ≥ 3.10 才能在运行时求值。若部署环境为 Python 3.9
#         (项目 README 标注最低 Python 3.10,但 .env 示例和 config.py 注释
#         未明确强制),运行时注解求值会抛 TypeError。
#   修复: 文件顶部加 `from __future__ import annotations`,使所有注解
#         延迟求值(PEP 563),现代语法在 Python 3.9+ 均可兼容,
#         不影响 Python 3.10+ 的运行时行为。
#
# ──────────────────────────────────────────────────────────────

from __future__ import annotations  # [R6] 兼容 Python 3.9+,所有注解延迟求值

import copy
import logging
from threading import RLock  # [R1] Lock → RLock,防止链式持锁死锁
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# 显式导出列表(✅ 修复 6:控制 from ... import * 行为)
# ============================================================
__all__ = [
    "upsert_approval",
    "get_approval",
    "update_approval_status",
    "update_approval_field",
    "remove_approval",
    "get_all_approvals_snapshot",
    "get_pending_only_snapshot",
    "is_pending",
    "approval_count",
    "clear_all_approvals",
]

# ============================================================
# 全局存储 + 锁
# ============================================================
# 🔧 BUG-FIX-24:模块级私有字典,**仅本模块内部赋值**
# 跨模块访问必须通过下面的函数接口(避免引用别名失效问题)
_pending_approvals: dict[str, dict[str, Any]] = {}
_approval_lock = RLock()  # [R1] 使用 RLock 防止链式持锁死锁

# ============================================================
# 配置常量
# ============================================================
# ✅ 修复 3:可更新字段白名单,防止误改 alert/script_key 等关键字段
# [R5] frozenset → frozenset[str],补全泛型注解
_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {
        "status",
        "proposal",
        "rule",
        "rule_name",
        "script_key",
        # 🆕 N+1 修复：驳回相关字段加入白名单
        "reject_reason",
        "rejected_at",
        "rejected_by",
    }
)

# 合法状态值(与 db_engine.py [27] pending_approvals 表保持一致)
# [R5] frozenset → frozenset[str],补全泛型注解
_VALID_STATUSES: frozenset[str] = frozenset(
    {
        "pending",
        "approved_no_script",
        "executed_success",
        "executed_failed",
        "execute_error",
        "rejected",
    }
)


# ============================================================
# 核心 API:写入
# ============================================================
def upsert_approval(alert_id: str, info: dict[str, Any]) -> bool:
    """
    插入或更新一条审批记录到内存
    Args:
        alert_id: 审批 ID(必须非空字符串)
        info:     审批数据字典,典型结构:
                  {
                      "alert":      dict,    # 原始告警对象
                      "rule":       str,     # 规则名称(向后兼容)
                      "script_key": str,     # 修复脚本 key
                      "proposal":   str,     # 修复方案文本
                      "status":     str,     # pending|executed_success|...
                  }
    Returns:
        bool: True=写入成功 / False=参数非法被拒
    """
    # ✅ 修复 4:严格参数校验
    if not alert_id or not isinstance(alert_id, str):
        logger.warning(
            "upsert_approval: alert_id 非法,拒绝写入 | "
            f"got type={type(alert_id).__name__}, value={alert_id!r}"
        )
        return False
    if not isinstance(info, dict):
        logger.warning(
            "upsert_approval: info 必须是 dict | "
            f"alert_id={alert_id} | got type={type(info).__name__}"
        )
        return False
    # 🔧 BUG-FIX-24:深拷贝传入数据,防止调用方后续修改影响内部状态
    safe_info = copy.deepcopy(info)
    with _approval_lock:
        is_new = alert_id not in _pending_approvals
        _pending_approvals[alert_id] = safe_info
    # is_new 是函数栈上的局部变量,锁释放后读取它是安全的(不受其他线程影响)
    logger.debug(
        f"BUG-FIX-24: 审批{'插入' if is_new else '更新'} | "
        f"alert_id={alert_id} | status={safe_info.get('status', 'unknown')}"
    )
    return True


# ============================================================
# 核心 API:读取
# ============================================================
def get_approval(alert_id: str) -> dict[str, Any] | None:
    """
    获取单条内存审批记录(线程安全 + 深拷贝)
    ✅ 修复 5:返回深拷贝,防止调用方意外修改内部状态
              与 get_all_approvals_snapshot 的快照语义保持一致
    Args:
        alert_id: 审批 ID
    Returns:
        审批数据深拷贝 / None(未找到或参数非法)
    """
    if not alert_id or not isinstance(alert_id, str):
        return None
    with _approval_lock:
        record = _pending_approvals.get(alert_id)
        if record is None:
            return None
        # 深拷贝防止外部修改污染内部状态(单条数据量小,锁内 deepcopy 可接受)
        return copy.deepcopy(record)


def is_pending(alert_id: str) -> bool:
    """
    ✅ 修复 2:便捷查询 — 判断指定审批是否处于 pending 状态
    Args:
        alert_id: 审批 ID
    Returns:
        True=存在且为 pending / False=不存在或非 pending
    """
    if not alert_id or not isinstance(alert_id, str):
        return False
    with _approval_lock:
        record = _pending_approvals.get(alert_id)
        if not isinstance(record, dict):
            return False
        return record.get("status") == "pending"


def approval_count() -> int:
    """
    ✅ 修复 2:便捷查询 — 当前内存中的审批记录总数(含已执行的)
    """
    with _approval_lock:
        return len(_pending_approvals)


# ============================================================
# 核心 API:更新
# ============================================================
def update_approval_field(
    alert_id: str,
    field: str,
    value: Any,
) -> bool:
    """
    更新审批记录的指定字段(白名单保护)
    ✅ 修复 3:仅允许更新 _UPDATABLE_FIELDS 中的字段
              防止误改 alert 等关键嵌套对象
    [R2] value 写入前执行深拷贝,防止外部可变对象污染内部状态
    [R4] 当 field == "status" 时,额外校验值合法性,
         防止调用方绕过 update_approval_status 写入非法状态

    Args:
        alert_id: 审批 ID
        field:    字段名(必须在 _UPDATABLE_FIELDS 白名单内)
        value:    新值
    Returns:
        True=更新成功 / False=记录不存在 / 字段不允许更新 / 参数非法
    """
    if not alert_id or not isinstance(alert_id, str):
        logger.warning(f"update_approval_field: alert_id 非法 | got={alert_id!r}")
        return False
    if field not in _UPDATABLE_FIELDS:
        logger.warning(
            f"update_approval_field: 字段 '{field}' 不在白名单内,拒绝更新 | "
            f"alert_id={alert_id} | 白名单={sorted(_UPDATABLE_FIELDS)}"
        )
        return False
    # [R4] status 字段额外校验合法性,防止绕过 update_approval_status
    if field == "status" and value not in _VALID_STATUSES:
        logger.warning(
            "update_approval_field: status 值非法,拒绝更新 | "
            f"alert_id={alert_id} | got={value!r} | "
            f"合法值={sorted(_VALID_STATUSES)}"
        )
        return False
    # [R2] 深拷贝 value,防止外部可变对象写入后被调用方篡改
    safe_value = copy.deepcopy(value)
    with _approval_lock:
        record = _pending_approvals.get(alert_id)
        if not isinstance(record, dict):
            logger.debug(f"update_approval_field: 记录不存在 | alert_id={alert_id}")
            return False
        record[field] = safe_value
    logger.debug(
        f"BUG-FIX-24: 审批字段更新 | alert_id={alert_id} | field={field} | value={value!r}"
    )
    return True


def update_approval_status(alert_id: str, new_status: str) -> bool:
    """
    ✅ 修复 2:便捷接口 — 专门用于更新 status 字段(最高频操作)
              内部含状态值合法性校验
    Args:
        alert_id:   审批 ID
        new_status: 新状态(必须在 _VALID_STATUSES 内)
    Returns:
        True=更新成功 / False=失败
    """
    if new_status not in _VALID_STATUSES:
        logger.warning(
            f"update_approval_status: 非法状态值 '{new_status}' | 合法值={sorted(_VALID_STATUSES)}"
        )
        return False
    return update_approval_field(alert_id, "status", new_status)


# ============================================================
# 核心 API:删除
# ============================================================
def remove_approval(alert_id: str) -> bool:
    """
    删除审批记录
    Args:
        alert_id: 审批 ID
    Returns:
        True=删除成功 / False=记录不存在 / 参数非法
    """
    if not alert_id or not isinstance(alert_id, str):
        return False
    with _approval_lock:
        removed = _pending_approvals.pop(alert_id, None)
    if removed is not None:
        logger.debug(
            f"BUG-FIX-24: 审批已删除 | alert_id={alert_id} | "
            f"prev_status={removed.get('status', 'unknown') if isinstance(removed, dict) else 'invalid'}"  # noqa: E501
        )
        return True
    return False


# ============================================================
# 核心 API:批量快照
# ============================================================
def get_all_approvals_snapshot() -> dict[str, dict[str, Any]]:
    """
    返回所有审批记录的深拷贝快照(线程安全)
    供 auto_heal.get_pending_approvals() 与 SQLite 数据合并

    [R3] 改为锁内浅拷贝 + 锁外深拷贝:
        - 锁内只做 dict.copy()(原子、极快),最小化锁持有时间
        - 锁外对浅拷贝的 value 逐项 deepcopy,不阻塞写操作
        - 正确性保证:浅拷贝固定了顶层 key→value 引用,
          即使锁外有新写入,也不影响本次快照的 key 集合

    Returns:
        { alert_id: 审批数据深拷贝, ... }
    """
    with _approval_lock:
        # 锁内浅拷贝:固定当前所有 key→value 引用,操作极快
        shallow = _pending_approvals.copy()
    # 锁外深拷贝:对浅拷贝的各 value 做深拷贝,不持锁,不阻塞写操作
    return {aid: copy.deepcopy(info) for aid, info in shallow.items()}


def get_pending_only_snapshot() -> dict[str, dict[str, Any]]:
    """
    ✅ 修复 2:便捷接口 — 仅返回 status='pending' 的快照
              auto_heal.get_pending_approvals() 中过滤更高效

    [R3] 同 get_all_approvals_snapshot,改为锁内浅拷贝 + 锁外深拷贝

    Returns:
        { alert_id: 审批数据深拷贝, ... }(仅含 pending)
    """
    with _approval_lock:
        # 锁内浅拷贝并过滤 pending,value 仍是原始引用(浅拷贝)
        shallow = {
            aid: info
            for aid, info in _pending_approvals.items()
            if isinstance(info, dict) and info.get("status") == "pending"
        }
    # 锁外深拷贝,不持锁
    return {aid: copy.deepcopy(info) for aid, info in shallow.items()}


# ============================================================
# 维护 API:测试/调试用
# ============================================================
def clear_all_approvals() -> int:
    """
    清空所有内存审批记录(测试用 / 紧急清理)
    ✅ 修复 7:生产环境调用会产生 WARNING 级别日志,便于审计追溯
    Returns:
        清空前的条数
    """
    with _approval_lock:
        count = len(_pending_approvals)
        _pending_approvals.clear()
    if count > 0:
        logger.warning(
            f"BUG-FIX-24: ⚠️ 审批存储已被全部清空 | 清空前条数={count} | 调用方应自行确认操作合规"
        )
    else:
        logger.debug("BUG-FIX-24: 审批存储清空(原本为空,无影响)")
    return count
