# 自动修复流程测试文档

## 概述

本文档描述了AIOps SRE Agent的自动修复流程测试方案，包括测试场景、测试用例和测试脚本。

---

## 自动修复流程

### 流程定义

```
┌─────────────────────────────────────────────────────────┐
│              Auto Repair Flow                           │
├─────────────────────────────────────────────────────────┤
│  1. Rule Configuration                                 │
│     ├── User creates repair rule                       │
│     ├── User configures conditions                     │
│     ├── User configures actions                        │
│     └── User enables rule                              │
├─────────────────────────────────────────────────────────┤
│  2. Problem Detection                                   │
│     ├── System monitors resources                      │
│     ├── System detects issues                          │
│     ├── System matches rules                           │
│     └── System triggers repair                         │
├─────────────────────────────────────────────────────────┤
│  3. Repair Execution                                   │
│     ├── System executes repair actions                  │
|     ├── System monitors repair progress                 │
|     ├── System validates repair results                │
|     └── System handles failures                        │
├─────────────────────────────────────────────────────────┤
│  4. Repair Validation                                  │
│     ├── System verifies issue resolved                 │
|     ├── System validates resource status               │
|     └── System confirms repair success                 │
├─────────────────────────────────────────────────────────┤
│  5. Repair Rollback (if needed)                         │
│     ├── System detects repair failure                  │
|     ├── System executes rollback actions                │
|     ├── System validates rollback results               │
|     └── System records rollback history                │
├─────────────────────────────────────────────────────────┤
│  6. Repair History                                     │
│     ├── System records repair details                  │
|     ├── System updates repair status                   │
|     └── System generates repair report                 │
└─────────────────────────────────────────────────────────┘
```

---

## 测试场景

### 场景1：基础自动修复

#### 场景描述
用户配置基础自动修复规则，系统检测符合条件的问题，执行修复操作，验证修复结果。

#### 测试步骤
1. 用户登录系统
2. 用户导航到修复规则页面
3. 用户创建修复规则
4. 用户配置修复条件（CPU>90%）
5. 用户配置修复操作（重启服务）
6. 用户启用修复规则
7. 系统检测符合条件的问题
8. 系统执行修复操作
9. 系统监控修复进度
10. 系统验证修复结果
11. 系统记录修复历史
12. 用户查看修复历史

#### 预期结果
- 修复规则成功配置
- 修复条件正确匹配
- 修复操作成功执行
- 修复结果验证通过
- 修复历史正确记录

### 场景2：条件自动修复

#### 场景描述
用户配置复杂条件的自动修复规则，系统检测符合多个条件的问题，执行修复操作。

#### 测试步骤
1. 用户登录系统
2. 用户导航到修复规则页面
3. 用户创建修复规则
4. 用户配置多个修复条件（CPU>90% AND 内存>80%）
5. 用户配置修复操作
6. 用户启用修复规则
7. 系统检测符合条件的问题
8. 系统执行修复操作
9. 系统监控修复进度
10. 系统验证修复结果
11. 系统记录修复历史

#### 预期结果
- 复杂条件正确配置
- 条件匹配准确
- 修复操作成功执行
- 修复结果验证通过

### 场景3：批量自动修复

#### 场景描述
系统检测到多个符合条件的问题，系统批量执行修复操作。

#### 测试步骤
1. 用户配置修复规则
2. 用户启用批量修复
3. 系统检测多个符合条件的问题
4. 系统批量执行修复操作
5. 系统监控批量修复进度
6. 系统验证批量修复结果
7. 系统记录批量修复历史
8. 用户查看批量修复历史

#### 预期结果
- 批量修复成功执行
- 所有问题被正确处理
- 批量修复结果验证通过

### 场景4：自动修复回滚

#### 场景描述
修复操作失败，系统自动执行回滚操作，恢复原始状态。

#### 测试步骤
1. 用户配置修复规则（包含回滚配置）
2. 用户启用修复规则
3. 系统检测符合条件的问题
4. 系统执行修复操作
5. 修复操作失败
6. 系统自动执行回滚操作
7. 系统验证回滚结果
8. 系统记录回滚历史
9. 用户查看回滚历史

#### 预期结果
- 修复操作失败被检测
- 自动回滚成功执行
- 回滚结果验证通过
- 回滚历史正确记录

### 场景5：自动修复审批

#### 场景描述
用户配置需要审批的自动修复规则，系统检测问题，发送审批请求，用户审批后执行修复。

#### 测试步骤
1. 用户配置修复规则（需要审批）
2. 用户启用修复规则
3. 系统检测符合条件的问题
4. 系统发送审批请求
5. 用户接收审批请求
6. 用户审批修复操作
7. 系统执行修复操作
8. 系统监控修复进度
9. 系统验证修复结果
10. 系统记录修复历史

#### 预期结果
- 审批请求成功发送
- 用户审批成功
- 修复操作成功执行
- 修复结果验证通过

---

## Playwright测试脚本

### 自动修复测试脚本

#### auto-repair.spec.ts
```typescript
// tests_e2e/auto-repair.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Auto Repair', () => {
  test.beforeEach(async ({ page }) => {
    // 登录系统
    await page.goto('http://localhost:8000/login');
    await page.fill('[name="email"]', 'admin@example.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('http://localhost:8000/dashboard');
  });

  test('should execute basic auto repair', async ({ page }) => {
    // 导航到修复规则页面
    await page.goto('http://localhost:8000/repair-rules');
    
    // 创建修复规则
    await page.click('button:has-text("Create Rule")');
    await page.fill('[name="ruleName"]', 'CPU High Repair');
    await page.selectOption('[name="condition"]', 'cpu_usage > 90');
    await page.selectOption('[name="action"]', 'restart_service');
    await page.click('button:has-text("Save")');
    
    // 启用修复规则
    await page.click('button:has-text("Enable")');
    
    // 验证规则已启用
    await expect(page.locator('.rule-enabled')).toBeVisible();
    
    // 等待自动修复触发
    await page.waitForTimeout(30000);
    
    // 验证修复执行
    await page.goto('http://localhost:8000/repair-history');
    await expect(page.locator('.repair-record')).toHaveCount(1);
    await expect(page.locator('.repair-status')).toContainText('success');
  });

  test('should execute conditional auto repair', async ({ page }) => {
    // 导航到修复规则页面
    await page.goto('http://localhost:8000/repair-rules');
    
    // 创建条件修复规则
    await page.click('button:has-text("Create Rule")');
    await page.fill('[name="ruleName"]', 'Complex Condition Repair');
    await page.selectOption('[name="condition1"]', 'cpu_usage > 90');
    await page.selectOption('[name="operator"]', 'AND');
    await page.selectOption('[name="condition2"]', 'memory_usage > 80');
    await page.selectOption('[name="action"]', 'restart_service');
    await page.click('button:has-text("Save")');
    
    // 启用修复规则
    await page.click('button:has-text("Enable")');
    
    // 验证规则已启用
    await expect(page.locator('.rule-enabled')).toBeVisible();
    
    // 等待自动修复触发
    await page.waitForTimeout(30000);
    
    // 验证修复执行
    await page.goto('http://localhost:8000/repair-history');
    await expect(page.locator('.repair-record')).toHaveCount(1);
  });

  test('should execute batch auto repair', async ({ page }) => {
    // 导航到修复规则页面
    await page.goto('http://localhost:8000/repair-rules');
    
    // 创建批量修复规则
    await page.click('button:has-text("Create Rule")');
    await page.fill('[name="ruleName"]', 'Batch Repair');
    await page.selectOption('[name="condition"]', 'cpu_usage > 90');
    await page.selectOption('[name="action"]', 'restart_service');
    await page.check('[name="batchRepair"]');
    await page.click('button:has-text("Save")');
    
    // 启用修复规则
    await page.click('button:has-text("Enable")');
    
    // 验证规则已启用
    await expect(page.locator('.rule-enabled')).toBeVisible();
    
    // 等待批量修复触发
    await page.waitForTimeout(60000);
    
    // 验证批量修复执行
    await page.goto('http://localhost:8000/repair-history');
    await expect(page.locator('.repair-record')).toHaveCount(3);
  });

  test('should execute auto repair rollback', async ({ page }) => {
    // 导航到修复规则页面
    await page.goto('http://localhost:8000/repair-rules');
    
    // 创建带回滚的修复规则
    await page.click('button:has-text("Create Rule")');
    await page.fill('[name="ruleName"]', 'Repair with Rollback');
    await page.selectOption('[name="condition"]', 'cpu_usage > 90');
    await page.selectOption('[name="action"]', 'restart_service');
    await page.check('[name="enableRollback"]');
    await page.click('button:has-text("Save")');
    
    // 启用修复规则
    await page.click('button:has-text("Enable")');
    
    // 验证规则已启用
    await expect(page.locator('.rule-enabled')).toBeVisible();
    
    // 等待自动修复触发
    await page.waitForTimeout(30000);
    
    // 验证回滚执行
    await page.goto('http://localhost:8000/repair-history');
    await expect(page.locator('.rollback-record')).toBeVisible();
    await expect(page.locator('.rollback-status')).toContainText('success');
  });

  test('should execute auto repair with approval', async ({ page }) => {
    // 导航到修复规则页面
    await page.goto('http://localhost:8000/repair-rules');
    
    // 创建需要审批的修复规则
    await page.click('button:has-text("Create Rule")');
    await page.fill('[name="ruleName"]', 'Repair with Approval');
    await page.selectOption('[name="condition"]', 'cpu_usage > 90');
    await page.selectOption('[name="action"]', 'restart_service');
    await page.check('[name="requireApproval"]');
    await page.click('button:has-text("Save")');
    
    // 启用修复规则
    await page.click('button:has-text("Enable")');
    
    // 验证规则已启用
    await expect(page.locator('.rule-enabled')).toBeVisible();
    
    // 等待审批请求
    await page.waitForTimeout(30000);
    
    // 查看审批请求
    await page.goto('http://localhost:8000/approvals');
    await expect(page.locator('.approval-request')).toBeVisible();
    
    // 审批修复操作
    await page.click('button:has-text("Approve")');
    
    // 验证修复执行
    await page.goto('http://localhost:8000/repair-history');
    await expect(page.locator('.repair-record')).toHaveCount(1);
  });
});
```

---

## 测试数据准备

### 测试修复规则数据

#### 修复规则数据模板
```json
{
  "id": "rule-001",
  "name": "CPU High Repair",
  "condition": "cpu_usage > 90",
  "action": "restart_service",
  "enabled": true,
  "batch": false,
  "rollback": false,
  "approval": false
}
```

---

## 测试执行

### 本地测试执行

#### 运行自动修复测试
```bash
# 运行所有自动修复测试
npx playwright test auto-repair.spec.ts

# 运行特定测试
npx playwright test auto-repair.spec.ts -g "should execute basic auto repair"

# 运行测试并生成报告
npx playwright test auto-repair.spec.ts --reporter=html
```

---

## 测试验证

### 功能验证
- [ ] 修复规则成功配置
- [ ] 修复条件正确匹配
- [ ] 修复操作成功执行
- [ ] 修复结果验证通过
- [ ] 修复历史正确记录

### 性能验证
- 修复检测时间<10秒
- 修复执行时间<60秒
- 修复验证时间<10秒
- 总修复时间<120秒

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 测试团队