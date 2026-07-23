# 贡献者指南

本指南帮助外部开发者快速上手并为 AIOps Agent 项目作出贡献。内容覆盖贡献流程、开发环境搭建、代码规范、测试指南以及提交规范，全部基于项目已有 `CONTRIBUTING.md` 文档进行结构化整理。

## 目录

- [贡献流程](#贡献流程)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [提交规范](#提交规范)
- [获取帮助](#获取帮助)

---

## 贡献流程

1. **Fork 并 Clone**
   ```bash
   git clone https://github.com/your-username/AIOps_Agent.git
   cd AIOps_Agent
   ```
2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name   # 新功能
   # 或
   git checkout -b fix/your-bug-fix          # Bug 修复
   ```
3. **本地开发**
   - 按照 **开发环境搭建** 部分准备好虚拟环境与依赖。
   - 完成代码实现，遵循 **代码规范**（PEP8、类型提示、Google 风格 docstring）。
4. **编写测试**
   - 为新功能或修改编写单元/集成测试，确保覆盖率 ≥ 80%。
5. **提交并 Push**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   git push origin feature/your-feature-name
   ```
6. **创建 Pull Request**
   - 在 GitHub 上创建 PR，描述变更动机、关联 Issue（若有）并附上必要的截图或日志。 
   - PR 将触发 CI 自动检查（格式化、Lint、类型检查、测试），并进入维护者审查阶段。

---

## 开发环境搭建

1. **创建并激活虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   # 或
   venv\Scripts\activate    # Windows
   ```
2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```
3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 填入本地或测试环境配置
   ```
4. **运行测试确保环境正常**
   ```bash
   pytest
   ```
5. **启动开发服务器**（可选）
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 代码规范

- **Python 风格**：遵循 PEP 8，最大行长 100，使用 `black` 自动格式化。
- **类型提示**：所有函数/方法必须使用类型注解。
- **Docstring**：采用 Google 风格，包含参数、返回值及示例。
- **导入顺序**：使用 `isort` 按标准分组。
- **静态检查**：运行 `mypy`、`flake8` 保证代码质量。

格式化示例：
```bash
python -m black .
python -m isort .
python -m mypy .
python -m flake8 .
```

## 安全注意事项
- **不要提交** 明文密钥或凭证。
- 所有敏感信息应通过环境变量读取。
- 对外部输入进行严格校验，防止注入攻击。

---

## 测试指南

### 目录结构
```
tests/
├── unit/          # 单元测试
├── integration/   # 集成测试
├── e2e/           # 端到端测试
└── fixtures/      # 测试数据/Mock
```
### 编写测试
```python
import pytest
from your_module import your_function

def test_your_function():
    # Arrange
    input_data = {...}
    # Act
    result = your_function(input_data)
    # Assert
    assert result == expected
```
### 运行测试
```bash
pytest                # 运行全部
pytest tests/unit/    # 仅运行单元测试
pytest --cov=. --cov-report=html   # 生成覆盖报告
```
> **目标**：整体覆盖率 ≥ 80%，关键路径覆盖率 ≥ 90%。

---

## 提交规范

- **提交信息** 采用 **Conventional Commits**：
  - `feat:` 新功能
  - `fix:` Bug 修复
  - `docs:` 文档更新
  - `style:` 代码格式（不影响功能）
  - `refactor:` 重构代码
  - `test:` 测试相关
  - `chore:` 其他维护
- **提交频率**：每次功能/修复完成后立即提交，避免大幅度一次性提交。
- **审查前自检**：在提交前运行全部 CI 检查（格式化、Lint、类型检查、测试），确保 `git status` 为干净状态。

---

## 获取帮助

- **文档**：项目根目录下的 `README.md`、`API_QUICKSTART.md`、`DEPLOYMENT.md`、`ARCHITECTURE.md` 等。
- **Issues**：在 GitHub Issues 区报告 bug 或提出需求。
- **Discussions**：在 GitHub Discussions 发起技术交流。
- **即时沟通**：加入项目 Slack/Discord（如有）获取实时帮助。

---

**致谢**

感谢每一位贡献者的投入与努力，您可以在 `CONTRIBUTORS.md` 中看到大家的名字，亦会在每次发布说明中列出贡献者名单。

---

*本指南遵循项目的技术与流程要求，任何更新请同步至 `CONTRIBUTING.md` 与本文件。*