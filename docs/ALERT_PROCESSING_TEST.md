# 告警处理流程测试文档

## 概述

本文档描述了AIOps SRE Agent的告警处理流程测试方案，包括测试场景、测试用例和测试脚本。

---

## 告警处理流程

### 流程定义

```
┌─────────────────────────────────────────────────────────┐
│              Alert Processing Flow                       │
├─────────────────────────────────────────────────────────┤
│  1. Alert Reception                                     │
│     ├── Receive alert from monitoring system           │
│     ├── Parse alert data                               │
│     └── Validate alert format                          │
├─────────────────────────────────────────────────────────┤
│  2. Alert Classification                                │
│     ├── Determine alert severity                        │
│     ├── Assign alert category                           │
│     └── Set alert priority                              │
├─────────────────────────────────────────────────────────┤
│  3. Alert Analysis                                     │
│     ├── Collect related data                           │
│     ├── Execute AI analysis                            │
│     ├── Generate root cause analysis                   │
│     └── Provide repair suggestions                     │
├─────────────────────────────────────────────────────────┤
│  4. Alert Notification                                  │
│     ├── Send notification to on-call engineer           │
│     ├── Send notification to Slack                      │
│     ├── Send notification to Email                      │
│     └── Create ticket in ServiceNow/Jira               │
├─────────────────────────────────────────────────────────┤
│  5. Alert Response                                     │
│     ├── Engineer acknowledges alert                     │
│     ├── Engineer reviews AI suggestions                 │
│     ├── Engineer executes manual repair                 │
│     └── Engineer triggers automatic repair             │
├─────────────────────────────────────────────────────────┤
│  6. Repair Execution                                    │
│     ├── Execute repair actions                          │
│     ├── Monitor repair progress                         │
│     ├── Validate repair results                         │
│     └── Handle repair failures                          │
├─────────────────────────────────────────────────────────┤
│  7. Alert Resolution                                   │
│     ├── Verify issue resolved                          │
│     ├── Update alert status                             │
│     ├── Close alert                                    │
│     └── Generate resolution report                      │
└─────────────────────────────────────────────────────────┘
```

---

## 测试场景

### 场景1：高优先级告警处理

#### 场景描述
系统接收到高优先级告警，立即通知值班工程师，工程师查看告警详情，执行AI建议的修复操作，验证修复结果，关闭告警。

#### 测试步骤
1. 模拟高优先级告警到达
2. 验证告警被正确接收
3. 验证告警被正确分类（高优先级）
4. 验证告警通知已发送
5. 工程师登录系统查看告警
6. 工程师查看告警详情
7. 工程师查看AI分析结果
8. 工程师执行自动修复
9. 验证修复操作执行成功
10. 验证修复结果验证通过
11. 工程师关闭告警
12. 验证告警已关闭

#### 预期结果
- 告警被正确接收和分类
- 告警通知及时发送
- AI分析结果准确
- 修复操作成功执行
- 修复结果验证通过
- 告警成功关闭

### 场景2：批量告警处理

#### 场景描述
系统同时接收到多个告警，工程师批量查看告警，批量执行修复操作，批量关闭告警。

#### 测试步骤
1. 模拟多个告警同时到达
2. 验证所有告警被正确接收
3. 验证告警被正确分类
4. 工程师登录系统查看告警列表
5. 工程师筛选告警
6. 工程师选择多个告警
7. 工程师执行批量操作
8. 验证批量操作执行成功
9. 验证所有告警被正确处理
10. 工程师批量关闭告警
11. 验证所有告警已关闭

#### 预期结果
- 所有告警被正确接收
- 批量操作成功执行
- 所有告警被正确处理
- 所有告警成功关闭

### 场景3：告警升级处理

#### 场景描述
告警在规定时间内未被处理，系统自动升级告警，通知更高级别的工程师。

#### 测试步骤
1. 模拟告警到达
2. 验证告警被正确接收
3. 设置告警升级规则（5分钟未处理）
4. 等待升级时间
5. 验证告警自动升级
6. 验证升级通知已发送
7. 高级别工程师接收通知
8. 高级别工程师处理告警
9. 验证告警成功处理

#### 预期结果
- 告警在规定时间内自动升级
- 升级通知及时发送
- 高级别工程师成功处理告警

### 场景4：告警重复处理

#### 场景描述
系统接收到重复告警，系统去重处理，避免重复通知。

#### 测试步骤
1. 模拟告警到达
2. 验证告警被正确接收
3. 模拟相同告警再次到达
4. 验证重复告警被去重
5. 验证没有重复通知
6. 验证告警状态正确更新

#### 预期结果
- 重复告警被正确去重
- 没有重复通知
- 告警状态正确更新

### 场景5：告警关联处理

#### 场景描述
系统接收到相关联的多个告警，系统识别告警关联关系，合并处理。

#### 测试步骤
1. 模拟相关联的告警到达
2. 验证告警被正确接收
3. 验证系统识别告警关联关系
4. 验证告警被合并处理
5. 工程师查看合并后的告警
6. 工程师执行修复操作
7. 验证所有相关告警被处理
8. 验证所有相关告警被关闭

#### 预期结果
- 告警关联关系被正确识别
- 告警被正确合并处理
- 所有相关告警被成功处理

---

## Playwright测试脚本

### 告警处理测试脚本

#### alert-processing.spec.ts
```typescript
// tests_e2e/alert-processing.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Alert Processing', () => {
  test.beforeEach(async ({ page }) => {
    // 登录系统
    await page.goto('http://localhost:8000/login');
    await page.fill('[name="email"]', 'admin@example.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('http://localhost:8000/dashboard');
  });

  test('should process high priority alert', async ({ page }) => {
    // 导航到告警列表
    await page.goto('http://localhost:8000/alerts');
    
    // 筛选高优先级告警
    await page.selectOption('[name="severity"]', 'high');
    await page.click('button:has-text("Filter")');
    
    // 点击第一个告警
    await page.click('.alert-item:first-child');
    
    // 验证告警详情显示
    await expect(page.locator('.alert-details')).toBeVisible();
    await expect(page.locator('.alert-severity')).toContainText('high');
    
    // 查看AI分析结果
    await page.click('button:has-text("AI Analysis")');
    await expect(page.locator('.ai-analysis')).toBeVisible();
    
    // 执行自动修复
    await page.click('button:has-text("Auto Repair")');
    await expect(page.locator('.repair-progress')).toBeVisible();
    
    // 等待修复完成
    await page.waitForSelector('.repair-success', { timeout: 30000 });
    
    // 验证修复结果
    await expect(page.locator('.repair-result')).toContainText('success');
    
    // 关闭告警
    await page.click('button:has-text("Close Alert")');
    await expect(page.locator('.alert-closed')).toBeVisible();
  });

  test('should process batch alerts', async ({ page }) => {
    // 导航到告警列表
    await page.goto('http://localhost:8000/alerts');
    
    // 选择多个告警
    await page.check('.alert-item:nth-child(1) input[type="checkbox"]');
    await page.check('.alert-item:nth-child(2) input[type="checkbox"]');
    await page.check('.alert-item:nth-child(3) input[type="checkbox"]');
    
    // 执行批量操作
    await page.click('button:has-text("Batch Action")');
    await page.selectOption('[name="action"]', 'auto-repair');
    await page.click('button:has-text("Execute")');
    
    // 验证批量操作执行
    await expect(page.locator('.batch-progress')).toBeVisible();
    
    // 等待批量操作完成
    await page.waitForSelector('.batch-success', { timeout: 60000 });
    
    // 验证所有告警被处理
    await expect(page.locator('.alert-processed')).toHaveCount(3);
  });

  test('should handle alert escalation', async ({ page }) => {
    // 导航到告警列表
    await page.goto('http://localhost:8000/alerts');
    
    // 创建测试告警
    await page.click('button:has-text("Create Alert")');
    await page.fill('[name="message"]', 'Test escalation alert');
    await page.selectOption('[name="severity"]', 'medium');
    await page.click('button:has-text("Create")');
    
    // 等待升级时间（模拟）
    await page.waitForTimeout(5000);
    
    // 验证告警已升级
    await page.reload();
    await expect(page.locator('.alert-escalated')).toBeVisible();
    await expect(page.locator('.alert-severity')).toContainText('high');
  });

  test('should handle duplicate alerts', async ({ page }) => {
    // 导航到告警列表
    await page.goto('http://localhost:8000/alerts');
    
    // 记录初始告警数量
    const initialCount = await page.locator('.alert-item').count();
    
    // 创建重复告警
    await page.click('button:has-text("Create Alert")');
    await page.fill('[name="message"]', 'Duplicate test alert');
    await page.selectOption('[name="severity"]', 'high');
    await page.click('button:has-text("Create")');
    
    // 再次创建相同告警
    await page.click('button:has-text("Create Alert")');
    await page.fill('[name="message"]', 'Duplicate test alert');
    await page.selectOption('[name="severity"]', 'high');
    await page.click('button:has-text("Create")');
    
    // 验证告警数量没有增加
    const finalCount = await page.locator('.alert-item').count();
    expect(finalCount).toBe(initialCount + 1);
  });

  test('should handle related alerts', async ({ page }) => {
    // 导航到告警列表
    await page.goto('http://localhost:8000/alerts');
    
    // 创建相关联的告警
    await page.click('button:has-text("Create Alert")');
    await page.fill('[name="message"]', 'Related alert 1');
    await page.fill('[name="resource"]', 'server-1');
    await page.selectOption('[name="severity"]', 'high');
    await page.click('button:has-text("Create")');
    
    await page.click('button:has-text("Create Alert")');
    await page.fill('[name="message"]', 'Related alert 2');
    await page.fill('[name="resource"]', 'server-1');
    await page.selectOption('[name="severity"]', 'high');
    await page.click('button:has-text("Create")');
    
    // 验证告警被关联
    await page.click('.alert-item:first-child');
    await expect(page.locator('.related-alerts')).toBeVisible();
    await expect(page.locator('.related-alert')).toHaveCount(1);
    
    // 执行修复操作
    await page.click('button:has-text("Auto Repair")');
    await page.waitForSelector('.repair-success', { timeout: 30000 });
    
    // 验证所有相关告警被处理
    await page.goto('http://localhost:8000/alerts');
    await expect(page.locator('.alert-resolved')).toHaveCount(2);
  });
});
```

---

## 测试数据准备

### 测试告警数据

#### 告警数据模板
```json
{
  "severity": "high",
  "message": "Test alert message",
  "source": "monitoring-system",
  "resource": "server-1",
  "timestamp": "2026-08-31T00:00:00Z",
  "metadata": {
    "cpu_usage": 95,
    "memory_usage": 90,
    "disk_usage": 85
  }
}
```

#### 测试告警数据集
```json
[
  {
    "id": "alert-001",
    "severity": "high",
    "message": "CPU usage critical",
    "source": "prometheus",
    "resource": "server-1",
    "timestamp": "2026-08-31T00:00:00Z"
  },
  {
    "id": "alert-002",
    "severity": "medium",
    "message": "Memory usage warning",
    "source": "prometheus",
    "resource": "server-2",
    "timestamp": "2026-08-31T00:01:00Z"
  },
  {
    "id": "alert-003",
    "severity": "low",
    "message": "Disk usage notice",
    "source": "prometheus",
    "resource": "server-3",
    "timestamp": "2026-08-31T00:02:00Z"
  }
]
```

---

## 测试执行

### 本地测试执行

#### 运行告警处理测试
```bash
# 运行所有告警处理测试
npx playwright test alert-processing.spec.ts

# 运行特定测试
npx playwright test alert-processing.spec.ts -g "should process high priority alert"

# 运行测试并生成报告
npx playwright test alert-processing.spec.ts --reporter=html

# 运行测试并显示浏览器
npx playwright test alert-processing.spec.ts --headed
```

### CI/CD测试执行

#### GitHub Actions配置
```yaml
# .github/workflows/e2e-alert-processing.yml
name: E2E Alert Processing Tests

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
        run: npx playwright test alert-processing.spec.ts
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
- [ ] 告警被正确接收
- [ ] 告警被正确分类
- [ ] 告警通知及时发送
- [ ] AI分析结果准确
- [ ] 修复操作成功执行
- [ ] 修复结果验证通过
- [ ] 告警成功关闭

### 性能验证

#### 性能指标
- 告警接收时间<1秒
- 告警分类时间<2秒
- AI分析时间<30秒
- 修复执行时间<60秒
- 总处理时间<120秒

### 稳定性验证

#### 稳定性指标
- 测试通过率≥95%
- 无重复性缺陷
- 无间歇性故障
- 系统稳定性良好

---

## 故障排除

### 常见问题

#### 告警未正确接收
```typescript
// 解决方案：检查告警接收端点
// 1. 验证告警接收API是否正常
// 2. 检查告警格式是否正确
// 3. 验证网络连接是否正常
```

#### AI分析失败
```typescript
// 解决方案：检查AI分析服务
// 1. 验证AI分析服务是否正常
// 2. 检查数据收集是否完整
// 3. 验证AI模型是否正常
```

#### 修复操作失败
```typescript
// 解决方案：检查修复服务
// 1. 验证修复服务是否正常
// 2. 检查修复权限是否足够
// 3. 验证修复参数是否正确
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 测试团队