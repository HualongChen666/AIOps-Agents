# CI/CD集成配置文档

## 概述

本文档描述了AIOps SRE Agent的E2E测试CI/CD集成配置方案，包括GitHub Actions配置、测试执行流程和最佳实践。

---

## CI/CD架构

### CI/CD流程

```
┌─────────────────────────────────────────────────────────┐
│              CI/CD Pipeline Architecture                  │
├─────────────────────────────────────────────────────────┤
│  1. Code Push/PR                                        │
│     ├── Developer pushes code                           │
│     ├── CI pipeline triggered                           │
│     └── Tests scheduled                                │
├─────────────────────────────────────────────────────────┤
│  2. Environment Setup                                   │
│     ├── Checkout code                                   │
│     ├── Setup dependencies                             │
|     ├── Start services                                 │
│     └── Configure environment                          │
├─────────────────────────────────────────────────────────┤
│  3. Test Execution                                     │
│     ├── Run unit tests                                 │
│     ├── Run integration tests                          │
│     ├── Run E2E tests                                  │
│     └── Generate test reports                           │
├─────────────────────────────────────────────────────────┤
│  4. Test Reporting                                     │
│     ├── Upload test results                            │
│     ├── Generate coverage reports                      │
│     ├── Send notifications                             │
│     └── Update status badges                            │
├─────────────────────────────────────────────────────────┤
│  5. Deployment (if tests pass)                          │
│     ├── Build Docker images                             │
│     ├── Deploy to staging                              │
│     ├── Run smoke tests                                │
│     └── Deploy to production                           │
└─────────────────────────────────────────────────────────┘
```

---

## GitHub Actions配置

### 主CI/CD配置

#### .github/workflows/e2e-tests.yml
```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    strategy:
      fail-fast: false
      matrix:
        browser: [chromium, firefox, webkit]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Install Node dependencies
        run: |
          cd frontend
          npm ci
          cd ..
      
      - name: Install Playwright
        run: npx playwright install --with-deps ${{ matrix.browser }}
      
      - name: Start application
        run: |
          python main.py &
          echo $! > app.pid
      
      - name: Wait for application
        run: |
          for i in {1..30}; do
            if curl -s http://localhost:8000/health > /dev/null; then
              echo "Application is ready"
              break
            fi
            echo "Waiting for application... ($i/30)"
            sleep 2
          done
      
      - name: Run E2E tests
        run: npx playwright test --project=${{ matrix.browser }}
        env:
          CI: true
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report-${{ matrix.browser }}
          path: playwright-report/
          retention-days: 7
      
      - name: Upload test screenshots
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: screenshots-${{ matrix.browser }}
          path: screenshots/
          retention-days: 7
      
      - name: Upload test videos
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: videos-${{ matrix.browser }}
          path: test-results/videos/
          retention-days: 7
      
      - name: Stop application
        if: always()
        run: |
          if [ -f app.pid ]; then
            kill $(cat app.pid) || true
            rm app.pid
          fi
```

### 并行测试配置

#### .github/workflows/e2e-parallel.yml
```yaml
name: E2E Parallel Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  e2e-parallel:
    runs-on: ubuntu-latest
    
    strategy:
      fail-fast: false
      matrix:
        shard: [1/4, 2/4, 3/4, 4/4]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          cd frontend && npm ci && cd ..
          npx playwright install --with-deps chromium
      
      - name: Start application
        run: python main.py &
      
      - name: Wait for application
        run: sleep 30
      
      - name: Run E2E tests (sharded)
        run: npx playwright test --shard=${{ matrix.shard }}
        env:
          CI: true
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report-shard-${{ matrix.shard }}
          path: playwright-report/
```

### 定期测试配置

#### .github/workflows/e2e-scheduled.yml
```yaml
name: Scheduled E2E Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  scheduled-e2e:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          cd frontend && npm ci && cd ..
          npx playwright install --with-deps
      
      - name: Start application
        run: python main.py &
      
      - name: Wait for application
        run: sleep 30
      
      - name: Run all E2E tests
        run: npx playwright test
        env:
          CI: true
      
      - name: Generate test report
        run: npx playwright show-report
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: scheduled-playwright-report
          path: playwright-report/
      
      - name: Send notification on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Scheduled E2E Tests Failed',
              body: 'The scheduled E2E tests have failed. Please check the test results.'
            })
```

---

## 测试报告配置

### HTML报告生成

#### Playwright报告配置
```typescript
// playwright.config.ts
export default defineConfig({
  reporter: [
    ['html', { open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list']
  ],
});
```

### 覆盖率报告

#### 覆盖率配置
```yaml
# .github/workflows/coverage.yml
name: Coverage Report

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  coverage:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests with coverage
        run: pytest --cov=core --cov=api --cov-report=html --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
      
      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
```

---

## 通知配置

### Slack通知

#### Slack通知配置
```yaml
# .github/workflows/slack-notification.yml
name: Slack Notification

on:
  workflow_run:
    workflows: ["E2E Tests"]
    types: [completed]
    branches: [main, develop]

jobs:
  slack-notification:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    
    steps:
      - name: Send Slack notification
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'E2E tests failed'
          webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Email通知

#### Email通知配置
```yaml
# .github/workflows/email-notification.yml
name: Email Notification

on:
  workflow_run:
    workflows: ["E2E Tests"]
    types: [completed]
    branches: [main, develop]

jobs:
  email-notification:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    
    steps:
      - name: Send email notification
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: 'E2E Tests Failed'
          to: ${{ secrets.NOTIFICATION_EMAIL }}
          from: GitHub Actions
          body: 'The E2E tests have failed. Please check the test results.'
```

---

## 性能优化

### 缓存策略

#### 依赖缓存
```yaml
# .github/workflows/e2e-tests.yml
- name: Cache Python dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache Node dependencies
  uses: actions/cache@v3
  with:
    path: frontend/node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('frontend/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### 并行执行

#### 矩阵策略
```yaml
strategy:
  fail-fast: false
  matrix:
    browser: [chromium, firefox, webkit]
    shard: [1/2, 2/2]
```

---

## 测试环境配置

### 环境变量

#### GitHub Secrets
```yaml
# GitHub Secrets配置
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  REDIS_URL: ${{ secrets.REDIS_URL }}
  QDRANT_URL: ${{ secrets.QDRANT_URL }}
  API_KEY: ${{ secrets.API_KEY }}
```

### Docker环境

#### Docker Compose配置
```yaml
# .github/workflows/docker-e2e.yml
name: Docker E2E Tests

on:
  push:
    branches: [main, develop]

jobs:
  docker-e2e:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Start Docker services
        run: docker-compose -f docker-compose.test.yml up -d
      
      - name: Wait for services
        run: |
          for i in {1..30}; do
            if docker-compose ps | grep -q "Up"; then
              echo "Services are ready"
              break
            fi
            echo "Waiting for services... ($i/30)"
            sleep 2
          done
      
      - name: Run E2E tests
        run: docker-compose run e2e-tests
      
      - name: Stop Docker services
        if: always()
        run: docker-compose -f docker-compose.test.yml down
```

---

## 测试结果存储

### 结果存储

#### S3存储配置
```yaml
# .github/workflows/store-results.yml
name: Store Test Results

on:
  workflow_run:
    workflows: ["E2E Tests"]
    types: [completed]

jobs:
  store-results:
    runs-on: ubuntu-latest
    
    steps:
      - name: Download test results
        uses: actions/download-artifact@v3
        with:
          name: playwright-report
      
      - name: Upload to S3
        uses: jakejarvis/s3-sync-action@v0.3.1
        with:
          args: -avz ./ s3://${{ secrets.S3_BUCKET }}/test-results/
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: 'us-east-1'
```

---

## 故障排除

### 常见问题

#### 测试超时
```yaml
# 解决方案：增加超时时间
- name: Run E2E tests
  run: npx playwright test
  timeout-minutes: 30
```

#### 服务启动失败
```yaml
# 解决方案：添加健康检查
- name: Wait for application
  run: |
    for i in {1..60}; do
      if curl -s http://localhost:8000/health > /dev/null; then
        echo "Application is ready"
        break
      fi
      echo "Waiting for application... ($i/60)"
      sleep 2
    done
```

#### 测试环境问题
```yaml
# 解决方案：使用Docker容器
- name: Run tests in Docker
  run: docker-compose run e2e-tests
```

---

## 最佳实践

### 1. 测试隔离
- 每个测试独立运行
- 不依赖测试执行顺序
- 使用测试数据清理

### 2. 并行执行
- 使用矩阵策略并行执行
- 合理分配测试负载
- 避免资源竞争

### 3. 失败处理
- 设置合理的重试次数
- 提供详细的错误信息
- 自动上传失败截图和视频

### 4. 性能优化
- 使用缓存减少构建时间
- 并行执行测试
- 优化测试执行时间

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent DevOps团队