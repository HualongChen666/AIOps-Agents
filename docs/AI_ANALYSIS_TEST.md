# AI分析流程测试文档

## 概述

本文档描述了AIOps SRE Agent的AI分析流程测试方案，包括测试场景、测试用例和测试脚本。

---

## AI分析流程

### 流程定义

```
┌─────────────────────────────────────────────────────────┐
│                AI Analysis Flow                          │
├─────────────────────────────────────────────────────────┤
│  1. Analysis Request                                    │
│     ├── User selects resource/service                    │
│     ├── User configures analysis parameters              │
│     └── User triggers AI analysis                       │
├─────────────────────────────────────────────────────────┤
│  2. Data Collection                                     │
│     ├── Collect metrics data                            │
│     ├── Collect logs data                               │
│     ├── Collect topology data                           │
│     └── Collect historical data                         │
├─────────────────────────────────────────────────────────┤
│  3. Data Preprocessing                                  │
│     ├── Clean data                                      │
│     ├── Normalize data                                  │
│     ├── Aggregate data                                  │
│     └── Feature extraction                              │
├─────────────────────────────────────────────────────────┤
│  4. AI Analysis Execution                               │
│     ├── Anomaly detection                               │
│     ├── Root cause analysis                             │
│     ├── Pattern recognition                             │
│     └── Predictive analysis                            │
├─────────────────────────────────────────────────────────┤
│  5. Result Generation                                   │
│     ├── Generate analysis report                        │
│     ├── Provide recommendations                          │
│     ├── Create visualizations                           │
│     └── Export results                                 │
├─────────────────────────────────────────────────────────┤
│  6. Result Review                                       │
│     ├── User reviews analysis results                   │
│     ├── User validates findings                         │
│     ├── User provides feedback                          │
│     └── User takes action                               │
└─────────────────────────────────────────────────────────┘
```

---

## 测试场景

### 场景1：单资源AI分析

#### 场景描述
用户选择单个资源，配置分析参数，触发AI分析，系统收集数据，执行AI分析，生成分析报告，用户查看分析结果。

#### 测试步骤
1. 用户登录系统
2. 用户导航到资源列表页面
3. 用户选择特定资源
4. 用户点击AI分析按钮
5. 用户配置分析参数（时间范围、分析类型）
6. 用户启动AI分析
7. 系统收集相关数据
8. 系统执行AI分析
9. 系统生成分析报告
10. 用户查看分析结果
11. 用户导出分析报告

#### 预期结果
- 资源选择成功
- 分析参数配置成功
- AI分析成功启动
- 数据收集完整
- AI分析结果准确
- 分析报告生成成功
- 分析报告导出成功

### 场景2：多资源AI分析

#### 场景描述
用户选择多个资源，配置分析参数，触发批量AI分析，系统收集数据，执行AI分析，生成分析报告，用户查看分析结果。

#### 测试步骤
1. 用户登录系统
2. 用户导航到资源列表页面
3. 用户选择多个资源
4. 用户点击批量AI分析按钮
5. 用户配置分析参数
6. 用户启动批量AI分析
7. 系统收集相关数据
8. 系统执行AI分析
9. 系统生成分析报告
10. 用户查看分析结果
11. 用户导出分析报告

#### 预期结果
- 多资源选择成功
- 批量分析参数配置成功
- 批量AI分析成功启动
- 数据收集完整
- AI分析结果准确
- 分析报告生成成功
- 分析报告导出成功

### 场景3：时间范围AI分析

#### 场景描述
用户选择时间范围，配置分析参数，触发AI分析，系统收集历史数据，执行AI分析，生成趋势分析报告。

#### 测试步骤
1. 用户登录系统
2. 用户导航到分析页面
3. 用户选择时间范围（过去7天）
4. 用户配置分析参数
5. 用户启动AI分析
6. 系统收集历史数据
7. 系统执行AI分析
8. 系统生成趋势分析报告
9. 用户查看分析结果
10. 用户导出分析报告

#### 预期结果
- 时间范围选择成功
- 历史数据收集完整
- AI分析结果准确
- 趋势分析报告生成成功
- 分析报告导出成功

### 场景4：自定义AI分析

#### 场景描述
用户自定义分析参数，选择分析类型，触发AI分析，系统执行自定义分析，生成分析报告。

#### 测试步骤
1. 用户登录系统
2. 用户导航到分析页面
3. 用户选择自定义分析
4. 用户配置自定义参数
5. 用户选择分析类型（根因分析、异常检测）
6. 用户启动AI分析
7. 系统执行自定义分析
8. 系统生成分析报告
9. 用户查看分析结果
10. 用户导出分析报告

#### 预期结果
- 自定义参数配置成功
- 分析类型选择成功
- 自定义分析成功执行
- 分析结果准确
- 分析报告生成成功
- 分析报告导出成功

### 场景5：AI分析历史查看

#### 场景描述
用户查看历史AI分析记录，选择特定分析记录，查看分析结果，重新执行分析。

#### 测试步骤
1. 用户登录系统
2. 用户导航到分析历史页面
3. 用户查看分析历史列表
4. 用户选择特定分析记录
5. 用户查看分析结果
6. 用户重新执行分析
7. 用户比较新旧分析结果
8. 用户导出分析报告

#### 预期结果
- 分析历史正确显示
- 分析记录查看成功
- 分析结果正确显示
- 重新分析成功执行
- 分析结果比较成功
- 分析报告导出成功

---

## Playwright测试脚本

### AI分析测试脚本

#### ai-analysis.spec.ts
```typescript
// tests_e2e/ai-analysis.spec.ts
import { test, expect } from '@playwright/test';

test.describe('AI Analysis', () => {
  test.beforeEach(async ({ page }) => {
    // 登录系统
    await page.goto('http://localhost:8000/login');
    await page.fill('[name="email"]', 'admin@example.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('http://localhost:8000/dashboard');
  });

  test('should analyze single resource', async ({ page }) => {
    // 导航到资源列表
    await page.goto('http://localhost:8000/resources');
    
    // 选择资源
    await page.click('.resource-item:first-child');
    
    // 点击AI分析按钮
    await page.click('button:has-text("AI Analysis")');
    
    // 配置分析参数
    await page.selectOption('[name="timeRange"]', '24h');
    await page.selectOption('[name="analysisType"]', 'root-cause');
    
    // 启动AI分析
    await page.click('button:has-text("Start Analysis")');
    
    // 验证分析进度显示
    await expect(page.locator('.analysis-progress')).toBeVisible();
    
    // 等待分析完成
    await page.waitForSelector('.analysis-complete', { timeout: 60000 });
    
    // 验证分析结果显示
    await expect(page.locator('.analysis-results')).toBeVisible();
    await expect(page.locator('.root-cause')).toBeVisible();
    
    // 导出分析报告
    await page.click('button:has-text("Export Report")');
    await page.selectOption('[name="format"]', 'pdf');
    await page.click('button:has-text("Download")');
    
    // 验证报告下载
    await expect(page.locator('.download-success')).toBeVisible();
  });

  test('should analyze multiple resources', async ({ page }) => {
    // 导航到资源列表
    await page.goto('http://localhost:8000/resources');
    
    // 选择多个资源
    await page.check('.resource-item:nth-child(1) input[type="checkbox"]');
    await page.check('.resource-item:nth-child(2) input[type="checkbox"]');
    await page.check('.resource-item:nth-child(3) input[type="checkbox"]');
    
    // 点击批量AI分析按钮
    await page.click('button:has-text("Batch AI Analysis")');
    
    // 配置分析参数
    await page.selectOption('[name="timeRange"]', '7d');
    await page.selectOption('[name="analysisType"]', 'anomaly-detection');
    
    // 启动批量AI分析
    await page.click('button:has-text("Start Analysis")');
    
    // 验证批量分析进度显示
    await expect(page.locator('.batch-analysis-progress')).toBeVisible();
    
    // 等待批量分析完成
    await page.waitForSelector('.batch-analysis-complete', { timeout: 120000 });
    
    // 验证批量分析结果显示
    await expect(page.locator('.batch-analysis-results')).toBeVisible();
    await expect(page.locator('.resource-analysis')).toHaveCount(3);
  });

  test('should analyze time range', async ({ page }) => {
    // 导航到分析页面
    await page.goto('http://localhost:8000/analysis');
    
    // 选择时间范围
    await page.selectOption('[name="timeRange"]', '7d');
    
    // 配置分析参数
    await page.selectOption('[name="analysisType"]', 'trend-analysis');
    
    // 启动AI分析
    await page.click('button:has-text("Start Analysis")');
    
    // 验证分析进度显示
    await expect(page.locator('.analysis-progress')).toBeVisible();
    
    // 等待分析完成
    await page.waitForSelector('.analysis-complete', { timeout: 60000 });
    
    // 验证趋势分析结果显示
    await expect(page.locator('.trend-analysis')).toBeVisible();
    await expect(page.locator('.trend-chart')).toBeVisible();
  });

  test('should perform custom analysis', async ({ page }) => {
    // 导航到分析页面
    await page.goto('http://localhost:8000/analysis');
    
    // 选择自定义分析
    await page.click('button:has-text("Custom Analysis")');
    
    // 配置自定义参数
    await page.fill('[name="customMetric"]', 'cpu_usage');
    await page.fill('[name="threshold"]', '90');
    await page.selectOption('[name="analysisType"]', 'custom');
    
    // 启动自定义分析
    await page.click('button:has-text("Start Analysis")');
    
    // 验证分析进度显示
    await expect(page.locator('.analysis-progress')).toBeVisible();
    
    // 等待分析完成
    await page.waitForSelector('.analysis-complete', { timeout: 60000 });
    
    // 验证自定义分析结果显示
    await expect(page.locator('.custom-analysis')).toBeVisible();
    await expect(page.locator('.custom-results')).toBeVisible();
  });

  test('should view analysis history', async ({ page }) => {
    // 导航到分析历史页面
    await page.goto('http://localhost:8000/analysis/history');
    
    // 验证分析历史列表显示
    await expect(page.locator('.analysis-history')).toBeVisible();
    await expect(page.locator('.analysis-record')).toHaveCount(5);
    
    // 选择特定分析记录
    await page.click('.analysis-record:first-child');
    
    // 验证分析结果显示
    await expect(page.locator('.analysis-results')).toBeVisible();
    
    // 重新执行分析
    await page.click('button:has-text("Re-run Analysis")');
    
    // 验证分析进度显示
    await expect(page.locator('.analysis-progress')).toBeVisible();
    
    // 等待分析完成
    await page.waitForSelector('.analysis-complete', { timeout: 60000 });
    
    // 比较新旧分析结果
    await expect(page.locator('.comparison-results')).toBeVisible();
  });
});
```

---

## 测试数据准备

### 测试资源数据

#### 资源数据模板
```json
{
  "id": "resource-001",
  "name": "server-1",
  "type": "server",
  "status": "active",
  "metrics": {
    "cpu_usage": 85,
    "memory_usage": 75,
    "disk_usage": 60,
    "network_io": 1000
  }
}
```

#### 测试资源数据集
```json
[
  {
    "id": "resource-001",
    "name": "server-1",
    "type": "server",
    "status": "active"
  },
  {
    "id": "resource-002",
    "name": "server-2",
    "type": "server",
    "status": "active"
  },
  {
    "id": "resource-003",
    "name": "database-1",
    "type": "database",
    "status": "active"
  }
]
```

---

## 测试执行

### 本地测试执行

#### 运行AI分析测试
```bash
# 运行所有AI分析测试
npx playwright test ai-analysis.spec.ts

# 运行特定测试
npx playwright test ai-analysis.spec.ts -g "should analyze single resource"

# 运行测试并生成报告
npx playwright test ai-analysis.spec.ts --reporter=html

# 运行测试并显示浏览器
npx playwright test ai-analysis.spec.ts --headed
```

### CI/CD测试执行

#### GitHub Actions配置
```yaml
# .github/workflows/e2e-ai-analysis.yml
name: E2E AI Analysis Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright
        run: npx playwright install --with-deps
      - name: Start application
        run: python main.py &
      - name: Wait for application
        run: sleep 30
      - name: Run E2E tests
        run: npx playwright test ai-analysis.spec.ts
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: playwright-report
          path: playwright-report/
```

---

## 测试验证

### 功能验证

#### 验证清单
- [ ] 资源选择成功
- [ ] 分析参数配置成功
- [ ] AI分析成功启动
- [ ] 数据收集完整
- [ ] AI分析结果准确
- [ ] 分析报告生成成功
- [ ] 分析报告导出成功

### 性能验证

#### 性能指标
- 数据收集时间<30秒
- AI分析时间<60秒
- 报告生成时间<10秒
- 总分析时间<120秒

### 稳定性验证

#### 稳定性指标
- 测试通过率≥95%
- 无重复性缺陷
- 无间歇性故障
- 系统稳定性良好

---

## 故障排除

### 常见问题

#### AI分析失败
```typescript
// 解决方案：检查AI分析服务
// 1. 验证AI分析服务是否正常
// 2. 检查数据收集是否完整
// 3. 验证AI模型是否正常
```

#### 数据收集失败
```typescript
// 解决方案：检查数据收集服务
// 1. 验证数据源是否可访问
// 2. 检查数据格式是否正确
// 3. 验证数据权限是否足够
```

#### 报告生成失败
```typescript
// 解决方案：检查报告生成服务
// 1. 验证报告模板是否正确
// 2. 检查报告数据是否完整
// 3. 验证报告格式是否支持
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 测试团队