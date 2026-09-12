# AIOps-Agents 全量代码通读 · 审计台账

> 目的：对全项目源码逐文件通读（非抽样、非 grep 文件名猜测），产出可核对台账 + 客观缺陷证据链。
> 方法：`file_read` 全文读取；大文件分块；每批登记「文件 → 行数 → 关键发现」。
> 规模基线：2598 个 `.py`（≈797,672 行），另前端 `.tsx` 785 / `.ts` 88 / `.js` 83。

## 范围（已排除非源码）
排除：`autobackup/`(全项目带时间戳备份副本, 799 py)、`__pycache__/`、`.mypy_cache/`、`.pytest_cache/`、`.benchmarks/`、`build/`、`artifacts/`、`releases/`。

| 域 | .py | 行数 |
|---|---|---|
| core | 444 | 175542 |
| api | 165 | 113978 |
| extensions/addons | 926 | 101808 |
| tests | 658 | 337223 |
| modules | 59 | 24768 |
| scripts | 107 | 18639 |
| services | 95 | 10259 |
| examples | 59 | 1163 |
| main.py / config.py | 2 | 3252 |

## 批次计划
- B1 入口层：main.py, config.py, conftest.py, sitecustomize.py, start.py, 根 scripts — **进行中**
- B2 core/ 顶层模块（core/*.py）
- B3 core/ 子包（core/agent, core/ai, core/analysis, core/repositories, core/interface, core/hitl, ...）
- B4 api/（165）
- B5 services/（95）
- B6 modules/（59）
- B7 extensions/addons（926）
- B8 frontend（tsx/ts/js）
- B9 tests/（658）
- B10 scripts/ examples/ alembic/ infra

## 发现登记（证据链）

### B1 入口层
（见下方逐条）

### B1 入口层 —— 发现（证据）

**已核对：非缺陷**
- `main.py:810` 附近 `k8s_router` 有定义（`try: from api.k8s_router import router as k8s_router / except ImportError: None`），`if k8s_router:` 非 NameError。
- `.env` / `ai_api.env` **不存在且已 gitignore** → `config.py:17 load_dotenv("ai_api.env", override=True)` 当前为 no-op；`override=True` 属潜在风险（若文件存在会覆盖真实环境变量），非当前泄露。

**B1-1 [中] slowapi 限流器被禁用但残留接线**
- `main.py:951-952`：`# limiter = Limiter(key_func=get_remote_address)  # Temporarily disabled - .env encoding issue` → `limiter = None  # disabled until rate limiter is configured`
- `main.py:994`：`app.state.limiter = limiter`（None）
- 影响：任何依赖 `app.state.limiter` / `@limiter.limit` 的端点限流失效；实际限流仅靠 `rate_limit_middleware`（`main.py:1020`）与 `security_middleware`（`main.py:1036`）。仓库根目录还有 6 个一次性正则脚本曾用于批量删除 `@limiter.limit`（见 B1-3）。
- 定性：限流职责被弱化/分散，接线残留，需收敛为单一机制。

**B1-2 [低] Exception 处理器重复注册，其一为死代码**
- `main.py:1078`：`app.add_exception_handler(Exception, general_exception_handler)`
- `main.py:1081-1082`：`@app.exception_handler(Exception)` `async def global_exception_handler(...)`
- 影响：同一异常类型注册两次，装饰器版本（后注册）覆盖前者 → `general_exception_handler` 实际不生效，属死代码/误导。应二选一。

**B1-3 [低-中，P2#16] 仓库根残留一次性脚本（会在工作树里改写源码）**
- `fix_limiter.py`、`fix_all_limiters.py`、`remove_limiters.py`、`remove_all_limiters.py`、`remove_all_limiters_v2.py`、`remove_remaining_limiters.py`
- 证据：以上脚本用 `re.sub(r'@limiter\.limit\([^)]+\)...', ...)` 直接改写 `api/*.py` 源文件并写回（`open(..., 'w')`）。属遗留的一次性迁移工具，误执行会破坏源码。
- 另有根级零散：`analyze_bandit.py`、`verify_components_availability.py`、`test_dependency_upgrade.py`。

**B1-4 [低] 配置密钥缺失仅告警（dev）**
- `config.py`：`JWT_SECRET_KEY`、`INTERNAL_API_KEY`、`POSTGRES_PASSWORD` 在非 production 下仅 `logger.warning`；生产下才 `raise`。已知项。

**B1-5 [信息] main.py 存在大量空占位注释块且含注释掉的导入**
- `main.py:24` `# from core.compliance_manager import get_compliance_manager`（合规管理器未接入主入口，与 #19 相关）
- `main.py:7-8` `# from core.accessibility_support ...`、`# from core.ai_engine import _get_http_client ...`
- 多处 `# Phase N: ...` 空注释块（如 920-935 连续 16 行仅注释，无代码）；`modules.analyze.root_cause.gnn` 因 torch 报错被禁用（main.py:373 注释）。

### B2 core/ 顶层模块 —— 进行中（已读：auth 簇 + api/auth_router.py）

**B2-1 [高] 两套并行认证栈，`sub` 语义冲突**
- `api/auth_router.py:87` 登录签发：`create_access_token({"sub": user.username, "role": user.role})` → sub=**用户名**
- `core/auth_service.py:get_current_user`（:149）：`payload.get("sub")` → `db.query(User).filter(User.username == username)` ✔ 自洽
- `core/auth.py:verify_token`（:29）返回 `payload.get("sub")` 当作 **user_id**；`core/auth.py:get_current_user`（:57）：`db.query(User).filter(User.id == user_id)` ✘ 拿用户名去比主键
- 且：`core/auth.py` 用 `from jose import JWTError, jwt`（python-jose）；`core/auth_service.py` 用 `import jwt`（PyJWT）；User 模型分别为 `core/models.User` 与 `core/auth_db.User`；DB 分别为异步 Postgres（`core.db_engine`）与同步 SQLite。
- 影响：登录 token 调 `core.auth.get_current_user` 依赖的端点 → `id == "username"` → 404/错用户。

**B2-2 [高] 生产路由内嵌 unittest.mock 伪造用户**
- `api/auth_router.py:139-147` `me()`：`if current_user is None: from unittest.mock import Mock; user = Mock(); user.id=1; user.username="test_user"; user.role="viewer"; ...`
- 生产代码引入 `unittest.mock` 并伪造身份，属测试桩泄漏进产品路径。

**B2-3 [高] 默认管理员弱口令种子**
- `core/auth_db.py:init_db()`：无用户时创建 `username="admin", hash_password("admin123"), role="admin"`。硬编码弱口令，任何调用 `init_db()` 的环境都会生成已知口令管理员。

**B2-4 [高] 导入即 monkeypatch bcrypt/passlib 内部**
- `core/auth_service.py:21-27`：
  `_bcrypt_mod.__about__ = type("about", (), {"__version__": "5.0.0"})()`
  `_passlib_bcrypt._BcryptCommon._finalize_backend_mixin = classmethod(lambda cls, backend, dryrun: setattr(cls, "_workrounds_initialized", True) or True)`
- 伪造版本 5.0.0 并绕过 passlib 后端 finalize，与项目约束「bcrypt 固定 4.0.1 兼容 passlib 1.7.4」直接矛盾；passlib 内部属性名变更即崩。

**B2-5 [中] 内部密钥校验可被空头绕过（dev）**
- `core/auth_service.py:is_internal_key`：`request.headers.get("X-Internal-Key") == config.INTERNAL_API_KEY`；dev 下 `config.INTERNAL_API_KEY=""`（仅告警），发送空 `X-Internal-Key:` 头即 `"" == ""` → True。（调用点授权范围待确认）

**B2-6 [中] 认证存储=本地 SQLite，与主体异步 Postgres 双库**
- `core/auth_db.py`：`data/aiops.db`（`AIOPS_TEST_DB_PATH` 可覆盖），`SessionLocal` 同步。测试持久状态污染源（对应任务 #2）。

**B2-7 [中/低] 弃用时间 API**
- `datetime.utcnow()`：`core/auth_db.py`（多列 default）、`api/auth_router.py`（register_admin）；`core/token_blacklist.blacklist_token` 用 `datetime.utcfromtimestamp`。Python 3.12+ 已弃用。

**B2-8 [低] `core/crypto.py:decrypt_snapshot` `except (InvalidToken, Exception)` 冗余**（Exception 已覆盖 InvalidToken）。

### B2-3 core/ 安全簇（auth/rbac/abac/mfa/key/security_*）—— 已通读

**B2-9 [高] `core/rbac.py` 权限装饰器为装饰性空壳**
- `require_permission`(:199)、`require_role`(:219)、`require_any_role`(:236) 三个装饰器的 wrapper 内**硬编码 `user_role = Role.VIEWER  # 默认角色`**（注释自承"这里应该从请求上下文中获取用户角色…简化实现，实际应该从JWT token或session中获取"）。
- 影响：鉴权与请求无关，真实 admin 亦被当 VIEWER 处理；`require_permission` 对任何非 VIEWER 权限恒 403，`require_role` 除 VIEWER/ADMIN 外恒 403。鉴权完全失效（装饰性）。

**B2-10 [高] `core/fine_rbac.py` 依赖引用不存在的函数**
- `require_permission`(:82)：`from core.rbac import get_user_tenant`；但 `core/rbac.py` 全文件（通读，结束于 `role_required`）**未定义 `get_user_tenant`**。
- 影响：任何使用该依赖的端点运行时 `ImportError` → 500。且策略库为进程内 `_POLICY_STORE`（注释承认"in‑memory … production 应为 PostgreSQL 表"），`_load_demo_policies()` 导入即注入默认策略。

**B2-11 [高] `core/abac.py` SQLAlchemy 支持半成品**
- `_create_tables`/`_load_policies` 按 `self._is_sqlalchemy` 分支，但 `_log_evaluation`(:418)、`create_policy`(:460)、`update_policy`(:536)、`delete_policy`(:609) **一律走 `self.storage.get_connection()`**，未做 SQLAlchemy 分支。
- 影响：构造函数接受 SQLAlchemy session（`abac.py:116` `_is_sqlalchemy = hasattr(postgres_storage,'execute')`）时，写路径调用不存在的 `get_connection` → 异常，仅读路径可用。

**B2-12 [中] `core/security_middleware.py:PasswordPolicy.hash_password` 无 72 字节截断**
- `hash_password`(:60) 直接 `bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())`；`verify_password` 同样不截断。
- 与 `core/authentication.py:_CompatPwdContext`（截断 72）**不一致**；bcrypt 4.x 对 >72 字节口令抛 `ValueError`。两条口令路径行为分叉。

**B2-13 [高] `core/security_middleware.py:MFAManager.verify_totp` fail-open**
- `verify_totp`(:146)：`if not self._mfa_enabled: return True`；`except ImportError: logger.warning(...); return True`（pyotp 未装即放行）。
- 影响：MFA 未显式启用或依赖缺失时，任何 TOTP 校验均通过 → MFA 形同虚设（安全绕过）。

**B2-14 [中] `core/token_blacklist.py` 与 `core/authentication.py` 两套互不感知的吊销机制**
- `token_blacklist` 用 `core.auth_db` 的 SQLite `TokenBlacklist` 表；`authentication.revoke_token`/`is_token_revoked` 用 Redis 或进程内 `_token_blacklist` 字典。
- 影响：经 `authentication.revoke_token` 吊销的 token，`token_blacklist.is_blacklisted` 不可见，反之亦然；吊销语义分叉。
- 另：`blacklist_token` 用 `datetime.utcfromtimestamp`（3.12 弃用）。

**B2-15 [中] `core/unified_access_control.py:require_permission` 同名不同义 + 强依赖 request.state.user**
- `require_permission(resource,action)`(:233) **返回 `Depends(check_access_dependency)`**；与 `fine_rbac.require_permission`（返回可调用依赖）签名相同、语义不同 → 易误用。
- 依赖仅读 `getattr(request.state,"user",None)`，无中间件注入即恒 401；全局实例 `unified_access_control = UnifiedAccessControl()`（无 postgres_storage → 无 ABAC 引擎 → 落到默认 deny）。
- `add_access_control_middleware` 默认 `AIOPS_ENFORCE_ABAC=false`（环境变量门控）。

**B2-16 [高] `core/enhanced_auth_integration.py` 无盐 SHA-256 口令 + 授权装饰器空壳**
- `_verify_password`(:255)：`hashlib.sha256(f"{user.username}:{password}".encode()).hexdigest()`，注释自承 "simplified … For now, use simple hash comparison"。无盐、无 KDF。
- `require_permission`(:426)：async/sync wrapper 内注释 "For now, just call the function"，**不做任何校验** → 装饰即绕过。
- 默认密钥回落 `dev-secret-key-change-me`（仅非生产告警）；用户/令牌存进程内字典。

**B2-17 [高] `core/sso_auth.py:login_success` 反射型 XSS**
- `login_success`(:153)：`html = f"...localStorage.setItem('access_token', '{token}')..."`，`token` 来自查询参数**未转义/未校验** → `?token=';alert(1)//` 注入脚本。
- 回调 `auth_callback` 的 state 校验仅查全局内存 `_state_store`（注释承认"Production should use Redis"），未与浏览器会话绑定。
- SSO 用户查库失败时写入 `globals()["_fake_users_db"]`（假内存库），非真实持久化。

**B2-18 [中] `core/security_input_validator.py` 双重转义 + 黑名单式防注入**
- `sanitize_string`(:236) 在 `html.escape`（Step 7）之后又执行 `replace("\\","\\\\")`、`replace("'","\\'")`、`replace('"','\\"')`（Step 8），对正常文本二次破坏。
- 防注入依赖正则黑名单（XSS/SQL/命令），易被编码/变形绕过；中间件 `SecurityInputValidatorMiddleware` 是否挂载需在 main.py 侧确认（已在 B1 记 main.py 接线）。

**B2-19 [低] `core/key_management.py` / `core/key_management_service.py` 双密钥服务并存且默认弱**
- `key_management.KeyEncryptionService.__init__`：未配置时 `_generate_master_key()` 随机并仅 warning；`_ensure_key_length` 用补 '0'/截断到 32 → 输入主密钥被静默改写。
- `key_management_service.get_jwt_secret_key(required=False)` 返回 `""`；与 `core/authentication.py` 的 `get_key_service()` 并用，缺省空串语义需在消费端区分。

### B2-4 可观测/告警簇 —— 已通读

**B2-20 [低] `core/alert_service.py:get_alerts` 存在不可达死代码**
- 方法在 `return result` 之后仍有第二个 `return {"total": len(alerts_list), "alerts": latest_alerts}`（不可达）。
- 缓存失效判据为 `cached_result.get("total") == len(alert_history)`，仅数量一致即命中，内容变化不失效（脆弱）。

**B2-21 [中] `core/anomaly_detection.py` CLI 入口 `pd` 未定义**
- 模块级无 `import pandas as pd`（仅 `if TYPE_CHECKING` 与函数内局部导入）；`if __name__ == "__main__"` 块直接 `pd.DataFrame(raw)` → 运行 `python core/anomaly_detection.py <json>` 即 `NameError: pd`。

**B2-22 [高] `core/stats_engine.py` 为显式 stub + 缓存整体重置**
- 文件内注释自述："Async query/insert **stubs** – tests patch these so engine stays testable"。
- `query_hourly_stats`/`query_daily_stats`/`query_system_stats` 仅读 `_summary_cache`，而生产代码无对应写入者 → 恒返回空/兜底值。
- `get_real_summary` 中 `global _summary_cache; _summary_cache = {"data": summary, "timestamp": now}` **整体替换字典**，抹掉此前累计的 `ingestion`/`alert_noise`/`repair_history`/`hourly_stats` 等键 → 统计自失忆。

### B2-5 KPI/SLO/SLA 簇 —— 已通读

**B2-23 [中，任务#5/#10 根因] KPI/SLA/SLO 状态写入 git 跟踪的 `data/*.json`**
- `core/kpi_config.py` → `data/kpi_config.json`；`core/sla_report_storage.py` → `data/sla_reports.json`；`core/slo_storage.py` → `data/slos.json`。
- 均为运行期可写、且位于受版本控制的 `data/` 下 → 测试/运行会污染工作树（本次审计中 `data/sla_reports.json` 即被改动）。

**B2-24 [低] `core/kpi_config.py` 默认项 id 非确定性**
- `_default_configs()` 每项 `id=str(uuid.uuid4())`；文件缺失时重建内容随运行变化，易被测试/git 视为 diff。
- `_write_configs` 内重复 `import os`（模块顶部已导入）。

**已核对非缺陷**
- `core/slo_engine._slo_counter` 撞号疑点排除：`slo_storage.save_slos`/`load_slos` 均持久化/恢复 `counter`，新建 id 不会与已载入项冲突。
- `core/slo_metrics_client.VictoriaMetricsClient` 默认 `verify=True`，仅环境变量显式关闭并告警；`_escape_label` 正确转义 PromQL 标签。
- `core/slo_incident_store.compute_downtime` 合并重叠区间，避免重复计时，逻辑正确。
- `core/metrics_history.MetricsHistory` 线程安全（Lock）、环形容量、时间戳归一化与动态阈值三层兜底，实现完整。

### B2-6/7 告警引擎 + 数据/配置基础设施 —— 已通读（部分）

**B2-25 [中] `core/feature_flag.py:delete_flag` 删除不落盘**
- `delete_flag` 仅 `del self._flags[key]`，**未调用 `_save_flag_to_storage`**（create/update/add_rule/remove_rule 都会落盘）→ 删除不入存储，进程重启后该标志复活。

**B2-26 [中] `core/feature_flag.py:_evaluate_percentage` 量纲错误**
- `percentage = flag.fallback_value ...; hash_percentage(<1) < percentage`；若 `fallback_value` 采用 0–100 百分比单位（如 50），则条件恒真 → 放量恒 100%。缺 `/100` 归一。

**B2-27 [低] `core/config_center.py:set_config` 变更事件 old_value 失真**
- fallback 分支先改写 `fallback_config[key].value` 再构造 `ConfigChangeEvent(old_value=... self.fallback_config[key].value)` → UPDATE 事件的 `old_value` 等于**新值**。

**B2-28 [低] `datetime.utcnow()` 弃用面**
- `core/persistent_store._persist/_persist_all`（`row.updated_at = datetime.utcnow()`）；连同 B2-7 清单，弃用时间 API 在多模块出现。

**已核对：`core/alert_engine.py`（1512 行）加固良好** —— SSH 暴破滑动窗口（负增量/logrotate 防御、冷却、过期清理、硬上限）、去重聚合（滑动窗口、容量淘汰、prev_suppressed）、动态阈值（DYNAMIC_THRESHOLD_CONFIG 门控）、SQLite 持久化失败降级到内存、通知/自愈/WebSocket 触发链路完整。

**已核对：`core/persistent_store.py`** —— `_TrackedDict`/`_TrackedList` 跟踪容器使原地变更落盘、`(domain,kind,tenant_id)` 隔离、`PersistentList` 整体序列化，设计与实现完整（仅时间 API 弃用）。

### B2-8 数据库主干 —— 已通读（db_engine 长文件主段）

**B2-29 [高，架构] 全项目并存三套数据库引擎/会话**
- `core/database.py`：同步 SQLite（`data/aiops.db`，`create_engine(sqlite:///…, pool_size=20)`，`Base` + `get_db`）。
- `core/auth_db.py`：另建同步 SQLite 引擎（同 `data/aiops.db`）+ `SessionLocal`（RBAC/资产/TokenBlacklist）。
- `core/db_engine.py`：异步 PostgreSQL/asyncpg 引擎（`_ensure_engine`、`async_get_session`、`async_*` ORM 操作）。
- 影响：`Base` 来自 `core/database`，但三处各自 `create_engine`；认证/资产落 SQLite、业务告警/修复落 Postgres → 数据割裂、事务边界不统一、测试易污染（对应任务 #2）。

**已核对：`core/db_engine.py`（1049 行）** —— 懒加载引擎/会话代理、`async_get_session` 自动 commit/rollback、告警/修复/审批全套 `async_*` ORM 读写、连接失败降级（`_is_db_connection_error`）逻辑真实完整，非 no-op。

### B2-9 自愈/修复簇 —— 已通读（auto_heal / collector / command_guard / heal_graph / linux_repair）

**B2-30 [高] 全项目 SSH 连接禁用主机密钥校验（`known_hosts=None`）→ MITM 风险**
- `core/linux_repair.py:_run_ssh_command`：`asyncssh.connect(host, username=..., password=..., known_hosts=None)`；无密码分支同样 `known_hosts=None`。
- 影响：不对远端主机公钥做校验，任何中间人可冒充被修复主机并接收修复口令/命令 → 自愈通道可被劫持。（同模式需在 k8s/其他修复模块核对）

**B2-31 [中] `linux_repair._find_host_config` 未命中即回退为“把 host_name 当主机直连”**
- `_find_host_config(host_name)`：配置里找不到时 `return {"name": host_name, "host": host_name}`。
- 影响：`execute_linux_repair(host_name=任意值)` 会对**任意字符串**发起 SSH（配置外主机），构成 SSRF/横向探测面。应改为“未配置即拒绝”。

**B2-32 [中] `heal_graph` 工作流节点语义含“或 simulate”表述，apply_fix 执行真实性待核**
- 模块 docstring 第 5 步写明 `apply_fix – Execute the run-book (or simulate)`；`HealState.fix_applied` 默认 False。
- 需在 `apply_fix` 节点尾部确认：是真实执行 `state.executed_commands` 还是仅置位（本批读到 invoke_agent 段被截断，apply_fix 待续读核验）。

**B2-33 [中] `auto_heal._is_pending_approval_error` 以“缺 approval_status”判为待审批而非失败**
- 判据 `final_state.approval_status in (None, "pending", "missing")` → 只要 `approval_status` 为 None 即视为“非真失败”。
- 影响：任何未显式设置审批状态的失败运行，会被归类为非失败，可能掩盖真实自愈失败、影响失败计数/升级阈值。

**B2-34 [低] `auto_heal` 的失败跟踪/锁为进程内内存，命名宣称“distributed”**
- `_HEAL_FAILURE_TRACKER`、`_HEAL_LOCKS` 均为模块级 dict；`_acquire_heal_lock` docstring 称 “per-process distributed lock”。
- 影响：多 worker/多实例部署下失败计数与去重锁不共享，升级阈值失效；命名误导。

**B2-35 [信息] `RepairScriptLibrary` 的 `script_content` 为“展示用源码字符串”**
- `_get_*_repair_script()` 返回 Python 源码文本，作为元数据随脚本登记；`CrossPlatformScriptExecutor.execute_script` 是否真正执行该内容需核（本批尾部被截断）。

**已核对：`collector.py`（Windows 指标采集，1071 行）实现扎实**
- N3-1 引擎层 TTL 缓存、N3-2 CPU+进程双采样窗口合并、N3-3 并行 IO、N3-4 三锁分离（防嵌套）、N3-6 分段超时、CR1 锁外记录指标、CR2 超时/异常区分、C12 时间倒退防御，逻辑完整；用 `datetime.datetime.now()` 非弃用 API。

**已核对：`command_guard.py`（1139 行）防线扎实**
- CG1 shlex 智能拆分（含引号边界）+ re.split 降级；CG2/CG11 运行时受保护 PID 自检；黑/白名单覆盖 Linux+Windows+K8s+RCE/数据外带；CG7 审计 deque LRU。未发现安全绕过。

### B2-10 修复载荷簇 —— 已通读（k8s_repair / docker_repair / cloud_repair / macos_repair / windows_repair + 核验 command_guard/heal_graph）

**B2-36 [高，真·空壳] `core/windows_repair.py` 两个函数体为空**
- `execute_windows_repair(script_key, params)` → `return {}`（无任何执行逻辑，忽略入参）。
- `get_windows_repair_history(limit)` → `return []`。
- 定性：名副其实的 stub/占位（非“有 fallback 的桩”）。`WINDOWS_REPAIR_SCRIPTS` 注册了 3 个脚本但**无执行器**。

**B2-37 [高] `core/k8s_repair.py` 审计调用位置参数错位（字段串位）**
- `record_audit` 真实签名（`core/command_guard.py`）：`record_audit(host, command, risk_level, executor="agent", result="success", ...)`。
- k8s_repair 三处均按 `record_audit(host, script_key, full_cmd, "blocked"/"success", reason)` 调用 →
  实际落库为 `command=script_key`、`risk_level=<完整命令串>`、`executor="blocked"/"success"/"failed"`、`result=reason/error`。
- 影响：审计日志“风险级别”列存的是命令全文，“执行者”列存的是结果状态，**审计字段全部错位**（对比 `linux_repair` 用关键字传参正确）。

**B2-38 [高] `core/k8s_repair.py` 在**本地**执行 kubectl，与 `host_cfg` 目标主机无关**
- `execute_repair(host_cfg, ...)`：`host = host_cfg.get("host")` 仅作标签；执行用 `subprocess_runner.run(["bash","-c",full_cmd])`、`_inspect_pod_state` 用本机 `shutil.which("kubectl")`。
- `repair_all_k8s` 对 `K8S_HOSTS` 逐台调用 → 每台都在**本机**重复执行同一条 kubectl。
- 影响：多主机 K8s 修复实为“本机跑 N 次”，远端集群未被修复；`host` 字段误导。

**B2-39 [中] `core/k8s_repair.py:REPAIR_SCRIPTS` 声称“只读、防篡改”，实为可变 dict**
- `REPAIR_SCRIPTS = json.loads(json.dumps(_REPAIR_SCRIPTS_RAW))` → 深拷贝但**可变**，注释“只读映射，防止外部篡改”与事实不符（对比 `linux_repair` 用 `MappingProxyType`）。

**B2-40 [中] `core/docker_repair.py` 默认不执行（dry-run），且 docker 缺失时假成功**
- `dry_run = params.get("force") not in ("true","1","yes")` → 默认 `dry_run=True`，仅返回“Dry-run would execute ...”，**不触碰 docker**。
- `docker_available=False` 时 `result["success"]=True`、output="docker CLI not available; command simulated" → 把“未执行”记为**成功**。
- 历史落盘 `BASE_DIR/data/docker_repair_history.json`（受版本控制的 `data/` 下）→ 又一处测试/运行污染源（同 #5 类）。

**B2-41 [中] `core/cloud_repair.py` 阿里云分支恒抛未实现**
- `_alibaba_repair` 直接 `raise RuntimeError("Alibaba Cloud repair SDK not installed; only metrics collection is supported")`；`execute_cloud_repair(provider="alibaba")` 恒失败。AWS(boto3)/Azure(azure-mgmt) 为真实 SDK 调用。

**B2-42 [信息/安全] `core/macos_repair.py` 仅支持本机，remote 直接拒绝；脚本名回退为 PATH 命令**
- `if host not in ("localhost","127.0.0.1","::1"): raise` → 远端不支持。
- `script_path` 找不到文件时 `= script_name` → 以 `create_subprocess_shell(shlex.quote(...))` 执行 PATH 命令（quote 已防注入，风险低）。

**B2-32 复核（heal_graph.apply_fix）：默认“模拟”，真实执行需环境变量**
- `apply_fix` 中：仅当 `os.getenv("HEAL_EXECUTE_ENABLED","false")=="true"` 才 `create_subprocess_*` 真实执行；否则 `results.append({"command": cmd, "simulated": True})`。硬件命令另受 `HARDWARE_EXECUTE_ENABLED`（默认 false）门控 → 默认 `simulated=True`。
- 另：`evaluate` 中 `if not isinstance(state.runbook, dict): state.verification={"passed": True, "confidence": 0.5}` → 非结构化 runbook 一律**判通过**（可能与实际不符）。
- 定性：工作流真实存在，但**默认空转（模拟）**；审批/快照/护栏链路完整。

**B2-33 复核（auto_heal.approval 语义）**：`HealState.approval_status` 缺省 None → `_is_pending_approval_error` 判为“非真失败”，沿用前述结论。

### B2-11 验证/快照/升级簇 —— 已通读（verifier / snapshot_store / escalation / phase3_metrics）

**B2-43 [中] `core/escalation.py:notify_rollback_failure` 的“多渠道通知”仅为日志**
- 函数体：仅当环境变量 `ROLLBACK_FAILURE_WEBHOOK` 非空时才真正 `httpx.post`；随后对 `_notification_channels()`（默认 `slack,teams,email`）**只做 `logger.warning("Notifying {channel} ...")`**，未向 Slack/Teams/邮件发送任何请求。
- 影响：回滚失败这一 critical 事件的“通知”在未配置 webhook 时是**空动作**（只写日志），运维可能收不到升级告警。属“宣称多渠道、实际单 webhook+日志”。

**已核对：`core/verifier.py`（1653 行, HITL 验证引擎）实现完整、加固到位**
- 策略矩阵 service_status/process_check/metric_threshold/disk_usage/network_check/k8s_status/custom_command；V/VFB 系列修复（护栏审查 V1、超时 V2、快照深拷贝 V3、AI_DYNAMIC 启发式 VFB2、PID 正则 \d{1,7} VFB8、仅放行 SAFE/警告 LOW VFB9 等）逻辑自洽。
- `custom_command`(LLM) 默认关闭（`VERIFY_CONFIG["llm_for_custom"]=False`）；`_CONFIDENCE_CUSTOM_COMMAND_MAX` 为预留死代码（已 noqa，非缺陷）。

**已核对：`core/snapshot_store.py`（532 行）为真实 DB 持久化 + 加密**
- 操作类型分类 → `build_pre_state` 采集 K8s/服务/进程状态 → `Snapshot` 表（`encrypt_snapshot` 加密 pre_state/rollback_plan）→ `update/get/cleanup_expired` 全套；资源名经 `_K8S_NAME_PATTERN`/`_SERVICE_NAME_PATTERN` 校验。实现真实完整。

**已核对：`core/phase3_metrics.py`（48 行）Prometheus 指标定义正常**（HEAL_TOTAL/SUCCESS/FAILED/PENDING_APPROVAL、VERIFY_PASSED/FAILED、LLM_COST_PER_INCIDENT）。

### B2-12 core/ 引擎簇 —— 已通读（ai_engine / notify_engine / root_cause_intelligence / integration_ecosystem / integration_manager / lifecycle_manager / performance_regression_detector，7 文件 ≈ 10,630 行）

**B2-44 [高] `core/integration_manager.py` 集成连通性测试为假成功（cloud/cicd）**
- `_test_cloud_integration`(:591) 与 `_test_cicd_integration`(:596)：函数体 `return {"success": True, "message": f"{name} integration test passed"}`，**未做任何真实连接/凭据测试**。
- 影响：`register_integration` 依据 `test_integration` 结果把 AWS/Azure/GCP/GitLab 等集成的 `status` 置为 `ACTIVE`——用的是"永远通过"的假测试，错误的凭据也会被标为 ACTIVE 且 `last_tested` 被更新。

**B2-45 [中] `core/integration_manager.py` Jenkins/Jira 调用为桩**
- `trigger_jenkins_job`(:约1140)：不发起任何 HTTP，直接 `return {"success": True, "message": f"Job {job_name} triggered successfully", ...}`。
- `create_jira_issue`(同段)：不发起任何 HTTP，`issue_key=f'AIO-{now}'` 本地拼造。
- 影响：声称"触发 Jenkins 构建 / 创建 Jira 工单"的能力实为本地回显，外部系统未收到请求。

**B2-46 [低] `core/integration_manager.py` 事件处理为日志桩；WebSocket 可用性判定恒真**
- `_handle_alert_event`/`_handle_deployment_event`/`_handle_incident_event`：函数体仅 `logger.info(...)`+ 注释 "Alert processing logic"。
- `WEBSOCKET_AVAILABLE`：`try: pass except ImportError:` → **永远 True**（死分支）。
- `webhook_secret` 默认值 `"default_secret_change_me"`（硬编码签名密钥）。

**B2-47 [高] `core/integration_ecosystem.py` 云/CI-CD/监控集成的"激活"为空操作**
- `_activate_monitoring_integration`(:约370) / `_activate_cloud_integration` / `_activate_cicd_integration`：函数体为 `if provider == "aws": # 配置AWS SDK \n pass` 形式，**全部 pass（仅注释）**。
- 仅 `_activate_notification_integration` 有真实 `register_webhook`。
- 影响：`register_integration` 校验通过后一律 `status = ACTIVE`（:约450），但监控/云/CI-CD 集成实际未建立任何连接或客户端。

**B2-48 [中] `core/integration_ecosystem.py` 触发 webhook 的 aiohttp 分支超时类型错误**
- `trigger_webhook`(:约560)：aiohttp 分支 `self.aiohttp_session.post(..., timeout=self.webhook_timeout)`；`webhook_timeout=30`（int）。
- 影响：aiohttp 要求 `ClientTimeout`，传 int 运行即抛 `TypeError` → HTTP 客户端分支（无 requests 时）触发 webhook 恒失败。

**B2-49 [中] `core/integration_ecosystem.py` async 内同步 HTTP 阻塞事件循环**
- `_send_slack_notification`(:约471)：async def 内直接 `self.http_session.post(webhook_url, json=payload, timeout=10)`（requests 同步调用），未走 `run_in_executor`。
- 对比 `_post_webhook_notification` 用 `loop.run_in_executor` 正确。影响：Slack 通知会阻塞事件循环（最长 10s）。

**B2-50 [低] `core/integration_ecosystem.py` 下载量为"模拟"值**
- `ConnectorMarketplace._get_download_count`(:约1660)：注释 "simulated"/"In production, this would come from a database"，返回 `hash(provider) % 10000 + 100` → 连接器"下载量"为哈希伪造值。
- `list_connectors` 用 `list(self.registry.integration_templates.values()).index(connector)` 反查 provider（按 dict 值相等性）→ O(n) 且脆弱。

**B2-51 [中] `core/performance_regression_detector.py` 告警三通道为桩（仅日志）**
- `_webhook_alert`/`_email_alert`/`_slack_alert`：函数体仅 `logger.info("Webhook alert would be sent to ...")` / "Email alert would be sent" / "Slack alert would be sent" → **未发送任何真实请求**。
- 仅 `_log_alert` 真实。`AlertConfig` 的 `notification_channels` 可配 webhook/email/slack，但配了也不生效。统计检测部分（t-test/Mann-Whitney/z-test/change-point）为真实 scipy 实现。

**B2-52 [中] `core/root_cause_intelligence.py` ML 组件为装饰性（实例化但从不训练/使用）**
- `_initialize_components`(:约200)：创建 `RandomForestClassifier`/`GradientBoostingRegressor`/`StandardScaler`。
- 全文件（1939 行通读）**无 `.fit(...)`/`.predict(...)` 调用**；`analyze_root_causes_enhanced` 全程走规则/拓扑/场景分支。`self.scaler` 从未使用。
- 影响：宣称"ML-based" 的根因能力实际未接入；`ML_AVAILABLE` 仅决定对象是否被创建。
- 另：`CAUSAL_AVAILABLE` 由 `try: pass except ImportError:` 设定 → 恒 True（死分支）；`_parse_timestamp` 对非 ISO 输入用 `logger.error` 记正常失败。

**B2-53 [低-中] `core/notify_engine.py` 模块级 `asyncio.Lock()` 未懒加载**
- `_http_client_lock = asyncio.Lock()`(:约318) 在**模块导入即实例化**。
- 对比 `core/ai_engine.py` 明确以 AE1/AE2 修复为懒加载（避免 Python 3.12+ 无事件循环时 DeprecationWarning/RuntimeError）。notify_engine 未同步该修复 → 2.12+ 导入告警；且 `_get_http_client` 实际并未使用该锁（竞态注释与实现不符）。

**B2-54 [低] `core/notify_engine.py` 格式化/转义风险**
- `build_structured_alert_message(fmt="html")`：`f'<li><a href="{url}">{name}</a></li>'` → url/name 未 HTML 转义（email/teams html 通道可注入）。
- `send_email_notification`：`f"Subject: {subject}\n\n{body}"` 直接拼邮件头，subject 含换行即**邮件头注入**（无过滤）。
- `_send_one_channel` email 分支 `alert.get('summary', alert.get('title','AIOps Alert'))[:80]`：若 `summary` 键存在但值为 None，`.get` 返回 None → `None[:80]` TypeError。
- `_send_teams_notification` 每次新建 `aiohttp.ClientSession`（未复用单例）。

**B2-55 [低] `core/ai_engine.py` 规则降级引擎为示例占位**
- `_rule_based_analysis`(:约970)：注释自承 "示例实现：仅返回简短提示，实际可自行拓展规则库"，返回固定告警文案，非真实规则分析。
- 影响：`AI_CONFIG.is_enabled=False`（默认）时，`analyze()` 主降级路径返回的是固定占位文本 → 无 AI 环境下的"规则引擎"名不副实。

**B2-56 [中] `core/lifecycle_manager.py` gRPC server 句柄丢失 → 永不停机**
- `lifespan` 调 `_initialize_l5_interface_layer(_grpc_server)`（传入当时模块全局 `_grpc_server`=None）。
- 该函数内 `_grpc_server = AIOpsGrpcServer(...)` 为**局部变量**，未 `global` 声明 → 模块级全局 `_grpc_server` 始终为 None。
- 影响：`_shutdown_interface_layers` 读全局 `_grpc_server`（None）→ `if _grpc_server:` 恒假 → 后台 `asyncio.create_task(_grpc_server.start())` 启动的 gRPC 服务在 shutdown 时**不被停止**（资源泄漏/端口占用）。

**B2-57 [信息] `core/lifecycle_manager.py` 启动即播种弱口令管理员**
- `lifespan` 末尾无条件 `auth_init_db()` → 触发 B2-3（`admin/admin123`）种子；每次启动都会执行。

**已核对：非缺陷**
- `core/ai_engine.py` 主体（1640 行）加固到位：AE1/AE2 懒加载锁、AE3/AE4 CancelledError reraise、AE5/AE6 base_url 去尾 + max_retries 配置、AE7 prompt token 预算压缩、AE8-10 输入白名单、S5 PII 脱敏、预算/会话保护、RAG（真实 AIOpsRAG）、Langfuse 全降级、审计留痕，链路真实完整。
- `core/root_cause_intelligence.py` 主引擎（拓扑发现/跨层追溯/历史模式/假设-验证循环/置信度门控/多根检测/升级保护）逻辑真实自洽（仅 ML 部分装饰性、B2-52）。
- `core/performance_regression_detector.py` 统计检测（scipy t-test/Mann-Whitney/z-test/percentile/change-point/seasonal）与历史数据管理（JSON 落盘 + chmod 600）实现真实（仅告警通道为桩、B2-51）。

### B2-13 core/ KPI-SLO / 漏洞情报簇 —— 已通读（kpi_slo_manager 1291 / vulnerability_intelligence 1103）

**B2-58 [中] `core/kpi_slo_manager.py:evaluate_slo` 无数据即判"健康"**
- `evaluate_slo`：`if not history: return SLOEvaluationResult(current=1.0, ..., status="healthy", alert=False)`。
- 影响：窗口内**没有任何数据**时 SLO 被当作 100% 健康（与 `compliance_manager.run_compliance_check` "假设全部合规"同类"无数据即绿"）——监控空洞被掩盖为合规，而非 UNKNOWN/降级。

**B2-59 [低] `core/kpi_slo_manager.py` 全局单例在导入期加载配置**
- 文件末 `kpi_slo_manager = KPISLOManager()` → 导入即读 `config/kpi_slo_config.yaml` 并初始化 KPI/SLO；历史数据仅内存（`self.historical_data` deque），与 `core/kpi_config.py`/`slo_storage.py` 的持久化是两套。
- 另：`analyze_trend` 的 `forecast_horizon`/`sum_y2` 为预留死变量（已 noqa）。

**已核对：非缺陷（实现真实完整）**
- `core/kpi_slo_manager.py`：KPI/SLO CRUD、窗口解析、6 种聚合（good_ratio/uptime/p99_lt…）、误差预算/burn rate、SLA 报告、告警阈值、趋势回归、真实 time-to-exhaustion 估算、后台实时监控线程（daemon + stop event）——逻辑真实自洽（仅 B2-58 的"无数据即健康"口径问题）。
- `core/vulnerability_intelligence.py`：NVD/OSV/GitHub 三源真实 API 客户端（httpx、404 处理）、归一化 parser（CVSS v3.1/v2、CWE、CPE）、加权风险评估、SHA256 键缓存（TTL+LRU 淘汰）、令牌桶式速率限制、多源去重、告警句柄分发——真实完整；SSL 默认校验、可选 NVD/GitHub 令牌。

**批注（跨文件模式）**：本批再确认两类"看起来完成、实为空转"的桩：
1) **集成类**（integration_manager / integration_ecosystem）：cloud/cicd/monitoring 的激活与连通性测试为 no-op / 假成功，Jenkins/Jira 触发为本地回显；
2) **告警外发类**（performance_regression_detector）：webhook/email/slack 告警为 "would be sent" 日志桩。

### B2-14 core/ "增强 AI / 根因 / 变更" 簇 —— 已通读（enhanced_ai_capabilities 834 / advanced_ai_capabilities 866 / enhanced_root_cause_analyzer 845 / change_management_engine ~700）

**B2-60 [高，真·骨架] `core/enhanced_root_cause_analyzer.py` 整条分析链为空实现**
- 拓扑发现全部空转：`_discover_from_config`/`_discover_from_service_registry`/`_discover_from_database_metadata`/`_discover_from_monitoring`/`_discover_edges_from_config`/`_discover_edges_from_traces`/`_discover_edges_from_database_queries` **一律 `return []`**（注释 "实现…逻辑/示例：…"）。
- `_load_historical_incidents` 仅 log，**不加载任何数据**；`_apply_topology_change` body 为 `pass`。
- `_identify_critical_nodes` → `return []`；`_is_single_point_of_failure` → `return False`；`_analyze_dependency_chains` → `return []`；`_perform_ml_analysis` → `return []`（训练/predict 全被注释）；`_analyze_state_trends`/`_predict_potential_failures` → `return []`。
- `_calculate_pattern_similarity` 仅 `1.0 if hash1==hash2 else 0.0`（哈希精确相等）。
- 影响：`analyze_root_causes`/`predict_root_causes` 在真实运行中**恒返回空结果**（无节点、无历史、无因果边）。虽类结构与算法框架齐全，但**无任何数据接入**——典型"骨架已搭、业务未落地"。

**B2-61 [高] `core/advanced_ai_capabilities.py:_generate_response` 调用 `ai_engine.analyze` 签名/返回不匹配**
- `_generate_response`：`ai_response = await analyze(user_input, context_type="conversation")`，随后 `ai_response.get("analysis", ...)`。
- `core/ai_engine.analyze` 真实签名 `analyze(query, metrics_snapshot, platform, rich_context, system_prompt, validate_json)` **无 `context_type` 参数** → `TypeError`；且 `analyze` 返回 **str** 非 dict → `.get` 亦错。
- 影响：`AI_ENGINE_AVAILABLE` 且 intent∈{analyze_alert,root_cause,predict} 时该分支恒抛异常被 except 吞掉 → 静默降级到静态文案（对话"AI 生成"名不副实）。

**B2-62 [中] `core/advanced_ai_capabilities.py` 自适应学习上报硬编码"改进值"**
- `_online_learning_update` → `return 0.1  # Assume small improvement`；`_batch_learning_update` → `return 0.15`；`_rule_based_learning_update` → `return 0.05`。
- `_prophet_prediction`/`_ml_time_series_prediction`/`_rule_based_prediction` 的 `confidence` 硬编码 0.8/0.7/0.5。
- `_generate_alternatives` 返回静态 2 条；`_extract_features` 对字符串用 `float(hash(value)) % 100`（**hash 随机化 → 跨进程不可复现**）。
- 影响："adaptive learning" 的 `performance_improvement` 与预测置信度为**伪造常数**，非实测。

**B2-63 [中] `core/enhanced_ai_capabilities.py` 模型性能评估为常数 + 复学循环空转**
- `_evaluate_model_performance` → `return 0.8  # 默认值`（注释 "实现性能评估逻辑"）→ 每次 `adaptive_learn` 前后 accuracy 恒 0.8，`LearningUpdate` 改进恒 0。
- `_learning_loop` 中触发复学的 `# await self._retrain_model(model_id)` 被**注释** → 循环只检测不动作。
- `predict_natural_language` 类关键词解析（真实但浅）；`_compute_parse_confidence` 可按实体数无上限累加（`0.2*len`）后 `min(...,1.0)`。

**B2-64 [信息/范围扩大 · 关联任务 #5/#10] `data/` 下多份运行态 JSON 均被 git 跟踪**
- `git ls-files data/` 证实被跟踪：`data/change_requests.json`、`collaboration.json`、`collaboration_activities.json`、`docker_repair_history.json`、`i18n_translations.json`、`kpi_config.json`、`sla_reports.json`、`slos.json`、`teams.json`、`tenants.json`、`abac_policies.json`。
- 其中 `change_management_engine`（写 `data/change_requests.json`）、`docker_repair`（写 `data/docker_repair_history.json`）等为运行期可写 → **#5 不止 KPI 一个文件**，而是一整组受控目录下的可变状态文件，测试/运行都会污染工作树。
- `.benchmarks/` 已在 `.gitignore`（performance_regression_detector 的落盘路径安全）。

**已核对：非缺陷**
- `core/change_management_engine.py`（变更请求生命周期）：状态机（draft→pending→review→approved→implemented/rolled_back/rejected）、租户隔离（`PermissionError`）、审计日志、JSON 原子落盘（`_LOCK`+`to_thread`+`chmod 600`）、批量/搜索/统计/校验——**实现真实完整**（仅 `cancel_request` 复用 REJECTED 状态、写入受控 `data/` 两点备注）。

### B2-15 core/ 数据库/缓存/优化/审计/备份簇 —— 已通读
（cache_helpers 1001 / database_connection_optimizer 1062 / database_query_optimizer 1041 / database_cache_optimizer 704 / db_optimization 802 / metrics_exporter 831 / audit_service 729 / backup_strategy 992 / security_system_integrator 955 / performance_optimizer 684 ≈ 8,801 行）

**B2-65 [中] `core/cache_helpers.py:ThreeLevelCache` 的“L3 数据库缓存”是假的**
- `__init__` 中 `try: import config; self._db_available = True`——**仅 `import config` 成功即标记“数据库后端可用”**；`_set_db_cache/_get_db_cache/_invalidate_db_cache/_clear_db_cache` 全是**进程内 dict**（`self._db_cache`）。
- 影响：宣称 memory + Redis + **database** 三级缓存，实为 memory + Redis + 内存 dict；`_db_available` 在没有任何 DB 连接时恒为 True。

**B2-66 [中] `core/database_query_optimizer.py:generate_optimizations` 潜在 `UnboundLocalError`**
- 循环内 `optimization` 仅在 `if query_type == "n_plus_one"/...` 分支赋值；当 `_classify_query_pattern` 返回 `"unknown"`（无特征命中，常见）且为**首个**迭代时，末尾 `if optimization:` 读未绑定局部变量 → `UnboundLocalError`。调用链 `generate_optimization_recommendations → generate_optimizations` 无 try 保护。

**B2-67 [低] `core/database_query_optimizer.py:_generate_query_hash` 用 `str(hash(normalized))`**
- 依赖 Python 进程随机化哈希（PYTHONHASHSEED）→ query_hash 跨重启不稳定，`query_history` 归并/命中不可复现（同类 B2-62）。

**B2-68 [中] `core/database_query_optimizer.py` 的 join 重写为占位**
- `_rewrite_with_joins`/`_rewrite_join` 仅返回 `f"-- Optimized with joins\n{query_text}"`（加注释，**不改写**）；`_replace_select_star` 把 `SELECT *` 硬替换为 `SELECT id, created_at, updated_at`（对无这些列的表产出**错误 SQL**）。仅 `_rewrite_subquery` 为真实正则重写。

**B2-69 [架构] “优化器”家族为独立模拟，未接入真实 DB 引擎**
- `DatabaseConnectionOptimizer._create_connection` 只生成**字符串连接 ID + dataclass 指标**，不建立任何真实连接；`DatabaseCacheOptimizer` 为进程内 `OrderedDict`；`db_optimization` 后半 `_OPTIMIZATION_STATE` 为进程内 dict 模拟池/缓存；`DatabaseQueryOptimizer` 为进程内。均属“监控/分析模拟器”，非真实数据库优化。

**B2-70 [低] `core/database_connection_optimizer.py` 死代码**
- 模块级 `_begin_transaction`、`_get_transaction_stats` 定义后**未**绑定到类（类上绑定的是 test-compat 版）→ 死代码。
- `commit_transaction/rollback_transaction(pool_name)` 把实参当 `txn_id` 用，语义混乱。

**B2-71 [低] `core/db_optimization.py` 组件函数为进程内状态 + `SET` 会话级**
- 后半 `record_slow_query/record_query_cache_*/get_performance_summary` 等全基于模块级 `_OPTIMIZATION_STATE`（进程内），非真实 DB 统计。
- `optimize_database_configuration` 用 `SET log_min_duration_statement/work_mem/max_parallel_workers_per_gather`（**会话级**，连接回收即失效），而非 `ALTER SYSTEM`。

**B2-72 [中] `core/backup_strategy.py` 默认加密密钥硬编码 + 默认不一致**
- `encrypt_file/decrypt_file`：`key_source = os.getenv("BACKUP_ENCRYPTION_KEY", "backup-default-secret")` → 未设环境变量时“加密备份”用**已知默认密钥**（且 `cryptography` 缺失时直接 `shutil.copy2` **明文拷贝**并 `return True`）。
- 模块级 `_backup_config["encryption_enabled"]=True`，但 `configure_backup_strategy(encryption_enabled=False)` 默认关 → 用默认参数**反而关闭加密**（默认自相矛盾）。

**B2-73 [中] `core/backup_strategy.py:restore_database_backup` 尾部不可达死代码**
- try/except 两分支均 `return` 后，仍挂着 `if not _backup_history: return {...}; successful=...; return {...}`（疑似 `get_backup_statistics` 旧实现被误并入）→ 死代码；`restore_backup("logs")` 直接返回成功但**不还原任何日志**（no-op）。

**B2-74 [中] `core/audit_service.py` 两套清理语义不一致**
- `AuditService.cleanup_old_logs` 删除条件含 `AuditLog.action.notin_(SECURITY_ACTIONS)`（保护安全事件）；模块级 `cleanup_old_audit_logs` **无**该排除 → 会把安全事件一并删除，违反“保护安全事件”声称。

**B2-75 [中] `core/security_system_integrator.py` 连接/扫描为“Simulate”**
- `_connect_component`：`# Simulate connection` + `await asyncio.sleep(1)` 后**无条件**置 `IntegrationStatus.CONNECTED`（无真实连通性校验/失败感知）；`_scan_component`：`# Simulate component scan` + `asyncio.sleep(1)`，仅对持有 `get_statistics` 的组件读取统计。宣称“企业级安全系统集成/扫描”。

**B2-76 [低] `core/performance_optimizer.py:memory_monitor` 被覆盖为 bool**
- `__init__`：`self.memory_monitor = self._initialize_memory_monitor()`，而该函数内部 `self.memory_monitor = psutil.virtual_memory()` 后 `return True` → 最终属性为 `True`（内存对象被覆盖）。文件内暂无 `self.memory_monitor.` 读取，仅潜伏。
- `_background_monitoring_loop` 无条件起 daemon 线程（仅 `PERFORMANCE_OPTIMIZER_DISABLED=true` 关闭）。

**已核对：非缺陷**
- `core/metrics_exporter.py`：prometheus_client 自定义 registry、全套 Counter/Gauge/Histogram、`collect_from_performance_data/optimizer` 有 try 保护；与 `performance_optimizer.metrics_history`（`(ts,val)` 元组）及 `cache_stats`（`CacheStats.hits/misses/size`）类型一致。
- `core/audit_service.py` 主路径真实：`AuditLog`+`AsyncSessionLocal` 落库、`data_privacy.anonymize_dict` PII 脱敏、SHA256 完整性哈希、`audit_context` 上下文管理器。
- `core/database_cache_optimizer.py`：进程内缓存 LRU/LFU/TTL 淘汰、命中率/TTL 过期/预加载逻辑真实自洽。

### B2-16 core/ 数据/调用链/错误处理/优化器簇 —— 已通读
（data_lineage 733 / call_chain_analysis 674 / call_chain_analysis_engine 604 / error_handler 679 / error_handling_logging 709 / api_performance_optimizer 636 / api_throughput_optimizer 545 / cpu_usage_optimizer 588 / memory_usage_optimizer 498 / api_response_time_optimizer 503 / api_resource_optimizer 539 ≈ 6,708 行）

**B2-77 [中] `core/memory_usage_optimizer.py` 按组件泄漏检测恒失效**
- `take_memory_snapshot()` 构造 `MemorySnapshot(...)` 时**未传 `metadata`**（全文件无 `metadata=` 赋值）→ `metadata` 恒为 `{}`；而 `detect_memory_leaks(component)` 以 `s.metadata.get("component","system") == component` 过滤 → **任何非 "system" 的 component 都匹配为空 → 直接 return []**（泄漏检测对所有具名组件失效）。
- 对照：`cpu_usage_optimizer.take_cpu_snapshot` **正确**传 `metadata={"component": component}`。
- 证据：`grep -n metadata= core/memory_usage_optimizer.py` → 空。

**B2-78 [中] `core/api_throughput_optimizer.py:health_check_backend` 恒判健康**
- `:442` 注释 `# In real implementation, this would make actual health check request`，`:443` 无条件 `server.is_healthy = True` → 后端健康检查为**假**，故障节点永不被摘除，负载均衡持续派发到坏节点。

**B2-79 [高] 重名族：三对同名类跨模块并存且接口不兼容**
- `AIOpsException`：`error_handler.py:77` 与 `error_handling_logging.py:113`
- `ErrorSeverity`：`error_handler.py:32` / `error_handling_logging.py:30`；`ErrorCategory`：`:43` / `:41`；`ErrorHandler`：`:176` / `:206`
- `CallChainAnalysisEngine`：`call_chain_analysis.py:111`（`__init__(config)`，产出 dataclass）与 `call_chain_analysis_engine.py:139`（`__init__()` 无参，处理 Trace/Span）
- `ErrorHandler` 两者 `handle_exception` 签名/返回态不同：`error_handler.py:176` 为**同步** `handle_exception(exc, context, user_id, request_id) -> ErrorContext`；`error_handling_logging.py:206` 为 **async** `handle_exception(exc, context) -> ErrorRecord`。导入二选一，调用方无法互换。

**B2-80 [中] 构造即 `logger.remove()` 清空全局 loguru handler（全局副作用）**
- `error_handler.py:233` `logger.remove()`、`error_handling_logging.py:533` `loguru_logger.remove()` —— 两模块各自先清空全部 handler 再加自己的文件 handler；实例化即互相覆盖/接管全局日志。`error_handler.py:276` 还默认起 daemon 告警线程（仅 `DISABLE_ERROR_HANDLER=true` 关闭）。

**B2-81 [中] `error_handler.py` 错误历史无界**
- `:191` `self.error_history: List[ErrorContext] = []`、`:193` `self.error_patterns: ... = defaultdict(list)` 仅 `append`（`:377/:379`），无 `maxlen`。对照 `error_handling_logging.py` 用 `deque(maxlen=10000)` → 长跑内存增长。

**B2-82 [低] `error_handling_logging.py` 处理查找重复 + recovery 查找恒空**
- `_find_error_handler`（`:338`）内两个 for 循环内容完全相同（"精确匹配"/"基类匹配" 均 `isinstance(exception, exc_type)`），后者为死循环体。
- `_handle_aiops_exception`（`:370`）用 `self.error_handlers.get(type(Exception(error_record.error_message)))` → 恒查基类 `Exception` → 几乎恒 `None`（dead recovery 分支）。

**B2-83 [中] `core/cpu_usage_optimizer.py` 的"优化动作"不落地**
- `optimize_cpu` 对 REDUCE_PRIORITY/THROTTLE_PROCESSES/DISTRIBUTE_LOAD/SCALE_WORKERS 仅 `result["actions_taken"].append(...)` + 计数，附描述字符串；**无** `os.nice`/`os.setpriority`/cgroup/affinity/worker 池的真实调整 → 名为 "Enterprise-grade CPU usage optimization"，实为"记录意图"，CPU 真占用不受控。

**B2-84 [中] 优化器族 `asyncio.create_task` 不持句柄**
- `cpu_usage_optimizer.py:562` / `memory_usage_optimizer.py:473` / `api_resource_optimizer.py:514` 均 `asyncio.create_task(monitoring_loop())` 未保存引用 → 任务可被 GC 静默回收（无强引用），监控可能停摆。

**B2-85 [中] 用 `hash()` 生成 ID/缓存键（跨进程不可复现）**
- `api_performance_optimizer.py:304` `optimization_id=f"opt_{hash(endpoint)}"`、`:619` `cache_key=f"{func.__name__}:{hash(str(args)+str(kwargs))}"`（连同 B2-67 的 `database_query_optimizer.py:189/211/555`）→ 受 `PYTHONHASHSEED` 影响，跨重启 ID/缓存键不同。

**B2-86 [低] `api_performance_optimizer.py` 缓存键方案不一致**
- `setup_response_cache`（`:319`）写 `self.response_cache[endpoint] = {}`（以 **endpoint** 为键）；而 `set/get_cached_response` 用 `f"{endpoint}:{cache_key}"` 为键 → 初始化写入的 endpoint 键**永不被读取**；`invalidate_cache(endpoint)` 只删 `startswith(f"{endpoint}:")` 的键（`:328` 那条残留）。

**B2-87 [低] `api_throughput_optimizer.py` 枚举/分支缺口**
- `RateLimitStrategy.TOKEN_BUCKET = "token" + "_bucket"`（字符串拼接混淆）；`LEAKY_BUCKET` 已声明但 `check_rate_limit` **无对应分支**（落入 else 的 fixed window，语义与名字不符）；`lb_state["connection_counts"]`（defaultdict）**从未使用**（死状态）。

**B2-88 [低] `api_response_time_optimizer.py` 慢端点分析对样本<20 永久失效**
- `_update_metrics` 仅 `if len(sorted_times) >= 20:` 才计算 `p95_response_time_ms`（`:188-189`，否则默认 `0.0`）；而 `analyze_slow_endpoints` 仅以 `metrics.p95_response_time_ms > threshold` 入选（`:210`）→ **样本数 <20 的端点恒不入选**，慢端点分析对低流量端点静默失效。

**B2-89 [低/信息] `core/data_lineage.py` 宣称 DataHub/Amundsen 集成但无对接代码**
- docstring `:4` `"...using DataHub/Amundsen integration"`、`:126` 同；全文 import 仅 logging/uuid/dataclasses/datetime/enum/typing，**无 HTTP/客户端代码**；`storage` 为可选注入，不注入则纯进程内 dict。`analyze_impact` 仅统计直接下游（源码注释自承 "Could be extended with recursive analysis"）。

**B2-90 [中] `call_chain_analysis.py` 与 `call_chain_analysis_engine.py` 功能重叠且各自独立**
- 两文件同名类 `CallChainAnalysisEngine`（见 B2-79）但数据结构/算法完全独立（前者 baseline+统计检测；后者 Trace/Span 树），互不共享 → 属重名族（同 B2-61/B2-79），调用方按导入路径择其一。

**已核对：非缺陷**
- `core/call_chain_analysis.py`：z-score 异常检测、中位数基线、impact score、错误分类/置信度自洽真实（进程内）。
- `core/call_chain_analysis_engine.py`：span 树深度/分支因子/关键路径/多条件搜索自洽（明确标注 "Simplified" 但无伪造）。
- `core/api_performance_optimizer.py`：缓存 TTL、滑动窗口限流、百分位、命中率计算真实（除 B2-86 键不一致）。
- `core/api_resource_optimizer.py`：资源限额/软硬类型/调度执行/监控聚合逻辑自洽（进程内）。
- `core/error_handling_logging.py`：`ErrorHandler` 主路径（记录/分类/`with_retry` 装饰器/告警阈值/统计）真实完整。

### B2-17 core/ 可观测·健康·拓扑·隐私·日志簇 —— 已通读
（health_check 598 / topology_engine 571 / data_privacy 545 / telemetry_core 446 / observability_query 460 / cross_service_tracing 461 / log_router 517 / log_collector 512 / tracing_visualization 542 ≈ 4,652 行）

**B2-91 [高] `core/health_check.py` 两个组件健康检查为"恒健康"空壳**
- `check_alert_engine_health`（`:290` `"Alert engine operational"`）与 `check_repair_engine_health`（`:312` `"Repair engine operational"`）函数体**无任何检测**，直接 `return {"status":"healthy",...}`（注释 "Check if alert engine is operational" 挂空）→ 告警/修复引擎真实故障时健康端点仍报健康，`overall_status` 不会因它们变为 unhealthy。`check_metrics_health` 亦仅读 `config.METRICS_ENABLED`。
- 对照：`check_database_health`（真 `SELECT 1`）、`check_redis_health`（真 `ping()`）、`check_system_resources`（真 psutil）为真实实现。

**B2-92 [高] `core/topology_engine.py` 整体为占位/内存态，无 DB 持久化**
- 头注释自承 `:98 "# API 所需的占位实现（后续可接入真实业务逻辑）"`、`:186 "获取单个节点的时间线信息（占位实现）"`、`:196 "# 数据库/缓存占位接口（测试中会被 patch）"`。
- `insert_topology/query_topology` 仅读写模块级 `_topology_cache`（进程内 dict）；`_nodes/_edges/_topology_view_cache` 均内存态；`get_topology_status` 忽略 `topo_key`。
- `update_node_health(node_id, status)` 参数不用，**恒 `return True`**（`:188`，无任何状态更新）；`get_node_timeline` 恒 `{"events": []}`。
- 定性：拓扑 CRUD/视图管理整套是"名字齐全、逻辑占位、测试 patch 兜底"的骨架，非真实拓扑存储。

**B2-93 [中] `core/cross_service_tracing.py` 多传播器声明未使用**
- `TracingContext.__init__`（`:22`）建 `self.propagators = [TraceContextTextMapPropagator(), B3MultiFormat(), JaegerPropagator()]`，但 `inject/extract` 实际调全局 `propagate.inject/extract`，**`self.propagators` 全文再无引用** → 声称支持 B3/Jaeger 多格式传播，实际仅用全局默认（W3C）。

**B2-94 [中] `core/cross_service_tracing.py` 异步拦截器不结束 span**
- `trace_http_request_async`（`:106`）与 `trace_database_query_async`（`:196`）`return span` 后**不调用 `span.end()`**（同步版在 `finally: span.end()` `:104/:194` 有）；异步路径调 `create_span` 后无配对结束 → span 泄漏/永不导出。

**B2-95 [中] `core/cross_service_tracing.py` 硬依赖 opentelemetry（顶层 import）**
- `:11-16` 顶层 `from opentelemetry import trace` 等，无 try/except；而 `telemetry_core.py` 对 OTEL 做了 `OTEL_AVAILABLE` 守卫 → OTEL 未安装时导入本模块即 `ImportError`（与项目"OTEL 可选"策略不一致）。

**B2-96 [中] `core/tracing_visualization.py` 服务依赖边恒为空**
- `ServiceNode.dependencies`（`:66`）**全文无 append 写入**，仅 `generate_service_map` 读取（`:303`）→ `edges` 恒 `[]`，服务地图无任何依赖连线。

**B2-97 [中] `core/tracing_visualization.py:_build_flame_tree` 解析缺失 start_time 即崩**
- `:373` `datetime.fromisoformat(span.get("start_time", ""))` 无 try 保护：span 缺 `start_time` 或为空串 → `ValueError` 冒泡，`generate_flame_graph` 整体失败。对照同文件 `_build_span_tree` 直接透传 `start_time`（不解析）→ 行为不一致。

**B2-98 [中] `core/log_router.py:route_log` destination↔result 错位**
- 仅对已知 destination 追加 task（`:156` `for destination in self.destinations:` 内 if/elif），但结果处理 `for dest, result in zip(self.destinations, results)`（`:168`）按**原列表顺序**配对 → 当 `destinations` 含未知项（不产生 task）时，`zip` 将 task 结果错配给错误 destination（如 `["unknown","loki"]` → loki 结果被记到 "unknown"）。

**B2-99 [中] `core/log_router.py:LogRouterManager.remove_router` 默认路由清理失效**
- 先 `del self.routers[name]` 再判断 `self.default_router == self.routers.get(name)` → `routers.get(name)` 已为 `None`，条件恒假 → **删除默认路由后 `default_router` 仍悬空指向已删对象**。

**B2-100 [中] `core/data_privacy.py` GDPR 合规数据全在进程内内存，重启即失**
- `_consent_records`（dict）、`_privacy_audit_logs`（list）为模块级内存结构，无任何持久化；`record_consent`/`log_privacy_event` 仅 append → 合规审计日志与同意记录重启丢失（GDPR/SOC2 场景下不可作为审计证据）。
- `hash_pii`（`:?`）用**无盐 SHA-256**（同 B2-3 模式）→ 低熵 PII（邮箱/手机）可彩虹表反推；`gdpr_compliance` 标志仅存储、不参与任何逻辑。

**B2-101 [低] `core/telemetry_core.py:reset_apm_metrics` 硬编码复位时间**
- `:325` `"last_reset": "2026-06-12T00:00:00Z"` 为**硬编码常量**，非 `datetime.now()` → 复位时间恒显示同一固定值，误导 APM 排查。
- 另：`record_apm_metric` 每次调用都 `meter.create_counter(...)` 新建计数器（未缓存），OTEL 下会重复创建；`initialize_telemetry` 把 `deployment.environment` 硬编码为 `"production"`。

**B2-102 [低] `core/observability_query.py` 全局 Semaphore 绑定事件循环**
- `_query_semaphore` 模块级 `asyncio.Semaphore`（`:92` 惰性创建）跨事件循环复用 → 多 loop 场景（测试/worker）可能触发绑定错误。模块其余（查询校验/字符白名单/PII 脱敏/令牌截断/时间窗对齐）质量高。

**已核对：非缺陷**
- `core/observability_query.py`：查询白名单校验、`build_clickhouse_query` 参数化、`_redact_recursive`、`prepare_for_llm` 截断、`align_time_window` 均真实健壮（仅 B2-102 一处）。
- `core/log_collector.py`：`_sanitize_keyword` 双重过滤、`newest` 钳制、PowerShell 子进程超时 kill、`source` 白名单、grep 链 head 防爆——加固完整（R2 修复真实有效）。
- `core/health_check.py`：`perform_health_checks` 并发聚合、告警回调、趋势分析、恢复建议、liveness/readiness 逻辑自洽。
- `core/log_router.py`：Loki/ES/Kafka/S3 四目的地真实 HTTP/客户端实现（Kafka/S3 走 `asyncio.to_thread` + 可选库守卫）。
- `core/cross_service_tracing.py`：同步拦截器（HTTP/DB/MQ）span 生命周期与异常记录正确。

### B2-18 core/ 集成域簇 —— 已通读
（integration_manager 1171 / integration_repository 915 / integration_monitoring_system 582 / integration_testing_system 570 / integration_test_validator 510 / third_party_service_integrator 492 / audit_integration_manager 510 ≈ 4,750 行）

**B2-103 [高] "集成测试系统"与"集成测试验证器"产出伪造随机结果**
- `integration_testing_system._execute_test`：`await asyncio.sleep(2)  # Simulate test execution` 后 `_random = secrets.SystemRandom(); is_passed = _random.random() > 0.2  # 80% chance of passing`，`coverage = _random.uniform(70.0, 95.0)` → **从未执行真实测试**，随机决定通过/失败/覆盖率。
- `integration_test_validator._execute_validation`：同样 `# Simulate validation execution` + `is_passed = _random.random() > 0.15` → 随机判定验证通过。
- 定性：两个"Enterprise-grade integration testing/validation system"是**假测试引擎**，可对从未运行的测试报 "passed"/覆盖率，并落盘 JSON 报告（`generate_test_report`/`generate_validation_report`）。

**B2-104 [高] `integration_monitoring_system._collect_metrics` 生成随机假指标**
- `:422-442` `_random = secrets.SystemRandom()`，注释 `# Simulate metric collection` / `# Simulate random values`，对 cpu/memory/disk/latency/error_rate 返回 `_random.uniform(...)` → **监控系统不读真实系统指标，而是随机数**；且这些随机值直接驱动告警触发（`record_metric → _check_monitors → _trigger_alert`）。

**B2-105 [高] `audit_integration_manager._collect_from_source` 伪造审计轨迹并落盘**
- `:?` 注释 `# Simulate collection from source` / `# In real implementation, would connect to actual audit source`，`num_trails = _random.randint(0, 10)`，生成 `event_type=f"sample_event_{i}"`、`action=f"Sample action {i}"` 的假 `AuditTrail`，写入 `self.audit_trails` **并由 `_store_trail` 追加落盘 `./audit_integration/trails_*.jsonl`** → **假审计证据被持久化**（合规场景下严重）。

**B2-106 [高] `integration_manager` 多云/CI/CD/ITSM 集成测试与触发为"恒成功"**
- `_test_cloud_integration`（`:593-594` `# Simplified cloud integration test` → `return {"success": True, "message": "... passed"}`）、`_test_cicd_integration`（`:598-599` 同）→ AWS/Azure/GCP/Jenkins/GitLab/GitHub 注册时"测试通过"是伪造。
- `_test_monitoring_integration` 仅 Prometheus 真实（`GET /api/v1/query`），其余监控工具走 `:589` 恒成功。
- `trigger_jenkins_job`（`:1074` 注释 `# Jenkins job trigger logic` 后直接）`return {"success": True, "message": f"Job {job_name} triggered successfully"}` → **未触发任何 Jenkins 作业**。

**B2-107 [中] `integration_manager` webhook 事件处理为空壳**
- `_handle_alert_event`（`:812` `# Alert processing logic`）、`_handle_deployment_event`（`:817`）、`_handle_incident_event`（`:822`）**仅 `logger.info`，无业务逻辑**；`_process_webhook_event` 之后仍置 `event.processed = True` → 告警/部署/事件型 webhook 被标记"已处理"却什么都没做。

**B2-108 [中] `integration_manager.WEBSOCKET_AVAILABLE` 恒为 True（空 try）**
- `:65-70`：`try: pass` 后 `WEBSOCKET_AVAILABLE = True`，`except ImportError` 分支永不可达 → 无论是否安装 websockets，标志恒 True（虚假能力探测）。

**B2-109 [中] `integration_manager` 配置型通知通道从未加载（死方法）**
- `_initialize_notification_channels`（`:339`）从 `config["notification_channels"]` 构建通道，但 `__init__` **只调 `_load_notification_channels_from_db`**，从不调用它 → 配置里定义的通道全部不生效。
- 另：`webhook_secret` 默认 `"default_secret_change_me"`（弱默认密钥）；`register_webhook` 写进程内 `self.webhooks` 而非 `WebhookRepository`（DB 仓储被旁路）。

**B2-110 [中] `core/third_party_service_integrator.py` 健康检查为被动读状态**
- `health_check` 仅返回 `connection.status.value`（不做 ping/探测）；`start_health_check_loop` 调它 → "健康检查循环"不会发现真实断连（状态仅由 connect/disconnect 改写）。Neo4j/Consul 主路径为真实实现（`AsyncGraphDatabase`/`httpx`）。

**已核对：非缺陷**
- `core/integration_repository.py`：Integration/Webhook/WebhookEvent/NotificationChannel 四套完整 CRUD 仓储（真 `Session.query`、分页/过滤/计数、软删），代码真实（注：走同步 SQLite `core.database`，与主体异步 Postgres 双栈——归 B2-16 架构项）。
- `core/integration_manager.py`：`query_prometheus_metrics`/`query_cloudwatch_metrics`/`query_pagerduty_incidents` 为**真实**实现（PromQL 校验 + 超时 + 缓存 + CloudWatch GetMetricData + PagerDuty REST），是本文件可信部分。
- `core/third_party_service_integrator.py`：Neo4j 查询（driver.session）、Consul KV PUT/GET/服务注册为真实 SDK/HTTP 实现。

### B2-19 core/ 服务网格·工作流·插件簇 —— 已通读
（service_mesh_manager 513 / workflow_engine 635 / plugin_system 510 / plugin_marketplace 635 / plugin_system_manager 506 / plugin_development_sdk 596 ≈ 3,395 行）

**B2-111 [高] `plugin_development_sdk` 生成的集成/AI 插件代码缺 `datetime` 导入，运行即 NameError**
- 集成模板 `code_template`（约 `:200+`）与 AI 模板（约 `:340+`）仅 `from typing import ...` + `from loguru import logger`，**无 `datetime` 导入**；但模板体内 `execute_action`（`:245`）与 `process_input`（`:369`）调用 `datetime.now(timezone.utc)` → `generate_plugin_code("integration"/"ai", ...)` 产出的插件**一执行即 `NameError: name 'datetime' is not defined`**。仅 monitoring 模板（`:68` 有 `from datetime import datetime, timezone`）正确。
- 定性：SDK 的核心产物（可运行插件模板）对 2/3 模板是**不可运行代码**，违反"交付即可运行"标准。

**B2-112 [高] `plugin_marketplace` 的"数字签名"实为对称 HMAC，且验证用同一密钥**
- `_sign_plugin`（`:311`）`hmac.new(self.private_key.encode(), message, sha256)`；`verify_plugin`（`:385-386`）**用同一个 `self.private_key`** 重算比对 → 无公私钥对；`public_key`（`:45/:56/:318`）仅存储与回显，**从不参与签名/验证**。docstring 声称"digital signatures / public key verification"。
- 连带：`_sign_plugin` 里 `PluginSignature(..., verified=True)` **签名时即置 verified=True** → `approve_plugin` 的 `if plugin.signature and not plugin.signature.verified` 门禁**永不拦截**（审批校验形同虚设）。

**B2-113 [中] `service_mesh_manager` 只生成清单、从不部署**
- `configs_applied` 声明（`:97`）并在 `generate_service_mesh_summary`（`:328`）上报，但**全文无任何自增点**（无 apply/deploy 方法）；`mesh_status` 恒 `NOT_CONFIGURED`（无置位）；`MeshStatus.DEPLOYED/ERROR` 不可达。
- `supported_features` 列出 `traffic_mirroring`/`fault_injection`（`:335-336`），但 `TrafficConfig.mirroring_config/fault_injection_config` 字段（`:52`）**无任何生成方法** → 宣称支持、实际无实现。

**B2-114 [中] `plugin_system._discover_plugins` 按文件名裸 `import_module`，跨目录同名冲突**
- `_load_plugin_from_file` 用 `os.path.splitext(basename)[0]` 作 module 名并 `importlib.import_module(module_name)` + `sys.path.insert(0, dir_name)` → 不同子目录下同名文件相互覆盖/命中先入 `sys.path` 者；且发现阶段 `instance = obj()` 实例化即产生副作用（部分插件构造即起后台线程）。

**B2-115 [中] 插件域 4 元并存且语义重叠（重名/重域族）**
- `core/plugin_system.py`（真加载执行）、`core/plugin_system_manager.py`（**仅元数据注册表，不加载/执行任何插件代码**）、`core/plugin_marketplace.py`（注册/签名/审批）、`core/plugin_development_sdk.py`（模板生成）四模块各建一套 `PluginStatus`/`PluginType`/`PluginMetadata`（同名类不同枚举值），调用方需按用途择一。

**B2-116 [低] `plugin_system_manager` 依赖约束解析为朴素字符串切分**
- `register_plugin` 用 `dep.split(">=")[0]` / `">=0.0.0"` 兜底解析依赖；`_check_version_compatibility` 逐段 `int()` 比较（非 PEPS 440 语义，`1.10` vs `1.9` 会误判）；`_check_dependencies` 只查同注册表内是否 ENABLED，不校验实际版本。

**已核对：非缺陷**
- `core/workflow_engine.py`：自述"工作流仿真引擎"（前端 SSE 演示用），`simulate_workflow_stream` 明确为仿真（随机延迟/警告概率可配），W1–W10 加固（`MappingProxyType` 只读、深拷贝、延迟钳制、字段防爆、key 校验）真实有效；`execute_langgraph_workflow` 在 LangGraph 可用时为真实执行。**命名已如实标注"仿真"，不算冒充**。
- `core/plugin_system.py`：插件 ABC + 目录发现 + 生命周期（initialize/execute/close）+ 类型过滤，加载/执行链路真实。
- `core/plugin_development_sdk.py`：模板/配置生成、包导出逻辑真实（缺陷仅 B2-111 的模板导入遗漏）。
- `core/service_mesh_manager.py`：Istio 清单生成（control-plane/auto-injection/VirtualService/DestinationRule/PeerAuthentication/Sidecar CR/sidecar 注入/Deployment 注入）为真实 YAML 结构产物（缺陷仅在"无部署、宣称超范围"）。

### B2-20 core/ 基础设施·部署·gRPC 簇 —— 已通读
（kubernetes_deployment_manager 507 / grpc_service_manager 515 / infrastructure_repository 554 / infrastructure_service 496 ≈ 2,072 行）

**B2-117 [高] `kubernetes_deployment_manager` 全程模拟，不接触真实集群却报成功**
- `_apply_manifests`：注释 `# In real implementation, would use kubectl or Kubernetes Python client` 后 `await asyncio.sleep(2)  # Simulate applying manifests` → **无任何 kubectl/API 调用**。
- `_wait_for_deployment_ready`：`await asyncio.sleep(5)  # Simulate waiting for readiness` → 无轮询，直接视为 ready。
- 结果：`_execute_deployment` 随后置 `status=RUNNING`、`ready_replicas=config.replicas`、`successful_deployments += 1` → **"部署成功"是伪造的**。
- `rollback_deployment`：`await asyncio.sleep(3)  # Simulate rollback` → 无论什么情况都回到 RUNNING（假回滚）；`scale_deployment` 只改内存 `config.replicas`（不调用 k8s 扩缩容）。

**B2-118 [中] `grpc_service_manager` 生成的 Python 服务代码 f-string 端口插值失效**
- `_generate_python_content` 以 `lines.append("    server.add_insecure_port(f'[::]:{{port}}')")` 与 `lines.append("    logger.info(f'... port {{port}}')")` 拼装 → 输出文件里保留字面 `{{port}}`；作为 f-string 求值得到**字面量 `{port}`**，端口不会被替换 → 生成代码行为错误。
- 且生成的服务方法体为 `pass`、protobuf 导入与 `add_..._Servicer_to_server` 均被注释 → 生成的 gRPC 服务不可运行（属脚手架性质，但与"可运行交付"有落差）。

**B2-119 [中] `infrastructure_repository.health_check` 不做真实连通检测**
- `InfrastructureStorageRepository.health_check` 注释 `# In production, this would perform actual connectivity checks`，仅回读 `storage.health_status`（该值只由 `update_health_status` 手工写入）→ 健康检查为被动回显，不会发现存储实际不可达。

**已核对：非缺陷**
- `core/infrastructure_repository.py`：Kafka/Flink/Storage/Config/DataFlow/Monitoring 六套仓储为**真实** SQLAlchemy 读写（真 `query/add/commit/refresh`、过滤/分页/计数/版本自增），`InfrastructureConfigRepository.set_config` 版本管理正确。
- `core/infrastructure_service.py`：服务层真实组合仓储 + 真实 `kafka_processor`/`monitoring_infrastructure` 调用，异常兜底与状态聚合正确。
- `core/grpc_service_manager.py`：proto 文本模板（unary/server_streaming/client_streaming/bidi_streaming）、message 字段编号生成为真实字符串生成逻辑（缺陷仅 B2-118 的 f-string 转义）。

### B2-21 core/ 数据/本地化/i18n 簇 —— 已通读
（i18n_manager 594 / data_lifecycle_manager 545 / localization_adapter 459 / data_integration_manager 635 ≈ 2,233 行）

**B2-120 [高] `i18n_manager` 数字/日期/时区格式化三处失效**
- `format_number`：`return locale.number_format.format(number)`，而 `number_format` 值形如 `"#,##0.##"`（无 `{}` 占位符）→ `str.format` 无占位直接**原样返回字符串**，故**任何数字都返回字面量 `"#,##0.##"`**（非数字格式化）；`format_currency` 因此恒返回如 `"CNY #,##0.##"`。
- `format_date`：语句 `locale.date_format` 为**无用表达式**，随后 `return date.strftime("%Y-%m-%d %H:%M:%S")` → **恒用同一硬编码格式，忽略 locale**。
- `convert_timezone`：注释 `# For now, return the same datetime` + `return date` → **不做任何时区转换**。
- 影响：i18n 域三个核心能力（数字/日期/时区）实为占位；`detect_locale_from_request` 的 timezone 分支仅校验后 `pass`。

**B2-121 [中] `localization_adapter._convert_unit` 单位换算为 no-op**
- `_convert_unit` 注释 `# In production, use a proper unit conversion library` 后 `return value` → `format_unit` 对 metric↔imperial **不转换**，返回 `f"{value} {unit}"`（原值原单位），宣称的"单位系统转换"未实现。

**B2-122 [高] `data_integration_manager._sync_from_source` 伪造数据并写入存储**
- 注释 `# Simulate sync from source` / `# In real implementation, would connect to actual data source` + `await asyncio.sleep(1)`；`num_records = _random.randint(0, 20)`，然后 `ingest_data(..., {"data": f"sample_data_{i}", ...})` → **"数据同步"凭空造随机样本记录**，并经 `_store_record` 落盘 `./data_integration/records_*.jsonl`。

**B2-123 [中] `data_integration_manager._log_access` 访问审计未落盘**
- `_log_access` 注释 `# In real implementation, would log to audit system`，实际仅 `logger.debug` → 对 `access_logging=True` 的策略（public/internal/confidential/restricted/critical 全为 True）**数据访问未被持久化审计**。
- `_apply_data_masking` 亦自述 `# Simulate data masking`（实际做了首2尾2掩码，可接受但标注为 simulate）。

**已核对：非缺陷**
- `core/data_lifecycle_manager.py`：**真实** DB 归档实现——`_fetch_expired_rows`/`_delete_expired_rows` 用 `text()` 执行真 SQL（表/列取自 `core/models` 的 `alerts.detected_at`/`metrics.timestamp`/`audit_logs.created_at` 白名单映射，非用户输入），gzip+JSONL 落盘归档，文件类目递归清理，`archive_old_data`/`apply_retention_policy` 经 `AsyncSessionLocal` 真连接。质量高。
- `core/localization_adapter.py`：`format_number`（f-string + 分隔符替换）、`format_date/format_datetime`（按 `date_formats` 映射）、`format_currency`（符号位置）为**真实**实现（缺陷仅 B2-121 单位换算）。
- `core/i18n_manager.py`：翻译资源加载/回退链（namespace→common→fallback_language）、`data/i18n_translations.json` 原子读写 + chmod、`set_translation` 持久化——真实（缺陷仅 B2-120 的格式化三方法）。

### B2-22 core/ AI 服务·模型微调·业务影响·容量·NLP/RAG/向量簇 —— 已通读
（ai_service 474 / model_fine_tuner 545 / model_inference_config 131 / business_impact_engine 466 / business_metrics 319 / ai_enhancement 338 / ai_interface 92 / backend_requirements 71 / capacity_engine 185 / enhanced_nlp 321 / rag_engine 331 / vector_pipeline 128 / qdrant_service 563 ≈ 3,964 行）

**B2-124 [高] `business_metrics.collect_business_metrics_task` 引用未定义名 → 周期采集任务一启动即崩**
- 第 308/312 行调用 `business_metrics_collector.get_metrics()` / `.cleanup_old_data()`，但本模块全局实例名为 `BUSINESS_METRICS_COLLECTOR`（第 278 行），无 `business_metrics_collector` 绑定 → `NameError`。
- 客观佐证：仓库自带类型检查基线 `mypy_baseline.txt:1073` 已白纸黑字记录 `core/business_metrics.py|name-defined|Name "business_metrics_collector" is not defined; did you mean "BusinessMetricsCollector"?`（即团队已扫描到但未修）。
- 影响：`setup_business_metrics()` 正常，但同名采集协程首次执行即 `NameError`，被 except 吞掉后 `sleep(60)` 无限重试 → 业务指标永不采集、MTTR/MTTA/解决率始终为空。

**B2-125 [中] `ai_service.py` 使用 PEP 701 多行 f-string，但项目声明 Python ^3.10 → 3.10/3.11 下整模块 ImportError**
- `_fetch_correlated_alerts` 内 `txt = f"{\n a.get(\n 'title',\n '')} {...}"` 为跨行表达式内插（PEP 701，仅 Python 3.12+ 合法），且外层双引号内再嵌单引号。本机 3.12 可解析。
- 客观佐证：`pyproject.toml:12/15` 声明 `python = "^3.10"`。3.10/3.11 下 `core/ai_service.py` 解析即 `SyntaxError` → 依赖它的 AI 富上下文接口全部导入失败。

**B2-126 [中] `model_fine_tuner.export_model` 伪造导出成功**
- 方法注释 `# In real implementation, would export actual model`，仅 `export_path.parent.mkdir(...)` 后直接 `logger.info(f"Model exported to: {export_path}")` 并 `return str(export_path)` → 从未写模型文件，返回的路径指向不存在的文件。
- 注：该模块**训练主链真实**（`transformers.Trainer`+`datasets.load_dataset`+`model.save_pretrained` 存 checkpoint、真 loss 回填、缺依赖时 `RuntimeError`），缺陷仅在 `export_model` 这一步。

**B2-127 [中] `capacity_engine.forecast_capacity` 在无真实历史时静默替换为硬编码合成序列**
- `if len(values) < 2: values = _to_floats(_DEFAULT_SERIES.get(key, [0.0]))` —— `_DEFAULT_SERIES` 是写死的上升斜坡（cpu 45→50…），随后线性外推 → 无数据时**"容量预测"来自编造数列**并驱动 scale-up 建议。
- 文档称"从历史指标序列做线性回归预测"；公开 `linear_forecast()` 特意"never substitutes a default series"，但业务入口 `forecast_capacity` 依旧替换 → 一真一假并存。

**B2-128 [中] `qdrant_service.get_vector_stats` 恒失败（属性不存在）**
- 遍历 `client.get_collections().collections` 后读 `col.points_count` 与 `col.config.params.vectors.size`，但该 API 返回的是 `CollectionDescription`（仅 `name` 字段）→ `AttributeError`，被 except 捕获后恒返回 `{"status": "error", ...}`。另 `total_points = sum(col.points_count ...)` 同行同因失败。
- （qdrant-client 未安装，运行时不可复现；结论基于该 API 返回模型结构 + 代码路径，标注为待运行确认。）

**B2-129 [中] `qdrant_service.search()` 用已被移除的 `client.search(...)`，与 `rag_engine` 的 `query_points` 不一致**
- 新版本 qdrant-client 移除/废弃 `QdrantClient.search()`（`rag_engine.search_similar` 已改用 `client.query_points`）。同一项目两条检索路径一新一旧。
- 附带：`search_hybrid` 的文本打分把命中项 `"score": 0.8` **硬编码**，且 `client.scroll(limit=100)` 只扫前 100 个点，非全库文本检索。

**B2-130 [中] `rag_engine.upsert_records` 用内建 `hash()` 造点 ID → 跨进程不确定、重复入库**
- `id=record.get("id") or (abs(hash(record["text"])) & ((1 << 63) - 1))` —— `hash(str)` 受 `PYTHONHASHSEED` 影响，不同进程/重启对同一文本得到不同 ID → 同一记录在 Qdrant 中被反复写成不同 point（与 B2-62/B2-67 同一"`hash()` 当稳定键"模式）。

**B2-131 [中] `rag_engine` 文档与实现不符：声称 sentence-transformers/BGE-zh，实际走 MiniMax HTTP embeddings**
- 模块 docstring："使用 sentence-transformers 的 BGE‑zh‑Embedding 模型进行中文语义向量化"；但 `_embed()` 实际 `httpx.post(f"{base_url}/embeddings", ...)` 调 MiniMax 接口，`_get_model()`/`SentenceTransformer` 分支**定义了却从不被调用**（死路径）。真实依赖是 `AI_API_KEY` 而非本地模型。

**B2-132 [低/中] `ai_enhancement._calculate_cache_hit_rate` 伪造命中率**
- 注释 `# Fallback: estimate hit rate from cached contexts vs total analyses`，用 `len(self._context_cache)/total_analyses` 当命中率，无真实 hit/miss 计数；且缓存/历史全为进程内 dict，重启即失。

**B2-133 [低] `enhanced_nlp` 双份硬编码动作表 + 恒 0.8 兜底置信度**
- `_precompute_action_embeddings.action_patterns` 与 `_keyword_match_action.action_keywords` 是两份**同内容硬编码**表（漂移风险）；关键词兜底 `confidence=0.8` 为固定值非计算值。模块级 `_model=None` 全局定义了但未使用（真实模型在实例 `self._model`）。

**B2-134 [低] `qdrant_service.search_hybrid` 未使用导入 + 有界扫描**
- `from qdrant_client.models import ScrollRequest, Filter, FieldCondition, MatchText` 均未使用；文本检索受 `scroll(limit=100)` 限制。

**已核对：非缺陷 / 正例**
- `core/backend_requirements.py`：**正面样板**——用显式 `503 + {"error":"requires-backend"}` 取代"编造一个看似合理的数"，正是为治理本台账反复出现的"伪造结果"类缺陷而引入的规范化方案。
- `core/ai_interface.py`：纯 ABC 抽象接口（全 `@abstractmethod`），无实现是有意为之（同任务 #17 判定为非缺陷）。
- `core/ai_service.py`：10+ 数据源并行采集、`asyncio.wait_for` 逐源超时、`return_exceptions`+`CancelledError` 正确上抛、异常隔离为 `None` 兜底——实现真实（缺陷仅 B2-125 版本语法）。
- `core/rag_engine.py`：Qdrant 客户端懒加载 + MiniMax embeddings + 空向量防护 (`if not vectors or not vectors[0]: raise`) + `query_points` 新 API——主链真实（缺陷仅 B2-130/131）。
- `core/vector_pipeline.py`：诚实懒加载，缺 `sentence-transformers` 时抛带安装指引的 `RuntimeError`，不伪造向量。
- `core/model_inference_config.py`：真实 env 驱动配置 + 单例。
- `core/business_impact_engine.py`：拓扑/监控/优先级真实取数，`_BASE_USERS/_REVENUE_PER_USER` 等为**业务假设常数**（文档标注为估算模型），非桩（缺陷仅 B2-132 命中率、`list_services` 空时兜底硬编码服务名）。
- `core/qdrant_service.py`：create/delete/upsert/search/clear/update_collection_config 为真实客户端调用（缺陷仅 B2-128/129/134）。

### B2-23 core/ 运行可靠性·分布式存储·消息/流处理簇 —— 已通读
（circuit_breaker 336 / resilience 214 / retry_enhanced 390 / concurrency_control 23 / idempotent 337 / dual_write 288 / db_replication 358 / db_read_write_router 358 / dependency_injection 351 / message_queue 312 / distributed_storage 291 / redis_cluster 394 / redis_cluster_manager 171 / kafka_stream_processor 292 / flink_stream_processor 210 ≈ 4,325 行）

**B2-135 [高] `idempotent.IdempotencyStore.get` 用 typing 泛型当构造器调用 → 命中缓存即 TypeError**
- `core/idempotent.py:57/117`：`return Dict[str, Any](response) if isinstance(response, dict) else None`。
- 实测：`python -c "from typing import Dict,Any; Dict[str,Any]({'a':1})"` → `TypeError: Type Dict cannot be instantiated; use dict() instead`。
- 影响：首次请求（键不存在）正常；**重复请求命中缓存、恰好要走 `return` 字典**时抛 TypeError → 幂等去重（本模块唯一功能）在关键时刻必然失败，`IdempotencyMiddleware` 会 500。`RedisIdempotencyStore.get` 同 bug（fallback 路径）。应为 `dict(response)`/直接 `response`。

**B2-136 [中] `resilience.CircuitBreaker` 不捕获异常 → 永不熔断（且与 `circuit_breaker.py` 重名双实现）**
- `core/resilience.py` `CircuitBreaker.call`：`result = func(...); self.record_success(); return result` —— **无 try/except**，被包装函数抛异常时 `record_failure()` 从不执行 → `failures` 恒 0，断路器永不 OPEN。`call_async` 同样。
- 另：本文件又定义一个 `CircuitBreaker`（与 `core/circuit_breaker.py` 的同名类并存，`circuit_breaker()` 装饰器亦重名）→ "同名族并存"模式再现（承 B2-115）。

**B2-137 [高] `flink_stream_processor` 流处理入口恒返回空，真实实现 `_stub_process` 定义了却从不被调用**
- `FlinkStreamJob.process_stream(self, stream_data)` 直接 `return []`；而签名匹配、逻辑完整的 `_stub_process()`（遍历→`_process_record()`→按作业类型 `_aggregate_metrics/_detect_anomaly/_clean_data/_aggregate_alerts`）**全项目无任何调用点**。
- 同文件 `start_job`/`stop_job` 恒 `return True`、`FlinkJobManager.get_job_status` 恒 `return {}`、`self._initialized=True` 硬写。→ "Flink 流处理适配器"的能力入口是空转。

**B2-138 [中] `db_read_write_router._check_replica_health` 恒 True（自带 "simulate" 注释）**
- `_check_replica_health`：`# In real implementation, would check actual database connectivity` / `# For now, simulate health check` → `return True`；`_check_all_replicas_health` 顶部注释 `# Simulate health check`。
- 影响：健康检查后台循环永不把副本置为 UNHEALTHY → `is_available()` 只看 state/lag，读写分离永远认为副本健康，坏副本继续被路由。

**B2-139 [中] `dual_write._write_to_victoriametrics` 异步写 fire-and-forget，未持任务引用且乐观返回 True**
- `async_write=True` 分支：`asyncio.create_task(self._vm_storage.store(...))` 后立即 `self._stats["vm_writes"] += 1; return True` —— 既不 await 也不保存 task 引用（事件循环可能回收，写失败无感知）；统计 "vm_writes" 与"写成功"不等价。
- 另：类 docstring 称双写到 "SQLite ... and VictoriaMetrics"，但 `_write_to_sqlite` 实际写的是 `core.metrics_history.METRICS_HISTORY`（**进程内内存结构**，非 SQLite）→ 命名与实现不符。

**B2-140 [中] `distributed_storage.check_health` 无条件置副本可用（自带"应有实际健康检查"注释）**
- `ReadWriteRouter.check_health`：`slave.is_available = True` + `# 这里应该有实际的健康检查逻辑` → 健康检查是假的；`configure_redis_cluster` 内 `# cluster = RedisCluster(...)` 被注释 → 集群配置为 no-op。
- 另：本文件 `ReadWriteRouter` 与 `core/db_read_write_router.ReadWriteRouter` **同名双实现**（不同语义），再现同名族模式。

**B2-141 [中] `db_replication.promote_replica_to_primary` / `redis_cluster.promote_replica_to_master` 只改变量不真提主**
- 两者 failover 的"提主"仅 `_current_primary = replica_key` / `_node_health[node_key]["role"]="master"`，不执行任何真实的复制角色切换（如 `pg_ctl promote`、`REPLICAOF NO ONE`）。健康探测本身是真的（TCP `open_connection` / RESP `PING`），但**故障转移动作是象征性的** → 上报"failover 成功"与实际数据面无必然联系。

**B2-142 [低/中] `message_queue` 多处能力桩：`ack_message` 恒 True；集群/复制/扩容为 no-op**
- `ack_message` 恒 `return True`（无参 usage）；`get_cluster_status` 硬编码 `"nodes": 1`；`enable_replication()` 恒 True 无实现；`join_cluster()` 仅日志；`rollback_transaction` 注释自承 "replay recorded operations is not implemented; this is best-effort"。
- 正面：持久化落 `data/message_queue_state.json`（已确认**未被 git 跟踪**，非受控污染）；`_try_real_publish` 真 RabbitMQ/Kafka，否则内存。

**B2-143 [低] `dependency_injection.setup_core_services` 工厂同步调用 + `get_llm_router is None` 分支**
- `create_ai_engine_service` `from core.ai_engine import get_llm_router; if get_llm_router is None: raise` —— 若 `core.ai_engine` 导入失败则整个 `setup_core_services` 落入外层 except 返回 error，其它核心服务注册被一并放弃（无逐项隔离）。
- `DIContainer.get()` 直接 `factory()`（不判协程），异步工厂会返回 coroutine 造成隐蔽 bug。

**B2-144 [低] `concurrency_control` 三行模块**：仅定义全局 `Semaphore(50)` 与 `ConcurrencyController.run_with_limit`（模块级 Semaphore 在 3.10+ 不再绑定 loop，可接受）。

**已核对：非缺陷 / 正例**
- `core/retry_enhanced.py`：指数/线性/固定 + SystemRandom 抖动 + deadline + 回调，实现真实。
- `core/circuit_breaker.py`：CLOSED/OPEN/HALF_OPEN 状态机 + 超时 + 同步/异步 wrapper，实现真实（缺陷仅在"与 resilience 重名"）。
- `core/redis_cluster.py`：`check_node_health` 真实 RESP `PING\r\n` 握手 + 响应校验，为**正例**真实探测。
- `core/redis_cluster_manager.py`：真 Redis-first + 内存 fallback，`distributed_lock` 用 `SET nx ex`（原子），实现真实。
- `core/db_replication.py`：健康探测用真 `asyncio.open_connection`（真 TCP），真实（缺陷仅提主动作 B2-141）。
- `core/idempotent.py`：`generate_idempotency_key`（SHA-256 规范化）与中间件 `call_next` 链路真实（缺陷仅 B2-135）。
- `core/message_queue.py`：内存队列核心（priority/batch/DLQ/持久化/cleanup）真实。

### B2-24 core/ 采集器簇（linux/windows/macos/docker/k8s/cloud）—— 已通读
（linux_collector 1033 / windows_collector 123 / macos_collector 76 / docker_collector 161 / k8s_collector 260 / cloud_collector 246 ≈ 1,899 行；`collector.py` 已在 B2-9 读）

**B2-145 [中·安全] `linux_collector._ssh_execute` 关闭主机密钥校验 + 明文口令进 argv**
- 硬编码 `["ssh","-o","StrictHostKeyChecking=no","-o",f"ConnectTimeout={LINUX_SSH_TIMEOUT}","-p",str(port)]`；密码认证路径 `ssh_args = ["sshpass","-p",pwd] + ssh_args` → **口令出现在进程 argv（`ps` 可见）**且主机密钥不校验（MITM 可劫持采集与口令）。与 B2-10 的 `asyncssh.connect(known_hosts=None)` 同一安全问题面。

**B2-146 [中] `windows_collector.collect_windows_host` `finally` 引用可能未绑定的 `command_id`**
- `command_id = sess.run_command(...)` 在 try 内；`finally: sess.cleanup_command(shell_id, command_id)`。若 `run_command` 抛异常，`command_id` 未绑定 → `finally` 内 `UnboundLocalError`，**掩盖原始 WinRM 异常**。
- 另：Windows 采集**无失败冷却机制**（linux/k8s/docker 均有 *_HOST_COOLDOWN），不可达主机每次都重试，模式不一致。

**B2-147 [中] `k8s_collector` 多集群采集用全局 `config.load_kube_config()` + 线程池并发 → 跨集群串扰**
- `_load_api` 调 `config.load_kube_config(config_file=...)`（kubernetes 客户端**全局默认配置**）；`collect_all_k8s` 用 `ThreadPoolExecutor(max_workers=4)` 并发遍历 `K8S_HOSTS` → 多线程同时改写同一全局 kubeconfig，A 集群的采集可能瞬间对 B 集群发请求（无 per-cluster `ApiClient` 隔离）。

**B2-148 [低] `cloud_collector` 文档声称的冷却防护未在本模块实现**
- 模块 docstring：`使用 register_self_pid 防止误杀(基于 CLOUD_HOST_MAX_FAILURES/CLOUD_HOST_COOLDOWN_SEC)`；实际代码只 `register_self_pid()`（来自 command_guard），**无** CLOUD_HOST_* 冷却逻辑 → 文档描述的能力不存在（config 里确有该两项）。

**已核对：非缺陷 / 正例**
- `core/linux_collector.py`：真 SSH 批量合并 + **随机 nonce 防注入**（R1-4）+ 模块级 Semaphore + 失败冷却（N3-1）+ 结构化解析可降级——整体质量高（缺陷仅 B2-145 安全）。
- `core/docker_collector.py`：真 Docker SDK（`docker.DockerClient`+`ping()`+`container.stats(stream=False)`），CPU% 按 delta 精算，`client.close()` 收尾，走统一 `collect_with_post_processing`（`core/base/collector.py:226` 确认存在）。
- `core/k8s_collector.py`：真 `CoreV1Api.list_pod_for_all_namespaces` + `read_only` 默认 True + 截断告警 + 线程池超时（缺陷仅 B2-147 全局配置串扰）。
- `core/cloud_collector.py`：真 SDK（boto3 `get_metric_statistics` / azure `MetricsQueryClient` / aliyun `DescribeMetricListRequest`），统一结构 + Loki/SQLite 落库（缺陷仅 B2-148 文档）。
- `core/macos_collector.py`：诚实限定 localhost+Darwin，psutil 缺失即 `RuntimeError`，不伪造远端数据。

### B2-25 core/ 可观测客户端·日志·OTel 簇 —— 已通读
（prometheus_client 625 / prometheus_metrics 289 / loki_client 612 / loki_sink 21 / tempo_client 575 / elasticsearch_client 701 / es_logger 146 / otel_exporter 276 / structured_logging 356 / heartbeat 121 / metrics_converter 296 / observability_schema 133）

> 注：本批 `elasticsearch_client.py`(701) 尚未读完，登记于下一批 B2-26 补齐（其余 11 文件已逐行通读）。

**B2-149 [高] `loki_sink.push_to_loki` 是 no-op 桩，且它正是采集/修复链路的唯一 Loki 写路径**
- 全文仅：`logging.getLogger(__name__).info(f"{__name__}.push_to_loki invoked"); return None`。
- 使用方（grep 实证）：`core/base/collector.py:258-260`（docker/k8s 采集的统一后处理，把**每个快照** `push_to_loki(snapshot)`）、`core/cloud_collector.py:206`、`core/k8s_repair.py:243`（把修复结果 `result_record`）。
- 后果：所有采集快照 / 修复审计记录**声称"写入 Loki"实际被丢弃**（`cloud_collector` 文档明写"通过 push_to_loki 将结果写入 Loki"）。
- 对照：同为 Loki 集成，`core/loki_client.LokiClient` 只有**查询** API（query/query_range/series/labels，无 push），真正可用的 Loki 写入仅存在于 `core/structured_logging.setup_loki_logging`（loguru sink → `/loki/api/v1/push`，带 60s 冷却）。→ 项目内**两条 Loki 路径，一条真(日志)一条假(采集)**。

**B2-150 [中] `otel_exporter._record_gauge` 每次导出都新建 observable gauge → 仪表泄漏/重复注册**
- `_record_gauge` 内 `_meter.create_observable_gauge(name, callbacks=[_callback], ...)`：**每次 `export_snapshot()` 调用**（周期 10s）都对每个指标重复 `create_observable_gauge`，且 callback 闭包只 observe 单值。OTel 正确用法是 create 一次、callback 读当前值 → 现状导致 instrument 数量随运行时间线性增长（内存/重复上报）。
- `export_snapshot` 用 `span.__enter__()`/`__exit__()` 手工管理（非 `with`），异常时 finally 兜底尚可。

**B2-151 [中] `tempo_client` 时间戳单位与 limit 与 Tempo `/api/search` 不符**
- `search_traces` 传 `"start": int(start.timestamp()*1e9)`（**纳秒**），而 Tempo `/api/search` 的 start/end 为 epoch **秒**（或 RFC3339）。
- `get_service_dependencies` 请求 `limit=1000`（Tempo search 默认上限 20）→ 可能被拒或截断。
- （本机无 Tempo，运行时不可复现；结论基于 Tempo HTTP API 契约，标注待确认。）

**B2-152 [低] `es_logger.index_log` 兜底落 `data/es_fallback/*.ndjson`（未 gitignore）**
- ES 不可用时写入 `data/es_fallback/{index}.ndjson`；该目录**未被 git 跟踪也未列入 .gitignore** → 运行后工作树出现未跟踪产物（`data/` 下 11 个受控 JSON 已在册，见 B2-64）。
- 已核实：`elasticsearch` 9.5.0 已安装，`AsyncElasticsearch.search(..., body=...)` 的 `body` 形参在 9.5 仍存在 → `es_search_logs` 调用可行（非缺陷）。

**B2-153 [低] `observability_schema` 混用 pydantic v1 `@validator` 与 v2 `model_config`**
- 用 `@validator("env")`（v1 API，v2 已弃用）同时声明 `model_config = {...}`（v2 API）；`LogRecord.timestamp` 默认 `_dt.datetime.utcnow`（Python 3.12 弃用）。迁移/升级时会失效。

**已核对：非缺陷 / 正例**
- `core/prometheus_client.py`：真 httpx.AsyncClient + 真 Prometheus API（query/query_range/series/labels/targets/metadata/config/runtimeinfo/buildinfo），`health_check` 真打 buildinfo，非桩。
- `core/prometheus_metrics.py`：真 prometheus_client 注册表（Histogram/Counter/Gauge/Info），`queue_depth`/`active_sessions`/`websocket_connections` 与 bus 呼应。
- `core/loki_client.py` / `core/tempo_client.py`：真 HTTP 客户端 + LogQL/Trace 查询（缺陷仅 B2-151 时间戳）。
- `core/structured_logging.py`：真 JSON 结构化日志 + 上下文注入 + **真 Loki sink**（批推送+冷却），是 Loki 写入的正例。
- `core/heartbeat.py`：真 Prometheus Gauge + asyncio 后台心跳任务（含 dummy 兜底）。
- `core/metrics_converter.py`：真 Prometheus 文本格式转换（名称/标签消毒、转义、双向解析）。
- `core/otel_exporter.py`：真 OTel SDK（gRPC OTLP Metric/Span exporter + PeriodicExportingMetricReader），缺陷仅 B2-150。

### B2-26 core/ 可观测客户端补遗 —— 已通读
（elasticsearch_client 701）

**已核对：非缺陷（同名族除外）**
- `core/elasticsearch_client.py`：真 httpx.AsyncClient + 真 ES REST（_search/_count/_doc/_cluster/health/stats/base64 Basic Auth），health_check 按 green/yellow 判定，实现真实。
- 备注：ES 有**两套客户端**——本模块（httpx REST）与 `core/es_logger.py`（elasticsearch-py `AsyncElasticsearch`），同名域双实现（并 B2-115/136/140 模式）。

### B2-27 core/ 错误处理/异常体系簇 —— 已通读
（error_handler 679 / error_handling 259 / error_handling_logging 709 / exception_handler 227 / api_error 123 ≈ 1,997 行）

**B2-154 [高·架构] 全项目存在 **4 套互不兼容的异常体系**（同名类 ×4）**
- `class AIOpsException`：`error_handler.py:77`（severity+category 枚举）、`error_handling.py:58`（ErrorCode 枚举 GEN_/AI_/DB_）、`exception_handler.py:22`（error_code:str+status_code）、`error_handling_logging.py:113`（severity+category+error_id）。
- `ValidationError`/`DatabaseError`/`AuthenticationError`/`AuthorizationError` 在 `error_handler` 与 `error_handling` **各定义一次**；`DatabaseException`/`AuthenticationException`/`ValidationException` 在 `exception_handler` 与 `error_handling_logging` **各定义一次**。
- `ErrorHandler` 亦**双实现**：`error_handler.ErrorHandler`（同步、线程告警）与 `error_handling_logging.ErrorHandler`（async、deque 记录）。
- 后果：`except AIOpsException` 只能捕获其中一套；跨模块抛/捕会漏接。错误码亦分三套（`error_handling.ErrorCode`=GEN_1000… / `api_response_standard.ErrorCode` / `api_error.APIErrorCode` 纯字符串常量）。→ 最严重的“同名族并存”实例。

**B2-155 [高] `core/error_handler.py` 模块导入即 `ERROR_HANDLER = ErrorHandler()` → 全局 `logger.remove()` + 起守护线程**
- 文件末 `ERROR_HANDLER = ErrorHandler()`（第 679 行）；`__init__` 内 `self._configure_logging()` 调 `logger.remove()`（第 233 行，loguru **全局**移除所有 handler）并重建 stdout/errors.log/structured.json，随后 `_start_alert_processor()` 启 `threading.Thread(daemon=True)`。
- 后果：**任何 import core.error_handler 都会清空应用 loguru 配置并启动后台线程**（除非设 `DISABLE_ERROR_HANDLER=true`）。与 `structured_logging.setup_logging`（也 `loguru_logger.remove()`）、`error_handling_logging.StructuredLogger._configure_loguru`（也 remove）三方竞争全局日志配置。

**B2-156 [中] `error_handling_logging._handle_aiops_exception` 的“自定义 recovery handler”路径恒为死代码**
- `handler = self.error_handlers.get(type(Exception(error_record.error_message)))` —— `type(Exception(msg))` **恒为 `Exception`**，而 `_register_default_handlers` 只注册 `AIOpsException/NetworkException/...`，从不注册裸 `Exception` → `handler` 恒 None，recovery 分支永不执行。
- 另 `_find_error_handler` 有**两个完全相同的 for 循环**（第二个不可达重复）。

**B2-157 [中] main.py 对 `Exception` 注册 **3 次** 处理器，且 `setup_exception_handlers` 再覆盖一次**
- `main.py:1078 app.add_exception_handler(Exception, general_exception_handler)` + `main.py:1081 @app.exception_handler(Exception) global_exception_handler`（装饰器又注册一次）+ `main.py:1351 setup_exception_handlers(app)`（`exception_handler.py` 内部第三次 `add_exception_handler(Exception, generic_exception_handler)`）。FastAPI 用 dict 存储，**最终生效者取决于注册顺序**，前两者为死代码；`HTTPException`→`api_error_handler` 与 `RequestValidationError`→`validation_error_handler` 亦与其它体系并存。

**B2-158 [低] 告警外发为日志桩**
- `error_handler._send_alert`（注释 `# Here you could add integration with notification systems`）与 `error_handling_logging._send_error_alert`（注释 `这里可以集成通知系统`）均只 `logger.critical(...)`，无真实通知通道（承 B2-51/“告警外发类”模式）。

**已核对：非缺陷**
- `core/api_error.py`：`api_error_handler`/`validation_error_handler`/`general_exception_handler` 三处理器实现真实（统一 `APIResponse.error` + 脱敏 `details`），是可用的 HTTP 层实现（缺陷仅是与其他 3 套并存/重复注册）。
- `core/error_handling.py`：异常类 + 标准错误响应字典 + 日志工具，实现自洽（缺陷仅体系重复）。

### B2-28 core/ API 响应/分页/追踪簇 —— 已通读
（api_response 118 / api_response_standard 442 / api_response_middleware 107 / pagination 131 / request_tracking 153 / api_deprecation 38 / api_performance 37 ≈ 1,026 行）

**B2-159 [高·架构] 响应封装存在 **2 套 `APIResponse` + 3 套包装中间件**，仅 1 套生效**
- `APIResponse`：`core/api_response.py`（静态方法，产出 `{success,message,data,timestamp}`）vs `core/api_response_standard.py`（`Generic[T]` 类，产出 `{success,timestamp,request_id,data,error,error_code}`）→ **响应 schema 不兼容**。
- 包装中间件三份：`api_response.api_response_middleware`(函数，**仅测试引用**)、`api_response_standard.APIResponseMiddleware`(纯 ASGI，**全项目未被注册**，死代码)、`api_response_middleware.APIResponseMiddleware`(BaseHTTPMiddleware，经 `main.py:1017 setup_api_response_middleware` 生效)。三者逻辑都是"把成功的 JSON body 再包一层 `success`"。
- `PaginationParams`/`PaginatedResponse` 亦两套（`api_response_standard` vs `pagination.py`）。

**B2-160 [中] `api_response_middleware.APIResponseMiddleware.dispatch` 重包响应时**丢弃所有响应头**
- `return JSONResponse(content=wrapped_body, status_code=response.status_code)` —— 未传 `headers=response.headers`。凡命中"`/api/` 且 JSON 且非已包装"的响应，`X-Request-ID`、CORS、`Set-Cookie` 等头**全部丢失**（对照 `api_response.api_response_middleware` 版本有 `headers=dict(response.headers)`，此版本漏了）。

**B2-161 [中] `pagination.PaginationHelper.apply_pagination` 属性名拼写错误 → 排序即崩**
- `sort_column = getattr(query.column_described, params.sort_by, None)` —— SQLAlchemy `Query` **无 `column_described`**（实测 `dir(Query)`：`column_described`=False、`column_descriptions`=True）→ 只要传 `sort_by` 就 `AttributeError`。
- 另：`query.count()` + `offset().limit().all()`（计数与取数双查），且面向**同步** `Query`，与主体 async 引擎不匹配。

**B2-162 [低] `api_performance` 统计无界增长 / `api_deprecation` 时区不匹配**
- `API_PERFORMANCE_STATS[func_name].append(duration)` 无上限（内存随调用线性增长）；`api_deprecation.deprecation_middleware` 若 `sunset_date` 为 naive datetime，`info["sunset_date"] - datetime.now(timezone.utc)` 抛 `TypeError`。

**已核对：非缺陷**
- `core/request_tracking.RequestTrackingMiddleware`：标准实现（ContextVar + 请求头透传 + `response.headers` 回写），真实可用。
- `core/api_response.py`：`APIResponse.success/error` 与中间件实现自洽（缺陷仅 B2-159 重名体系）。

### B2-29 core/ 校验·治理·助手·内容审查·上下文压缩簇 —— 已通读
（type_validation 405 / input_validator 361 / api_governance 352 / api_helpers 370 / content_moderation 174 / context_compression 239 ≈ 1,901 行）

**B2-163 [中] `api_helpers.get_operator_ip` 只取 `request.client.host`，绕过项目自身可信代理逻辑 → 审计记录错误来源 IP**
- `return request.client.host if request.client else "unknown"` —— 不解析 `X-Forwarded-For`，也不使用 `config.TRUSTED_PROXY_COUNT`（该项目已有 `_get_real_client_ip`）。部署在反代/网关后，所有审计/操作人 IP 记为**代理地址**，与统一可信代理口径冲突（关联项目约束 TRUSTED_PROXY_COUNT）。

**B2-164 [中] `api_governance` 注册表静态且使用统计永不更新**
- `_setup_default_versions()` 硬编码 3 个端点（`/api/v1/alerts` GET/POST、`/api/v1/metrics` GET）为占位注册（真实路由有几百个，不一一对应）；`record_endpoint_usage()` **全项目无调用点**（grep 仅 `setup_api_governance` 被 `lifecycle_manager`/`main.py` 调用）→ `get_usage_stats()` 的 `usage_count`/`last_used` **恒 0/None**，"API 治理使用统计"名不副实。
- 与 `core/api_deprecation.py`（另一套弃用登记 DEPRECATED_ENDPOINTS）概念重复，同样未被请求链路调用。

**B2-165 [低] `content_moderation` 屏蔽词含高频运维术语 → 误伤风险**
- `_HARMFUL_BLOCKLIST` / `_SHELL_LIKE_PATTERNS` 含 `"password"`、`"api key"`、`"private key"`、`"subprocess"`、`"os.system"`、`"killall"` 等，`moderate_content` 对**所有 AI 输入/输出**做子串命中即拒（threshold=1）。合法运维文本（如"rotate the database password"）会被判违规。`$(...)` 正则还会命中普通告警文本。

**已核对：非缺陷**
- `core/type_validation.py`：`RuntimeTypeValidator`（含 Optional/List/Dict/dataclass 递归校验）、`validate_types`/`validate_return_type`/`validate_request` 装饰器实现真实。
- `core/input_validator.py`：SQL/XSS/命令注入/路径遍历正则 + HTML 转义 + 递归 sanitize，实现真实（正则启发式，非桩）。
- `core/api_helpers.py`：`handle_api_error`（截断 detail）、`validate_required_fields`、`with_error_handling` 装饰器、`find_host_config`/`validate_hostname` 实现真实（缺陷仅 B2-163）。
- `core/context_compression.py`：真实 token 预算压缩（依赖 `core/ai/token_budget.estimate_tokens` 确认存在），保护段/摘要/截断/中间向外删除策略完整。

### B2-30 core/ 告警智能·任务分解·审计簇 —— 已通读
（alert_intelligence 614 / intelligent_alert_analyzer 553 / intelligent_task_decomposer 569 / service_monitoring_manager 456 / chat_command_handler 371 / external_api_audit 441 / security_audit_system 493 / alert_rules 207 / audit_logger 197 / anomaly_engine 126 / priority_engine 48 / metadata_engine 161 / oncall_adapter 205 / slack_adapter 216 / teams_adapter 158 ≈ 4,815 行）

**B2-166 [高] `chat_command_handler._get_user_roles` 用**子串**判定角色 → 用户名含 "admin" 即获管理员**
- `lowered = (user_id+user_name).lower(); if "admin" in lowered: roles.add("admin")`（同理 oncall/sre）。任意用户名包含子串 "admin"（如 `badadmin`、`administrator_x`、`admin-readonly`）→ 自动获得 admin 角色，可放行 PAUSE/APPROVE/REJECT/ASSIGN 等高风险聊天指令。→ **聊天指令权限提升**。

**B2-167 [高] `intelligent_alert_analyzer.predict_alert_trends` 从未 `fit()` 即 `predict()` → 恒失败**
- `# 训练模型` 之后是注释 `# (简化实现，实际需要更复杂的数据准备)`，**没有 `model.fit(df)`**，紧接着 `future = model.make_future_dataframe(periods=24)` + `model.predict(future)`。对未训练的 Prophet 调 predict 必抛异常 → 被 `except` 吞并 `return None`。该"趋势预测"永远返回 None。

**B2-168 [中] `intelligent_alert_analyzer` 的抑制/历史/拓扑均为空实现**
- `_matches_suppression_rule` 的 `time_window` / `max_frequency` 分支都是 `pass`（未实现），仅支持 `pattern` 子串；`_load_historical_patterns`/`_build_topology_graph` 仅 `logger.info` 后 `# 实现…逻辑` 空转 → 依赖 `alert_patterns`（永不填充）的降噪与依赖 `topology_graph` 的拓扑关联在默认运行下失效。

**B2-169 [中] `intelligent_task_decomposer._llm_decompose` 把 LLM 返回的 **dict** 当 **str** 送 `re.search` → 静默降级为硬编码 3 任务，却仍标 `decomposition_method="llm"`**
- `EnhancedLLMRouter.generate()`（`core/ai/llm_router/enhanced_router.py:261`）返回 `Dict{content,model,usage}`；`_parse_llm_response(response, ...)` 却 `re.search(r'\{[\s\S]*\}', response)` → 对 dict 调 `re.search` 抛 `TypeError` → 被同函数 except 捕获 → 返回 `_create_fallback_tasks`（写死的 Analysis/Execution/Verification 三步）。最终 `DecompositionResult.decomposition_method="llm"` 名不副实。

**B2-170 [中] `security_audit_system.generate_audit_report` 非 json 格式时 `report_path` 未绑定 → UnboundLocalError**
- 仅 `if format == "json":` 分支内赋 `report_path`；`format="csv"` 时跳过该分支，末尾却 `logger.info(f"...: {report_path}")` + `return str(report_path)` → `UnboundLocalError`。

**B2-171 [中] `external_api_audit` 装饰器取参方式与实际调用不匹配 → 审计记录字段为空**
- `audit_httpx_call` 从 `kwargs.get("method")`/`kwargs.get("url")`/`kwargs.get("content")` 取值，但项目内 httpx 调用多为**位置参数**（`self._client.request("GET", url, params=..., json=...)`）→ 记录恒 `method="GET"`、`url=""`、`body_size=0`，审计形同虚设。且日志仅存**内存 deque**（无落盘）。

**B2-172 [中·架构] 审计实现共 **4 套**并存**
- `core/audit_logger.py`（仅 `logger.info` 落文本，自承 "In production, this would also write to a dedicated audit database"）、`core/audit_service.py`（真 SQLAlchemy AuditLog，见 B2-15）、`core/security_audit_system.py`（jsonl 落盘 + 策略/报表）、`core/external_api_audit.py`（内存 deque）。四套事件模型/严重级别/存储各异（承 B2-154 异常体系模式）。

**B2-173 [低] `metadata_engine.amundsen_register_table` 无客户端时仍返回 True（伪成功）**
- `if AmundsenTable is None: logger.warning(...); return True` —— 未注册也回报成功；且函数末尾 `return True` 无任何注册动作（Amundsen 路径整体为占位）。

**B2-174 [低] `alert_intelligence` 用内建 `hash()` 造特征 / `intelligent_alert_analyzer` 用 `hash()` 造聚合 ID**
- `_extract_alert_features` 用 `hash(host)%100`/`hash(metric)%100` 作 ML 特征；`_create_cluster_aggregation` 用 `hash(str([...ids]))` 作 `agg_cluster_<hash>` → 跨进程/重启不确定（同 B2-62/130 模式）。另 `alert_intelligence` 头部称 "Prophet/**LSTM**"，全文件无 LSTM 实现（能力声明 > 实现）。

**已核对：非缺陷 / 正例**
- `core/anomaly_engine.py`：真 Z-score 检测（均值/标准差/阈值/置信度/时间戳归一），实现真实。
- `core/priority_engine.py`：真 config 驱动 `compute_sla_score`（含非法值回退）。
- `core/alert_rules.py`：真规则 CRUD + `evaluate_all_rules`（按 metrics 映射）+ 冷却；实现真实（仅支持 `>=` 阈值，无 `<`）。
- `core/service_monitoring_manager.py`：真指标/统计（mean/median/p95/p99/stddev）+ 规则告警 + 冷却 + z-score 异常；实现真实（数据进程内、无持久化）。
- `core/oncall_adapter.py` / `slack_adapter.py` / `teams_adapter.py`：真 HTTP 集成（Slack HMAC `compare_digest` 验签正确、Teams Webhook 卡片、PagerDuty/Opsgenie 外呼 + 本地 JSON 回退）。
- `core/audit_logger.py`：trace_id 上下文传播 + 结构化审计事件字段完整（仅落文本，见 B2-172）。

### B2-31 core/ 配置簇 —— 已通读
（config_manager 482 / config_validation 471 / config_models 370 / unified_config 128 / environment_config 211 / constants 23 / platform_strategies 226 / service_worker_config 90 / security_config 250 ≈ 2,251 行）

**B2-175 [中] `security_config.validate_tls_certificates` 因 aware/naive 混比 → 证书校验恒失败（已实测）**
- `now = datetime.now(timezone.utc)`（aware）与 `cert.not_valid_before` 比较；cryptography 50.0.1 下 `not_valid_before` 返回**naive**（实测 `tzinfo=None`）→ `TypeError: can't compare offset-naive and offset-aware datetimes`，被 except 吞 → 恒返回 `{"valid": False, "reason": "Certificate validation failed: ..."}`。应改用 `not_valid_before_utc`。
- 另 `setup_enterprise_security` 中 `results["timestamp"]` 实际填 "success"/"error"（字段名与语义不符）。

**B2-176 [中·架构] 配置体系三套 `ConfigManager`/`ConfigValidator` 并存**
- `core/config_manager.ConfigManager`（pydantic-settings 真实现，含 dotenv/watchdog/热重载/回滚）、`core/unified_config`（再导出同一套）、`core/environment_config.EnvironmentConfigManager`（**自建 `ConfigManager()` 实例**，与全局 `config_manager` 并存 → 状态可能分叉）、`core/config_validation.ConfigValidator`（与 config_manager 的 `ConfigValidator` 同名不同语义）。`config_validation` 又从 `environment_config`→`unified_config` 取 `AppConfig/Environment`，依赖链绕。

**B2-177 [低] `config_validation._validate_ai_config` 建议项过时**
- 提示 `suggestion="Set OPENAI_API_KEY environment variable"`，与实际 AI 配置（`AI_API_KEY`/MiniMax，见 config）不符。

**已核对：非缺陷 / 正例**
- `core/config_manager.py`：真 pydantic-settings 加载（.env/env/JSON/YAML 多源 + 生产 JWT_SECRET 强校验 + CORS 逗号解析）、`save_config` 落盘 chmod、热重载（watchdog）、`rollback_config`、`_record_config_version`（有界历史）——实现完整。
- `core/platform_strategies.py`：真策略模式（Windows/Linux/Docker/K8s 各自脚本/执行/历史），消除 if/elif；实现真实（Windows 端点桩见 B2-10）。
- `core/constants.py` / `core/eager_loading.py`：常量/Documented 空配置，非缺陷。
- `core/service_worker_config.py`：真 SW 脚本生成（install/activate/fetch）。

### B2-32 core/ 缓存簇 —— 已通读
（cache_manager 360 / caching_strategy 377 / enhanced_caching 348 / frontend_cache_strategy 276 / connection_pool_optimization 239 / smart_cache_strategy 29 / eager_loading 13 ≈ 1,642 行）

**B2-178 [中] `enhanced_caching.setup_enhanced_caching` 缓存预热写入**伪造数据**且忽略项目 Redis 配置**
- 硬编码 `RedisCacheBackend(host="localhost", port=6379 ...)`（不使用 `config.REDIS_HOST/PORT/REDIS_URL`）；注册的 warmup 任务是内置假数据 `{"system:config": {"version":"1.0.0","features":[]}, "system:metrics": {"cpu":0,"memory":0}}` → 预热把**编造值写入缓存**，污染真实缓存空间。

**B2-179 [低/中] `enhanced_caching.CacheInvalidationStrategy.invalidate_by_time` 未实现**
- 函数体仅 `logger.warning("Time-based invalidation not yet implemented")` → 声明的时间维度失效不存在。

**B2-180 [中] `smart_cache_strategy.get_cache_tier` 恒返回 "cold"**
- `access_count = 0  # 需要从缓存获取` 写死为 0 → 永远 <10 → 恒 "cold"；`get_ttl` 的 `data_size` 参数被忽略。缓存分层策略形式存在、逻辑恒为冷数据。

**B2-181 [低] `cache_manager` 用 `print` 而非 logger 记日志**
- `_initialize_redis`/`get`/`set`/`delete`/`get_cache_stats` 等以 `print(...)` 输出 → 不进结构化日志/不落盘；`cache_key_generator` 用 `hashlib.md5`（FIPS 环境告警）。

**已核对：非缺陷**
- `core/cache_manager.py`：真 Redis 后端（`redis.from_url` + ping + setex + 模式失效 + keyspace 统计 + 策略 TTL 表）——实现真实（缺陷仅 B2-181 日志方式）。
- `core/caching_strategy.py`：真内存缓存（TTL/过期/容量淘汰/命中率/装饰器/模式失效），实现自洽。
- `core/connection_pool_optimization.py`：真 SQLAlchemy async engine 池监控（`size/checkedin/checkedout/overflow`、`SELECT 1` 健康探测、按负载给建议），实现真实。
- `core/enhanced_caching.RedisCacheBackend`/`CacheWarmer`：Redis 后端与预热框架真实（缺陷仅 B2-178 载荷）。

### B2-33 core/ 备份·灾难恢复·证书·模块健康簇 —— 已通读
（chaos_engineering 634 / disaster_recovery_drill 406 / dr_scenarios 380 / service_discovery_manager 428 / system_resource_optimizer 364 / task_scheduler 310 / multi_tenant 345 / multi_tenant_quota 308 / tenant_engine 258 / disaster_recovery 291 / certificate_manager 220 / backup_manager 181 / module_health_check 134 / module_dependencies 35 / monitoring_system_integrator 271 ≈ 4,565 行；本批先记 backup/DR/cert/health 子集；chaos/scheduler/tenant/discovery/resource/monitoring 见 B2-33-续（已补齐））

**B2-182 [高] `backup_manager._run_walg` 从不检查退出码 → 备份/恢复失败也报成功**
- `_run_walg` 执行后仅按 `isinstance(result, dict)` 记日志，**末尾无条件 `return True`**（仅异常才 False）。`backup_database()`/`restore_latest_backup()` 直接透传该布尔 → wal-g 返回非 0（备份失败）时 `backup_database()` 仍返回 True。→ `api/database_advanced_router.py:593` 依赖此结果，会向调用方/前端报"备份成功"。

**B2-183 [中] `backup_manager` 在模块级对 `DATABASE_URL` 强校验，非 postgres 部署 import 即抛**
- 模块顶层 `if not POSTGRES_URL.startswith(("postgresql://","postgresql+asyncpg://")): raise ValueError(...)` → 若部署使用 sqlite/其他 URL，则 `import core.backup_manager` 直接抛错（当前默认 URL 为 postgres，故本机可导入；但脆弱）。

**B2-184 [中] `disaster_recovery_drill` 全部检查恒 True，演练"必定成功"**
- 文件头已自承 `# TEST ONLY: ... simulations for testing purposes`；其 `_check_standby_database/_perform_database_failover/_verify_data_consistency/_check_service_health/_restart_service/...` **全部直接 `return True`**（`_detect_data_corruption` 恒 False）。
- 且 `_data_corruption_drill` 的 `success = restore_result and integrity_check` **忽略 `corruption_detected`**。→ `run_drill(...).success` 恒 True（除异常），`get_drill_stats` 成功率恒 100%。属"已声明为仿真"，但与 `dr_scenarios`（真 Chaos Mesh，见下）形成真假并存。

**B2-185 [低] `disaster_recovery.backup_configuration`/`restore_database` 用 `print` 且 restore 硬编码 `aiops_agent.db`**
- 失败分支一律 `print(...)`；`restore_database` 忽略传入 backup 对应的目标库，固定恢复到 CWD 的 `aiops_agent.db`（与 `_database_url()` 解析出的库不一致）。

**已核对：非缺陷 / 正例**
- `core/certificate_manager.py`：**真实 X.509 全流程**——RSA/ECDSA/Ed25519 密钥生成、SAN+BasicConstraints+KeyUsage(EKU SERVER_AUTH)+SKI 扩展、`random_serial_number`、PEM 序列化、AES-256-GCM 私钥封存（`seal/unseal_private_key` + 无 ENCRYPTION_KEY 时显式告警）。高质量。
- `core/dr_scenarios.py`：**真实** Chaos Mesh 注入（PodChaos/IOChaos，`CHAOS_DB_SERVICE` 等 env 指定目标，`DR_EXECUTE_ENABLED` 门控，缺目标/未知类型**显式抛错**而非假成功），恢复时逐个 delete 实验。质量高。
- `core/disaster_recovery.py`：`backup_database` 真 `sqlite iterdump` / `pg_dump`（PGPASSWORD env、非 0 退出即删档抛错）、`backup_redis` 真 BGSAVE 轮询 + RDB 复制；实现真实（缺陷仅 B2-185 的 print/硬编码）。
- `core/module_health_check.py`：真 `SELECT 1`/Redis ping/AI router 探活。
- `core/module_dependencies.py`：静态依赖图 + `validate_initialization_order` 自洽。

### B2-33-续（欠账补齐）：chaos / scheduler / tenant / discovery / resource / monitoring 簇 —— 已通读
> 补齐 B2-33 节头声明为「见下批」而从未落笔的 8 个文件；本次全部 `file_read` 整文逐行读取（非抽样、非 grep、无遗漏；chaos_engineering 634 行分两段补齐首尾）。
（chaos_engineering 634 / service_discovery_manager 428 / system_resource_optimizer 364 / multi_tenant 345 / task_scheduler 310 / multi_tenant_quota 308 / monitoring_system_integrator 271 / tenant_engine 258 ≈ 2,918 行）

**B2-186 [高] `core/service_discovery_manager.py` 健康检查为随机模拟，`HealthCheckConfig` 全字段失效**
- `health_check()`（:312-341）：`await asyncio.sleep(0.1)  # Simulate network delay` + `is_healthy = _random.random() > 0.1  # 90% chance of being healthy`（注释自承 `# Simulate health check (in real implementation, this would make HTTP/gRPC call)`、`# For demonstration, randomly mark as healthy`）。
- 后果：实例健康状态由随机数决定；`HealthCheckConfig.health_check_path`(`/health`) / `timeout_seconds` / `unhealthy_threshold` / `healthy_threshold`（`interval_seconds` 仅用于 loop sleep）**全部从未被读取** → "Enterprise-grade ... health management" 无任何真实探活。
- 且 `discover_service()` 仅返回 `status==HEALTHY` 的实例，而 `register_service()` 注册实例默认 `UNKNOWN` → 未跑健康检查前发现集恒为空；负载均衡（round_robin/least_connections/weighted/random 算法本身为真）作用在随机健康集上。

**B2-187 [中] `core/monitoring_system_integrator.py` 告警规则只实现 CPU 一条，内存/API 规则为死配置**
- `_setup_default_alert_rules()` 注册 3 条：`high_cpu_usage`、`high_memory_usage`(`system_memory_percent > 85`)、`high_api_error_rate`(`api_error_rate > 0.05`)。
- `evaluate_alert_rules()`（:229-249）仅 `if "cpu" in rule["condition"].lower(): cpu_value=... >80` 一个分支（注释自承 "简化的规则评估 实际应该解析condition表达式并评估"）→ 内存、API 错误两条规则**永不触发**；`rule["duration"]` 亦未使用；CPU 阈值 `>80` 为硬编码（未解析 condition）。

**B2-188 [中·架构] 三套彼此独立的租户体系并存，模型/存储互不相通**
- `core/multi_tenant.py`：进程内 dict（`_tenant_configs`/`_tenant_users`）+ ContextVar 上下文；`Tenant`/`create_tenant`/`get_tenant`；**无持久化**，重启即失。
- `core/tenant_engine.py`：`data/tenants.json` JSON 持久化 + `threading.RLock`；另一套 `Tenant`（含 `Quota/Usage/Billing`）与 `create_tenant/get_tenant/update_tenant`（同名不同语义，且 `Tenant` 与 multi_tenant 的 `Tenant` 同类名冲突）。
- `core/multi_tenant_quota.py`：又一套进程内 dict（`tenant_profiles`），`TenantQuotaProfile` + `ResourceQuota`（plan 模板），与 `tenant_engine.Quota` 概念重叠但**无任何对接**：tenant_engine 的 usage 不经 quota_manager 校验，quota_manager 的 used 也不来自 tenant_engine。
- 影响：无统一租户注册表；同名函数/类按导入路径语义不同；配额、用量、上下文与实际租户数据互不联通。

**B2-189 [中] `core/multi_tenant_quota.py` soft/hard 限额与 period 全部失效**
- `ResourceQuota.soft_limit=int(limit*0.8)`、`hard_limit=int(limit*1.1)`、`period=timedelta(days=1)` 定义后**在任何判断中均未被引用**：`check_quota`/`consume_quota` 只用 `quota.limit`（→ soft 预警从不触发；hard 允许的 110% 反被 100% 卡死，即 `hard_limit` 语义与 `limit` 冲突）。
- `period` 未驱动自动重置 → `used` 永久累加、无按周期归零（仅手工 `reset_usage`）。
- `upgrade_tenant_plan()` 经 `create_tenant_profile()` **重建 profile 并把 used 清零**（升级即丢用量），返回前赋值的 `new_profile` 亦未使用（F841）。
- `check_quota`/`consume` 在无 profile 时 `return True`（fail-open）：未建 profile 的租户=无限额。

**B2-190 [中] `core/task_scheduler.py` 启用 Temporal/Prefect 反而使任务不执行**
- `_InMemoryScheduler`（fallback）真执行（`create_task(_run_interval/_run_cron)`）。
- `TemporalWrapper.schedule()` / `PrefectWrapper.schedule()` **仅 `self._tasks.append({...})`** 记录元数据（注释 "这里仅记录任务信息，实际执行交由 Temporal Worker (outside scope)"）→ 一旦环境装载 temporalio/prefect，`TaskScheduler.schedule_task` 退化为**完全不执行**的登记操作，与未装时行为相反。
- 附带：`_InMemoryScheduler._get_loop()` 在无运行中 loop 时 `new_event_loop()+set_event_loop()` 后 `loop.create_task(...)` 但**无处 run** → 同步入口下 interval/one-off 任务不会真正运行（仅 async 运行中调用才生效）；本地 cron 只支持 `*/N * * * *` 分钟级，其它样式退化为固定 60s。

**B2-191 [低-中] `core/system_resource_optimizer.py` 汇总状态可误报 "complete"**
- `run_comprehensive_optimization()` 以 `if result and "error" not in result` 统计成功数，但 `results["memory_optimization"]` 结构为 `{"analysis": {...}, "optimization": {...}}`——子项返回 `{"error": ...}` 时顶层 dict **无 `error` 键** → 仍计为成功 → `overall_status` 可报 "complete"，掩盖子操作失败。
- `network_optimization_enabled` 硬编码 `True`；`optimize_network()` 仅读 `psutil.net_io_counters/net_connections` 并返回**静态建议文本**，无任何网络优化动作（注释 "Network optimization is handled at infrastructure level"）。

**B2-192 [低] `core/chaos_engineering.py` 实验 success 恒 True（健康/连通结果未并入判定）**
- 各 `_inject_*`/`_limit_*`/`_partition_*`/`_fail_*` 末尾一律 `return {"success": True, ...}`；`_check_system_health()`/`_check_network_connectivity()`/`_verify_service_degradation()` 结果被记录进 metrics 却**不参与 success**（仅异常才 False）→ `run_experiment().success` 除异常恒 True。

**已核对：非缺陷 / 正例**
- `core/chaos_engineering.py`：**真实 Chaos Mesh** 注入后端（`CustomObjectsApi.create/delete_namespaced_custom_object` + `asyncio.to_thread` 卸载阻塞；NetworkChaos/PodChaos/StressChaos/IOChaos 规格完整；`_resolve_target` 缺目标显式抛错；辅助探活为真实 `httpx` GET `/health`）——注入链路真实（缺陷仅 B2-192 判定语义）。
- `core/service_discovery_manager.py`：负载均衡算法（round-robin/随机/最少连接/加权）为真实实现；除 `health_check` 外逻辑自洽（缺陷仅 B2-186）。
- `core/tenant_engine.py`：JSON 持久化 + `os.chmod(600)` 收紧权限 + `RLock` 串行化，实现自洽（缺陷仅 B2-188 架构割裂；跨进程无锁）。
- `core/system_resource_optimizer.py`：内存/CPU 优化委托真实 `MemoryUsageOptimizer`/`CPUUsageOptimizer`（缺陷仅 B2-191 汇总语义与 network 桩）。
- `core/multi_tenant.py`：ContextVar 协程安全租户上下文，实现自洽（缺陷仅 B2-188 无持久化/割裂）。
