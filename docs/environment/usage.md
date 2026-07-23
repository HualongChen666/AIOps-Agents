# 环境变量使用指南

本文档说明如何在 AIOps Agent 项目中设置、加载和验证环境变量。

## 环境变量设置

创建 `.env` 文件并填充变量值：

```bash
cp .env.example .env
# 编辑 .env
```

在 Windows 下可直接复制并重命名 `.

## 环境变量加载

`ConfigManager` 在 `load_config()` 中调用 `python-dotenv` 的 `load_dotenv()` 加载 `.env` 文件。加载顺序：

1. `os.environ` 中的变量优先。
2. `.env` 文件中的变量补充。

## 环境变量优先级

当环境变量与 YAML 配置冲突时，优先级如下：

1. 环境变量
2. `.env` 文件
3. YAML 配置文件
4. 代码默认值

## 环境变量验证

运行验证脚本：

```bash
python scripts/validate_config.py
```

脚本会检查必填项、端口范围和密钥长度等。

## 常见问题

- **变量未生效**：确认 `.env` 在应用启动前已存在，并检查是否有拼写错误。
- **敏感信息泄露**：避免在日志中打印完整配置，`ConfigManager.get_config_dict()` 会排除敏感字段。
