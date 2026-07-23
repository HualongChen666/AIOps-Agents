# 测试覆盖率报告配置指南

## 概述

本文档说明了AIOps Agent项目的测试覆盖率报告配置，包括HTML、XML、终端等多种格式的报告生成和CI/CD集成。

## 覆盖率配置

### pytest.ini 配置

已配置以下覆盖率选项在 `pytest.ini` 中：

```ini
addopts =
    --cov=.
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-report=json:coverage.json
```

**说明**:
- `--cov=.`: 测量当前目录的覆盖率
- `--cov-report=html:htmlcov`: 生成HTML报告到htmlcov目录
- `--cov-report=xml:coverage.xml`: 生成XML报告到coverage.xml文件
- `--cov-report=term-missing`: 在终端显示覆盖率并标出缺失的行
- `--cov-report=json:coverage.json`: 生成JSON报告到coverage.json文件

### .coveragerc 配置

已创建 `.coveragerc` 配置文件，包含详细的覆盖率设置：

#### [run] 部分
- `source`: 指定要测量的源代码目录
- `omit`: 排除不需要测量的文件（测试文件、__pycache__等）
- `branch`: 启用分支覆盖率测量
- `parallel`: 并行模式支持
- `data_file`: 覆盖率数据文件位置

#### [report] 部分
- `precision`: 覆盖率百分比精度
- `show_missing`: 显示缺失的行
- `skip_empty`: 跳过空文件
- `sort`: 报告排序方式
- `exclude_lines`: 排除特定行（pragma、防御性代码等）

#### [html] 部分
- `directory`: HTML报告输出目录
- `title`: HTML报告标题

#### [xml] 部分
- `output`: XML输出文件路径

#### [json] 部分
- `output`: JSON输出文件路径

## 覆盖率报告格式

### HTML报告

**生成命令**:
```bash
pytest --cov=. --cov-report=html:htmlcov
```

**查看报告**:
- 打开 `htmlcov/index.html` 文件在浏览器中查看
- 提供交互式的覆盖率可视化界面
- 可以查看每个文件的详细覆盖率

**特点**:
- 可视化显示
- 交互式导航
- 显示缺失的行
- 按模块和文件组织

### XML报告

**生成命令**:
```bash
pytest --cov=. --cov-report=xml:coverage.xml
```

**用途**:
- CI/CD集成
- 覆盖率趋势分析
- 第三方工具集成（如Codecov、Coveralls）

**特点**:
- 机器可读格式
- 适合自动化处理
- 包含详细的覆盖率数据

### 终端报告

**生成命令**:
```bash
pytest --cov=. --cov-report=term-missing
```

**用途**:
- 实时覆盖率反馈
- 快速查看覆盖率状态
- 开发过程中使用

**特点**:
- 命令行显示
- 标出缺失的行
- 实时反馈

### JSON报告

**生成命令**:
```bash
pytest --cov=. --cov-report=json:coverage.json
```

**用途**:
- 自定义分析
- 趋势分析
- 数据处理

**特点**:
- 结构化数据
- 易于解析
- 适合程序化处理

## 覆盖率报告历史

### 本地历史存储

创建脚本存储覆盖率历史：

```bash
# scripts/store_coverage_history.sh
#!/bin/bash

# 创建历史目录
mkdir -p coverage_history

# 生成覆盖率报告
pytest --cov=. --cov-report=json:coverage.json

# 存储历史（使用时间戳）
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp coverage.json "coverage_history/coverage_${TIMESTAMP}.json"

# 保留最近30天的历史
find coverage_history -name "coverage_*.json" -mtime +30 -delete
```

### 覆盖率趋势分析

创建Python脚本分析覆盖率趋势：

```python
# scripts/analyze_coverage_trend.py
import json
import glob
from datetime import datetime
import matplotlib.pyplot as plt

def analyze_coverage_trend():
    """分析覆盖率趋势"""
    history_files = glob.glob("coverage_history/coverage_*.json")
    history_files.sort()

    dates = []
    coverages = []

    for file in history_files:
        with open(file) as f:
            data = json.load(f)
            timestamp = datetime.strptime(file.split("_")[1].split(".")[0], "%Y%m%d_%H%M%S")
            coverage = data["totals"]["percent_covered"]
            dates.append(timestamp)
            coverages.append(coverage)

    # 绘制趋势图
    plt.figure(figsize=(12, 6))
    plt.plot(dates, coverages, marker='o')
    plt.title("Coverage Trend")
    plt.xlabel("Date")
    plt.ylabel("Coverage %")
    plt.grid(True)
    plt.savefig("coverage_trend.png")
    plt.close()

if __name__ == "__main__":
    analyze_coverage_trend()
```

## CI/CD集成

### GitHub Actions

创建 `.github/workflows/coverage.yml`:

```yaml
name: Coverage Report

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  coverage:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests with coverage
        run: pytest --cov=. --cov-report=xml:coverage.xml --cov-report=html:htmlcov

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: false

      - name: Upload coverage reports
        uses: actions/upload-artifact@v3
        with:
          name: coverage-reports
          path: |
            coverage.xml
            htmlcov/
```

### GitLab CI

创建 `.gitlab-ci.yml`:

```yaml
coverage:
  stage: test
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=. --cov-report=xml:coverage.xml --cov-report=html:htmlcov
  artifacts:
    paths:
      - coverage.xml
      - htmlcov/
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
  coverage: '/TOTAL\s+\d+\s+\d+\s+(\d+\%)/'
```

### Jenkins Pipeline

创建 `Jenkinsfile`:

```groovy
pipeline {
    agent any

    stages {
        stage('Coverage') {
            steps {
                sh '''
                    pip install -r requirements.txt
                    pip install pytest pytest-cov
                    pytest --cov=. --cov-report=xml:coverage.xml --cov-report=html:htmlcov
                '''
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])

                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }
    }
}
```

## 覆盖率目标

### 当前目标

- **整体覆盖率**: 40%（务实目标）
- **核心模块覆盖率**: 80%
- **API覆盖率**: 70%

### 覆盖率门槛

在 `.coveragerc` 中设置覆盖率门槛：

```ini
[report]
fail_under = 40
```

### 分模块覆盖率

为不同模块设置不同的覆盖率目标：

```ini
[report]
fail_under = 40

[core]
fail_under = 80

[api]
fail_under = 70
```

## 使用指南

### 生成覆盖率报告

```bash
# 生成所有格式的报告
pytest

# 只生成HTML报告
pytest --cov=. --cov-report=html:htmlcov

# 只生成XML报告
pytest --cov=. --cov-report=xml:coverage.xml

# 只生成终端报告
pytest --cov=. --cov-report=term-missing

# 生成特定模块的覆盖率
pytest --cov=core --cov-report=html:htmlcov
```

### 查看覆盖率报告

```bash
# 在浏览器中打开HTML报告
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### 过滤覆盖率报告

```bash
# 排除测试文件
pytest --cov=. --cov-report=html --omit=tests/*

# 只包含特定目录
pytest --cov=core --cov-report=html
```

## 最佳实践

### 1. 定期生成覆盖率报告

建议在每次提交后自动生成覆盖率报告，并在CI/CD中集成。

### 2. 设置覆盖率门槛

在 `.coveragerc` 中设置 `fail_under` 参数，确保覆盖率不低于目标值。

### 3. 排除不需要测量的代码

使用 `omit` 和 `exclude_lines` 排除测试文件、__pycache__、防御性代码等。

### 4. 分支覆盖率

启用 `branch = True` 以测量分支覆盖率，更全面地评估测试质量。

### 5. 覆盖率趋势分析

定期分析覆盖率趋势，识别覆盖率下降的原因。

### 6. 覆盖率报告归档

归档覆盖率报告，便于历史对比和趋势分析。

## 故障排除

### 覆盖率报告为空

**问题**: 覆盖率报告显示0%或为空

**解决方案**:
- 检查 `source` 配置是否正确
- 确认测试文件是否被正确发现
- 检查 `omit` 配置是否排除了所有文件

### 覆盖率报告不准确

**问题**: 覆盖率报告显示的覆盖率与实际不符

**解决方案**:
- 清除旧的覆盖率数据：`rm .coverage`
- 检查 `exclude_lines` 配置
- 确认测试是否真正执行了代码

### 并行测试覆盖率

**问题**: 并行测试时覆盖率报告不准确

**解决方案**:
- 在 `.coveragerc` 中设置 `parallel = True`
- 使用 `coverage combine` 合并覆盖率数据
- 或禁用并行测试进行覆盖率测量

## 总结

本文档提供了完整的覆盖率报告配置指南，包括：
- pytest.ini 和 .coveragerc 配置
- 多种格式的覆盖率报告生成
- 覆盖率历史和趋势分析
- CI/CD集成示例
- 使用指南和最佳实践

遵循本指南可以确保项目有完善的覆盖率报告系统，支持持续改进测试质量。

---

**文档版本**: 1.0
**最后更新**: 2026-07-06
**维护者**: AIOps Agent Team
