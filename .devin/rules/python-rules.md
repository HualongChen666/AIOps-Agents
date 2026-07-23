---
name: python-rules
description: Python代码规范和项目约定
---

# Python 项目规则

## 项目特定约定

### 文件结构约定
- API路由必须在 `api/` 目录下
- 数据库模型在 `core/` 相关模块中
- 测试文件在 `tests/` 目录下，对应源文件结构
- 配置文件使用 `config.py` 和环境变量

### 代码风格约定
- 使用类型提示 (Type Hints)
- 函数文档字符串使用 Google 风格
- 异步函数使用 `async/await`
- 错误处理使用自定义异常类

### 导入约定
- 标准库导入
- 第三方库导入
- 本地应用导入
- 每组之间空一行分隔

### 命名约定
- 类名: PascalCase
- 函数名: snake_case
- 常量: UPPER_CASE
- 私有方法: _leading_underscore

## 自动化检查规则

### 必须检查项
1. 所有函数必须有类型提示
2. 所有公开函数必须有文档字符串
3. 所有数据库操作必须是异步的
4. 所有API端点必须有错误处理
5. 敏感信息不能硬编码

### 质量标准
- 类型检查覆盖率: >90%
- 测试覆盖率: >80%
- 代码复杂度: <15
- 函数长度: <50行

## 智能触发规则

### 自动触发条件
当检测到以下情况时自动应用Python规则：
- 创建或修改 .py 文件
- 定义新的函数或类
- 添加数据库操作
- 创建API端点
- 编写测试代码

### 优先级规则
1. 安全相关检查 (最高优先级)
2. 类型检查
3. 代码风格检查
4. 文档完整性检查
5. 测试覆盖率检查 (最低优先级)

## 项目特定模式

### FastAPI路由模式
```python
@router.post("/endpoint")
async def endpoint_name(
    request: RequestModel,
    db: AsyncSession = Depends(get_db)
) -> ResponseModel:
    """端点描述."""
    try:
        # 实现逻辑
        return response
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 数据库操作模式
```python
async def database_operation(db: AsyncSession):
    """数据库操作模板."""
    try:
        result = await db.execute(query)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise
```

## 禁止模式

### 禁止的代码模式
- 硬编码的敏感信息
- 同步数据库操作
- 缺少错误处理的API端点
- 未经验证的用户输入
- 直接的SQL字符串拼接

## 工具集成

### 自动化工具集成
- black: 代码格式化
- mypy: 类型检查
- flake8: 代码质量检查
- bandit: 安全检查
- pytest: 测试运行

### 工具执行顺序
1. 安全检查 (bandit)
2. 类型检查 (mypy)
3. 代码质量 (flake8)
4. 格式检查 (black)
5. 测试运行 (pytest)