# Playwright测试脚本文档

## 概述

本文档描述了AIOps SRE Agent的Playwright测试脚本配置和使用方法，包括测试脚本结构、配置文件和最佳实践。

---

## Playwright配置

### 配置文件

#### playwright.config.ts
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests_e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list']
  ],
  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  webServer: {
    command: 'python main.py',
    url: 'http://localhost:8000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

---

## 测试脚本结构

### 目录结构

```
tests_e2e/
├── fixtures/
│   ├── auth.fixture.ts
│   ├── data.fixture.ts
│   └── api.fixture.ts
├── pages/
│   ├── BasePage.ts
│   ├── LoginPage.ts
│   ├── DashboardPage.ts
│   ├── AlertsPage.ts
│   ├── AnalysisPage.ts
│   └── RepairPage.ts
├── tests/
│   ├── auth.spec.ts
│   ├── alert-processing.spec.ts
│   ├── ai-analysis.spec.ts
│   ├── auto-repair.spec.ts
│   └── dashboard.spec.ts
└── utils/
    ├── helpers.ts
    └── constants.ts
```

---

## Page Object Model

### BasePage
```typescript
// tests_e2e/pages/BasePage.ts
import { Page, Locator } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async navigate(url: string) {
    await this.page.goto(url);
  }

  async click(selector: string) {
    await this.page.click(selector);
  }

  async fill(selector: string, value: string) {
    await this.page.fill(selector, value);
  }

  async waitForSelector(selector: string, timeout?: number) {
    await this.page.waitForSelector(selector, { timeout });
  }

  async isVisible(selector: string): Promise<boolean> {
    return await this.page.isVisible(selector);
  }

  async getText(selector: string): Promise<string> {
    return await this.page.textContent(selector) || '';
  }
}
```

### LoginPage
```typescript
// tests_e2e/pages/LoginPage.ts
import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;

  constructor(page: Page) {
    super(page);
    this.emailInput = page.locator('[name="email"]');
    this.passwordInput = page.locator('[name="password"]');
    this.loginButton = page.locator('button[type="submit"]');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }
}
```

### DashboardPage
```typescript
// tests_e2e/pages/DashboardPage.ts
import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class DashboardPage extends BasePage {
  readonly systemHealthCard: Locator;
  readonly activeAlertsCard: Locator;
  readonly activeRepairsCard: Locator;

  constructor(page: Page) {
    super(page);
    this.systemHealthCard = page.locator('.system-health-card');
    this.activeAlertsCard = page.locator('.active-alerts-card');
    this.activeRepairsCard = page.locator('.active-repairs-card');
  }

  async getSystemHealth(): Promise<string> {
    return await this.systemHealthCard.textContent() || '';
  }

  async getActiveAlertsCount(): Promise<number> {
    const text = await this.activeAlertsCard.textContent() || '';
    return parseInt(text);
  }

  async getActiveRepairsCount(): Promise<number> {
    const text = await this.activeRepairsCard.textContent() || '';
    return parseInt(text);
  }
}
```

---

## Fixtures

### Auth Fixture
```typescript
// tests_e2e/fixtures/auth.fixture.ts
import { test as base } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

type AuthFixtures = {
  loginPage: LoginPage;
  authenticatedPage: any;
};

export const test = base.extend<AuthFixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  authenticatedPage: async ({ page, loginPage }, use) => {
    await page.goto('http://localhost:8000/login');
    await loginPage.login('admin@example.com', 'admin123');
    await use(page);
  },
});
```

### Data Fixture
```typescript
// tests_e2e/fixtures/data.fixture.ts
import { test as base } from '@playwright/test';

type DataFixtures = {
  testData: any;
};

export const test = base.extend<DataFixtures>({
  testData: async ({}, use) => {
    const data = {
      user: {
        email: 'admin@example.com',
        password: 'admin123'
      },
      alert: {
        severity: 'high',
        message: 'Test alert',
        source: 'test'
      },
      resource: {
        name: 'server-1',
        type: 'server'
      }
    };
    await use(data);
  },
});
```

---

## 测试脚本示例

### 完整的E2E测试脚本

#### complete-journey.spec.ts
```typescript
// tests_e2e/tests/complete-journey.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { AlertsPage } from '../pages/AlertsPage';

test.describe('Complete User Journey', () => {
  test('should complete alert processing journey', async ({ page }) => {
    // 1. 登录
    const loginPage = new LoginPage(page);
    await page.goto('http://localhost:8000/login');
    await loginPage.login('admin@example.com', 'admin123');
    await expect(page).toHaveURL('http://localhost:8000/dashboard');

    // 2. 查看仪表板
    const dashboardPage = new DashboardPage(page);
    const systemHealth = await dashboardPage.getSystemHealth();
    expect(systemHealth).toContain('healthy');

    // 3. 查看告警列表
    await page.goto('http://localhost:8000/alerts');
    const alertsPage = new AlertsPage(page);
    await alertsPage.filterBySeverity('high');
    
    // 4. 处理告警
    await alertsPage.selectFirstAlert();
    await alertsPage.viewAlertDetails();
    await alertsPage.executeAutoRepair();
    
    // 5. 验证修复结果
    await alertsPage.verifyRepairSuccess();
    
    // 6. 关闭告警
    await alertsPage.closeAlert();
    
    // 7. 验证告警已关闭
    await expect(page.locator('.alert-closed')).toBeVisible();
  });

  test('should complete AI analysis journey', async ({ page }) => {
    // 1. 登录
    const loginPage = new LoginPage(page);
    await page.goto('http://localhost:8000/login');
    await loginPage.login('admin@example.com', 'admin123');
    await expect(page).toHaveURL('http://localhost:8000/dashboard');

    // 2. 导航到资源列表
    await page.goto('http://localhost:8000/resources');
    
    // 3. 选择资源
    await page.click('.resource-item:first-child');
    
    // 4. 执行AI分析
    await page.click('button:has-text("AI Analysis")');
    await page.selectOption('[name="timeRange"]', '24h');
    await page.click('button:has-text("Start Analysis")');
    
    // 5. 等待分析完成
    await page.waitForSelector('.analysis-complete', { timeout: 60000 });
    
    // 6. 查看分析结果
    await expect(page.locator('.analysis-results')).toBeVisible();
    
    // 7. 导出报告
    await page.click('button:has-text("Export Report")');
    await page.selectOption('[name="format"]', 'pdf');
    await page.click('button:has-text("Download")');
  });

  test('should complete auto repair journey', async ({ page }) => {
    // 1. 登录
    const loginPage = new LoginPage(page);
    await page.goto('http://localhost:8000/login');
    await loginPage.login('admin@example.com', 'admin123');
    await expect(page).toHaveURL('http://localhost:8000/dashboard');

    // 2. 创建修复规则
    await page.goto('http://localhost:8000/repair-rules');
    await page.click('button:has-text("Create Rule")');
    await page.fill('[name="ruleName"]', 'Test Repair Rule');
    await page.selectOption('[name="condition"]', 'cpu_usage > 90');
    await page.selectOption('[name="action"]', 'restart_service');
    await page.click('button:has-text("Save")');
    
    // 3. 启用修复规则
    await page.click('button:has-text("Enable")');
    
    // 4. 等待自动修复触发
    await page.waitForTimeout(30000);
    
    // 5. 查看修复历史
    await page.goto('http://localhost:8000/repair-history');
    await expect(page.locator('.repair-record')).toBeVisible();
  });
});
```

---

## 测试工具函数

### Helpers
```typescript
// tests_e2e/utils/helpers.ts
import { Page } from '@playwright/test';

export async function waitForElement(page: Page, selector: string, timeout: number = 30000) {
  await page.waitForSelector(selector, { timeout });
}

export async function clickElement(page: Page, selector: string) {
  await page.click(selector);
}

export async function fillElement(page: Page, selector: string, value: string) {
  await page.fill(selector, value);
}

export async function getText(page: Page, selector: string): Promise<string> {
  return await page.textContent(selector) || '';
}

export async function isVisible(page: Page, selector: string): Promise<boolean> {
  return await page.isVisible(selector);
}

export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `screenshots/${name}.png` });
}
```

### Constants
```typescript
// tests_e2e/utils/constants.ts
export const TEST_URL = 'http://localhost:8000';
export const TEST_USER = {
  email: 'admin@example.com',
  password: 'admin123'
};
export const TEST_TIMEOUT = 30000;
export const NAVIGATION_TIMEOUT = 30000;
```

---

## 测试运行命令

### 本地运行
```bash
# 运行所有测试
npx playwright test

# 运行特定测试文件
npx playwright test complete-journey.spec.ts

# 运行特定测试
npx playwright test -g "should complete alert processing journey"

# 运行特定项目
npx playwright test --project=chromium

# 运行测试并显示浏览器
npx playwright test --headed

# 运行测试并生成报告
npx playwright test --reporter=html

# 运行测试并录制视频
npx playwright test --video=retain-on-failure

# 运行测试并截图
npx playwright test --screenshot=only-on-failure
```

### CI/CD运行
```bash
# CI环境运行
npx playwright test --workers=1

# 生成JUnit报告
npx playwright test --reporter=junit

# 生成HTML报告
npx playwright test --reporter=html
```

---

## 测试最佳实践

### 1. 使用Page Object Model
- 将页面元素和操作封装在Page类中
- 提高代码可维护性
- 减少代码重复

### 2. 使用Fixtures
- 使用fixtures共享测试数据
- 提高测试可读性
- 减少测试代码重复

### 3. 使用等待
- 使用显式等待而非隐式等待
- 提高测试稳定性
- 减少测试失败

### 4. 使用选择器
- 使用稳定的选择器
- 避免使用动态选择器
- 提高测试可靠性

### 5. 使用断言
- 使用有意义的断言
- 提供清晰的错误信息
- 提高测试可调试性

---

## 测试调试

### 调试模式
```bash
# 调试模式运行
npx playwright test --debug

# 慢动作模式
npx playwright test --slow-mo=1000

# 显示浏览器
npx playwright test --headed
```

### 失败重试
```typescript
// playwright.config.ts
retries: process.env.CI ? 2 : 0,
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 测试团队