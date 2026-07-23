# Devin 项目级指令

## 反幻觉铁律

1. 禁止凭记忆或训练数据推测项目内容，一切以 `read_file` 读到的真实文件为准
2. 修改任何文件前，必须先 `read_file` 该文件的完整内容
3. 调用任何函数/类/接口前，必须先确认它在项目中真实存在
4. 如果无法通过读取文件确认某个信息，立即停下来问用户
5. 每次修改完成后，必须重新 `read_file` 文件确认修改结果与预期一致

## 输出与交互约定

- 默认使用中文回复用户
- 项目根目录固定为 `C:\AIOps_Agent_bak`；执行命令时默认 `Cwd` 为该目录
- 优先使用 `read_file`、PowerShell `bash`、`edit`/`multi_edit` 等当前可用工具
- Windows 环境禁止用 Unix 风格 heredoc；多行 Python 脚本先写 `.py` 文件再执行

## 并发与效率

- 批量读取文件、搜索、运行测试时优先并行调用
- 长时间运行的命令用 `bash` 的 `Background` 模式启动，并通过 `command_status` 轮询
- 任务执行用 `todo_list` 跟踪，完成后立即更新状态

## 项目资源

- 记忆文件: `C:\Users\Hualong_Chen\.codeium\windsurf\memories\aiops_project_memory.md`
- 任务清单: `C:\AIOps_Agent_bak\docs\document\task_list.md`
- 技能目录: `.devin/skills/`
- 代码管理: GitLab MCP
- 本地敏感配置: `.devin/config.local.json`（已加入 `.gitignore` 和 `.devinignore`，不要提交）
