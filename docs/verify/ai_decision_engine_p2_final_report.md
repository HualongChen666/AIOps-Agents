# AI Decision Engine P0–P2 修复最终验证报告

> 生成时间：2026-07-26  
> 目标模块：`core/heal_graph.py`、`core/auto_heal.py`、`core/agent/executor.py`、`core/verifier.py`、`tests/test_auto_heal.py`、`tests/core/test_ai_decision_engine_fixes.py`

## 1. 修复范围总结

| 优先级 | 任务 | 关键改动 |
| --- | --- | --- |
| P0 | 接入 `heal_graph.run_heal` | `auto_heal.try_auto_heal` 调用 `run_heal` 并处理审批/失败/SLA 结果 |
| P0 | 上下文断裂 | `invoke_agent` 返回结构化 dict，传给 `runbook_generator` |
| P0 | 验证参数 | `apply_fix` 保存 `pre_snapshot`，`evaluate` 将其传给 `verify_repair` |
| P0 | 统一 `RiskLevel` | 统一使用 `core.command_guard.RiskLevel`（字符串值 safe/low/medium/high/blocked） |
| P0 | 命令失败回滚 | `apply_fix` 执行失败时设置 `verification = {"passed": False}` 触发 rollback |
| P1 | 自动执行/审批分流 | `apply_fix` 对 SAFE/LOW 自动执行，中高风险的命令进入待审批 |
| P1 | 补齐 verifier 策略 | 新增 `disk_usage`、`network_check`、`k8s_status` 验证策略及启发式策略选择 |
| P1 | 失败升级 | `try_auto_heal` 跟踪连续失败次数，超过阈值后 `escalated=True` |
| P1 | 冲突检测/锁/维护窗口 | `try_auto_heal` 检查 `HEAL_MAINTENANCE_MODE`、维护窗口、资源级 `asyncio.Lock` |
| P2 | RepairScriptLibrary fallback | `generate_runbook` 在 LLM runbook 生成失败/无效时回退到 `repair_script_library` |
| P2 | metrics/audit 可观测性 | `complete` 节点生成 `state.metrics`，引入 Prometheus counter |
| 兼容性 | langgraph checkpointing | `heal_graph._build_graph` 按 `graph.compile` 签名条件传递 `checkpointer` |
| 健壮性 | metrics_history | 对 `HISTORY_MAX_POINTS` 被设为非整数时 fallback 到 60 |

## 2. 修改的核心文件

- `core/verifier.py`：新增/修复 `disk_usage`、`network_check`、`k8s_status` 验证策略与策略选择逻辑。
- `core/auto_heal.py`：新增 `try_auto_heal`（失败升级、维护窗口、分布式锁）；`approve_repair` / `reject_repair` / `get_pending_approvals` 改为 async；返回原始 `alert_id` 类型；补充 `import os`。
- `core/heal_graph.py`：`generate_runbook` 增加 RepairScriptLibrary fallback；`complete` 增加 metrics；条件性 `checkpointer` 编译；修复 `evaluate` 对 `verified=None` 的归一化。
- `core/agent/executor.py`：`execute_task` 使用 `tool_executor.execute_with_auto_selection`。
- `core/metrics_history.py`：防御非整数 `maxlen` 默认值。
- `tests/core/test_ai_decision_engine_fixes.py`：新增 P0–P2 回归测试。
- `tests/test_auto_heal.py`：解除对 `approve_repair` / `reject_repair` / `get_pending_approvals` 的同步调用，增加 async fixture patch。
- `tests/core/test_verifier.py`：移除 `@pytest.mark.skip`。
- `tests/core/test_heal_graph.py`：移除 `@pytest.mark.skip`。

## 3. 验证命令与结果

### 3.1 编译检查

```powershell
python -m py_compile core/verifier.py core/auto_heal.py core/heal_graph.py core/agent/executor.py core/metrics_history.py tests/core/test_ai_decision_engine_fixes.py tests/test_auto_heal.py tests/core/test_verifier.py
```

**结果：全部通过（exit 0）**

### 3.2 修复目标专项回归测试

```powershell
python -m pytest tests/core/test_ai_decision_engine_fixes.py -n0 --no-cov -q
```

**结果：10 passed, 1 warning**

覆盖：RiskLevel 统一值、verifier disk/network/k8s 策略、`try_auto_heal` 维护窗口/失败升级/资源锁、`heal_graph` RepairScriptLibrary fallback、`complete` metrics。

### 3.3 受影响的官方测试文件（合并）

```powershell
python -m pytest tests/core/test_heal_graph.py tests/test_auto_heal.py tests/core/agent/test_executor.py tests/core/test_verifier.py tests/core/test_ai_decision_engine_fixes.py -n0 --no-cov -q
```

**结果：92 passed, 1 warning**

日志：`p2_combined_tests.log`

### 3.4 分项验证

- `tests/test_auto_heal.py`：**11 passed, 1 warning**（`auto_heal_tests.log`）
- `tests/core/test_verifier.py`：**2 passed, 1 warning**（`verifier_tests.log`）
- `tests/core/agent/test_executor.py`：**67 passed, 1 warning**（历史记录）
- `tests/core/test_heal_graph.py`：**2 passed**（历史记录）

## 4. 关键修复点验证摘录

- `verifier._select_strategy` 对 `disk_high_script` 返回 `disk_usage`，`flush_dns` 返回 `network_check`，`k8s_pod_crash` 返回 `k8s_status`。
- `heal_graph.generate_runbook` 在 LLM runbook 返回 `{"success": False}` 时，成功回退到 `cpu_high_script`，`state.runbook["source"] == "repair_script_library"`。
- `heal_graph.complete` 生成的 `metrics` 包含：`status`、`fix_applied`、`commands_executed`、`verification_strategy`、`verification_passed`、`error`。
- `try_auto_heal` 连续 2 次失败（阈值 2）后返回 `escalated=True` 并要求人工介入。
- `HEAL_MAINTENANCE_MODE=true` 时 `try_auto_heal` 直接返回 `maintenance=True` 并跳过修复。

## 5. 结论

P0、P1、P2 修复建议均已在目标模块实现，受影响的官方测试文件及新增回归测试全部通过（**92 passed**），`py_compile` 通过。由于完整 `tests/core` 套件运行时间过长（ thousands of tests），已采用受影响的专项测试 + 新增回归测试完成验证。未发现与本次修复相关的失败。

---
*注：日志文件 `p2_combined_tests.log`、`p2_final_tests.log`、`auto_heal_tests.log`、`verifier_tests.log` 均位于仓库根目录，可被复现。*
