# CodingSubAgent增强功能故障排查手册

## 常见问题

### 1. 导入错误

**问题**: `NameError: name 'Optional' is not defined`

**原因**: 缺少类型导入

**解决**: 确保所有文件都正确导入了typing模块的类型注解

```python
from typing import Dict, Any, Optional
```

### 2. 配置不生效

**问题**: 环境变量配置不生效

**原因**: 
- 环境变量未正确设置
- .env文件未加载
- 环境变量名称拼写错误

**解决**:
```bash
# 检查环境变量
echo $SUBAGENT_TIMEOUT_SECONDS

# 确保使用正确的环境文件
export ENVIRONMENT=development
```

### 3. 测试失败

**问题**: 测试用例失败

**原因**: 
- 依赖组件未正确导入
- 测试环境配置不正确
- 测试用例逻辑错误

**解决**:
```bash
# 运行单个测试文件
pytest tests/core/agent/test_coding_subagent_basic.py -v

# 查看详细错误信息
pytest tests/core/agent/test_coding_subagent_basic.py -v -s
```

### 4. 超时不生效

**问题**: 工具执行超时但没有触发超时异常

**原因**: 
- 超时功能未启用
- 超时时间设置过长
- 工具执行未超时

**解决**:
```python
# 检查功能开关
ENABLE_TIMEOUT=true

# 检查超时时间
SUBAGENT_TIMEOUT_SECONDS=60

# 检查代码是否正确使用超时
result = agent.run(..., timeout=30)
```

### 5. 参数验证失败

**问题**: 参数验证总是失败

**原因**: 
- 参数格式不正确
- 工具不在白名单中
- 参数验证规则过于严格

**解决**:
```python
# 检查参数格式
context = {
    "tool": "bash",
    "params": {"command": "ls"}  # 确保params是字典
}

# 检查工具白名单
ALLOWED_TOOLS=bash,read_file,write_to_file,edit

# 检查验证规则
# 查看parameter_validator.py中的验证逻辑
```

### 6. 并发控制问题

**问题**: 并发数限制不生效

**原因**: 
- Semaphore配置不正确
- 并发数设置过高
- 并发控制未启用

**解决**:
```python
# 检查并发配置
MAX_CONCURRENT_TOOL_EXECUTIONS=10

# 检查Semaphore使用
with runtime.acquire_execution_slot(tool_name):
    # 执行工具
    pass
```

### 7. 性能监控数据不准确

**问题**: 性能监控数据不准确

**原因**: 
- 时间测量不精确
- 样本数量不足
- 性能监控未启用

**解决**:
```python
# 使用time.perf_counter()进行精确测量
start_time = time.perf_counter()
# 执行操作
duration = time.perf_counter() - start_time

# 确保有足够的样本
for i in range(100):
    monitor.record_execution(duration, success)
```

### 8. 安全审计日志过多

**问题**: 审计日志占用过多内存

**原因**: 
- 日志数量限制设置过高
- 日志清理机制未启用
- 日志记录过于频繁

**解决**:
```python
# 调整日志数量限制
auditor = SecurityAuditor(max_logs=100)  # 降低到100

# 定期清理日志
auditor.audit_log.clear()
```

## 调试技巧

### 1. 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 检查功能开关状态

```python
flags = FeatureFlags()
print(f"超时启用: {flags.is_timeout_enabled()}")
print(f"验证启用: {flags.is_validation_enabled()}")
```

### 3. 查看性能指标

```python
performance = agent.performance.get_summary()
print(f"平均执行时间: {performance['avg_time']}秒")
print(f"错误率: {performance['error_rate']:.2%}")
```

### 4. 查看安全审计报告

```python
audit_report = agent.security.get_audit_report()
print(f"总执行次数: {audit_report['total_executions']}")
print(f"可疑活动: {audit_report['suspicious_activities']}")
```

### 5. 检查降级级别

```python
level = agent.degradation.get_current_level()
config = agent.degradation.get_level_config()
print(f"当前级别: {level}")
print(f"级别配置: {config}")
```

## 性能问题排查

### 1. 执行时间过长

**检查项**:
- 超时时间是否设置过长
- 是否启用了不必要的功能
- 并发数是否设置过高

**优化建议**:
- 降低超时时间
- 禁用可选功能（进度显示、停滞检测）
- 降低并发数

### 2. 内存占用过高

**检查项**:
- 审计日志数量限制
- 性能监控样本数量限制
- 进度跟踪器数据清理

**优化建议**:
- 降低日志数量限制
- 降低样本数量限制
- 定期清理进度数据

### 3. CPU占用过高

**检查项**:
- 并发数是否设置过高
- 是否有死循环
- 是否有频繁的锁竞争

**优化建议**:
- 降低并发数
- 检查锁使用情况
- 优化算法复杂度

## 安全问题排查

### 1. 参数验证绕过

**检查项**:
- 参数验证是否启用
- 验证规则是否完整
- 是否有验证漏洞

**解决建议**:
- 确保参数验证始终启用
- 定期审查验证规则
- 进行安全测试

### 2. 命令注入风险

**检查项**:
- 命令注入检测是否有效
- 是否有遗漏的危险字符
- 白名单是否完整

**解决建议**:
- 增强命令注入检测
- 扩展危险字符列表
- 严格限制可用工具

### 3. 路径穿越风险

**检查项**:
- 路径穿越检测是否有效
- 是否有遗漏的路径模式
- 文件操作权限是否正确

**解决建议**:
- 增强路径穿越检测
- 使用绝对路径
- 限制文件操作范围

## 联系支持

如果问题无法通过上述方法解决，请：
1. 收集详细的错误日志
2. 记录环境配置
3. 提供复现步骤
4. 联系技术支持团队