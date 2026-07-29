---
name: security-tools
description: 原生 Tool 使用安全策略与最小权限约束
---

# Agent 原生 Tool 安全使用规则

> 本规则约束 Cascade/Windsurf Agent 在 `AIOps_Agent_bak` 项目中使用原生 Tool 的行为，防止越权、数据外泄和死循环。

## 1. 高危 Tool 必须显式确认

### `bash`
- 只有在命令**纯只读且不可变**（如 `python --version`、`pytest --collect-only`）时，才能设置 `SafeToAutoRun: true`。
- 以下命令必须**每次询问用户**，禁止自动运行：
  - 任何 `rm`、`del`、`rmdir`、`format`、`diskpart` 等删除/格式化命令
  - 任何 `pip install`、`npm install`、可执行文件下载/安装命令
  - 任何访问 `.env`、`*credentials*`、`*secret*`、`.ssh`、`*key*`、`*.pem` 的命令
  - 任何向外部网络发送数据的命令（`curl`、`Invoke-WebRequest`、`wget`）
  - 任何修改系统/注册表/服务配置的命令
- 工作目录严格限制在项目根 `C:\AIOps_Agent_bak`；避免使用 `cd` 切换目录。

### `read_url_content` / `search_web`
- 禁止访问本地/内网地址：`localhost`、`127.0.0.1`、`10.*`、`172.16-31.*`、`192.168.*`。
- 仅允许访问项目文档、PyPI、GitHub/GitLab 公开 API、官方文档等可信域名。
- 禁止将本地读取到的内容编码后发送到外部 URL。

### `write_to_file` / `edit` / `multi_edit`
- 只能写入/修改项目工作区内的文件。
- 禁止覆盖 `.env`、`.devin/*.local.json`、`*credentials*`、`*secret*`、`*.key`、`*.pem` 等敏感文件。
- 禁止写入可执行脚本后未确认就执行。

### `read_file`
- 禁止主动读取 `.env`、`.env.*`、`*credentials*`、`*secret*`、`*.key`、`*.pem`、`secrets/`、`credentials.json` 等敏感文件。
- 若用户明确要求，读取后不得通过 `read_url_content`/`search_web`/`bash` 外发。

### `browser_preview`
- 仅允许预览 `http://localhost` 或 `http://127.0.0.1` 上的本地服务。
- 禁止预览外部或内网其他主机服务。

## 2. 危险 Tool 组合必须拆分确认

以下组合属于**高危操作链**，执行前必须向用户说明风险并获得二次确认：

- `read_file`（读取敏感文件）+ `read_url_content` / `search_web` / `bash`（外发或执行）
- `find_by_name` / `grep_search`（扫描密钥）+ `read_file` + 任何网络/执行 Tool
- `write_to_file` / `edit`（写入脚本/配置）+ `bash`（执行）
- `bash`（安装依赖）+ `bash`（执行新安装的程序）
- `browser_preview` + `bash`（暴露本地服务）

## 3. 死循环防护

- 同一 Tool 在 60 秒内被调用超过 10 次且没有实质性进展，必须停止并询问用户。
- 禁止无终止条件地反复调用 `read_url_content`、`search_web`、`bash`、`write_to_file`、`command_status`。
- `skill` 调用时，禁止内部再次调用相同 skill 形成递归。

## 4. 最小权限执行顺序

调用 Tool 前按以下顺序评估：

1. 是否有**只读、无网络、无执行**的替代方案？
2. 是否需要用户确认？
3. 是否在项目工作区内？
4. 是否涉及敏感文件或外部网络？
5. 是否可能形成越权/外泄/破坏的攻击链？

## 5. 敏感文件保护清单

以下路径/模式默认禁止读取/写入，除非用户明确授权：

```
.env
.env.*
*.key
*.pem
credentials.json
secrets/
.devin/*.local.json
.ssh/
config/production.yaml（包含真实数据库密码时）
```

## 6. 违规处理

- 一旦检测到违反上述规则，立即向用户报告具体 Tool 和原因，不执行该操作。
- 不替用户做决定绕过安全规则。
