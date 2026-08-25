# API测试用例

本目录包含安全管理、修复管理和监控高级API路由的测试用例。

## 测试文件

1. **test_security_advanced_router.py** - 安全管理API测试
   - 测试25个安全管理相关的API端点
   - 包括密钥管理、MFA、ABAC、RBAC、速率限制等

2. **test_repair_advanced_router.py** - 修复管理API测试
   - 测试20个修复管理相关的API端点
   - 包括配置管理、HITL审批、修复效果、平台特定修复等

3. **test_monitoring_advanced_router.py** - 监控API测试
   - 测试35个监控相关的API端点
   - 包括日志告警、Elasticsearch、Tempo、Loki、健康检查等

## 测试覆盖

每个测试文件包含：
- ✅ GET、POST、PUT、PATCH、DELETE操作测试
- ✅ 正常情况测试
- ✅ 错误情况测试
- ✅ 数据验证测试
- ✅ 权限控制测试
- ✅ 使用mock模拟依赖项

## 运行测试

### 安装依赖

```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### 运行所有测试

```bash
pytest
```

### 运行特定测试文件

```bash
pytest tests/api/test_security_advanced_router.py
pytest tests/api/test_repair_advanced_router.py
pytest tests/api/test_monitoring_advanced_router.py
```

### 运行特定测试类

```bash
pytest tests/api/test_security_advanced_router.py::TestKeyManagement
```

### 运行特定测试方法

```bash
pytest tests/api/test_security_advanced_router.py::TestKeyManagement::test_get_keys_success
```

### 生成覆盖率报告

```bash
pytest --cov=api --cov-report=html
```

覆盖率报告将生成在 `htmlcov/` 目录中。

### 查看覆盖率报告

```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

## 测试覆盖率目标

- 目标覆盖率：90%以上
- 当前配置要求：`--cov-fail-under=90`

## 测试标记

- `@pytest.mark.slow` - 标记慢速测试
- `@pytest.mark.integration` - 标记集成测试
- `@pytest.mark.unit` - 标记单元测试

### 运行特定标记的测试

```bash
# 只运行单元测试
pytest -m unit

# 跳过慢速测试
pytest -m "not slow"

# 运行集成测试
pytest -m integration
```

## 测试结构

每个测试文件按功能模块组织：

```python
class TestModuleName:
    """模块测试类"""
    
    def test_success_case(self, client):
        """测试正常情况"""
        pass
    
    def test_error_case(self, client):
        """测试错误情况"""
        pass
    
    def test_validation_error(self, client):
        """测试验证错误"""
        pass
```

## Fixtures

测试使用以下fixtures：

- `client` - FastAPI测试客户端
- `mock_request` - 模拟请求对象
- `event_loop` - 异步事件循环

## Mock使用

测试中使用mock来模拟：
- 外部依赖（如数据库、API调用）
- 核心模块函数
- 配置项

示例：

```python
@patch('api.security_advanced_router.analyze_command')
def test_check_command_success(self, mock_analyze_command, client):
    mock_analyze_command.return_value = {
        'risk_level': 'high',
        'reason': 'Dangerous command'
    }
    # 测试代码
```

## 持续集成

这些测试可以集成到CI/CD流程中：

```yaml
# GitHub Actions示例
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest --cov=api --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## 故障排除

### 导入错误

如果遇到导入错误，确保：
1. 项目根目录在Python路径中
2. 所有依赖已安装
3. 从项目根目录运行pytest

### 异步测试错误

如果异步测试失败，确保：
1. 安装了 `pytest-asyncio`
2. 使用了 `@pytest.mark.asyncio` 标记
3. 使用了 `event_loop` fixture

### Mock问题

如果mock不工作，检查：
1. Mock路径是否正确
2. Mock返回值是否设置
3. 是否需要side_effect而不是return_value

## 贡献指南

添加新测试时：

1. 遵循现有测试结构
2. 使用描述性的测试名称
3. 测试正常和错误情况
4. 添加必要的mock
5. 确保覆盖率不下降
6. 更新此README

## 许可证

与主项目相同。
