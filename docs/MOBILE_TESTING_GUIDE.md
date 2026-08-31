# 移动端测试指南

## 概述

本文档提供了AIOps SRE Agent前端应用的移动端测试指南，包括测试策略、测试方法、测试工具和测试流程。

---

## 测试策略

### 测试层次

#### 1. 单元测试
- 组件功能测试
- Hook测试
- 工具函数测试

#### 2. 集成测试
- 组件集成测试
- API集成测试
- 状态管理测试

#### 3. 端到端测试
- 用户流程测试
- 跨页面测试
- 真实设备测试

### 测试类型

#### 功能测试
- 基础功能验证
- 用户交互测试
- 业务逻辑测试

#### 性能测试
- 加载性能测试
- 渲染性能测试
- 内存使用测试

#### 兼容性测试
- 设备兼容性测试
- 浏览器兼容性测试
- 操作系统兼容性测试

#### 可访问性测试
- 屏幕阅读器测试
- 键盘导航测试
- 触摸交互测试

---

## 测试工具

### 单元测试工具

#### Jest + React Testing Library
```typescript
// Jest配置
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/__mocks__/fileMock.js'
  },
  collectCoverageFrom: [
    'components/**/*.{js,jsx,ts,tsx}',
    'app/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**'
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    }
  }
};
```

#### 测试示例
```typescript
// 组件测试示例
import { render, screen, fireEvent } from '@testing-library/react';
import { TouchButton } from './TouchButton';

describe('TouchButton', () => {
  it('should render button with correct text', () => {
    render(<TouchButton>Click me</TouchButton>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('should call onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<TouchButton onClick={handleClick}>Click me</TouchButton>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('should be disabled when disabled prop is true', () => {
    render(<TouchButton disabled>Click me</TouchButton>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
});
```

### 集成测试工具

#### Cypress
```typescript
// Cypress配置
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    viewportWidth: 375,
    viewportHeight: 667,
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    setupNodeEvents(on, config) {
      // 配置事件监听器
    }
  }
});
```

#### 测试示例
```typescript
// Cypress测试示例
describe('Mobile Navigation', () => {
  beforeEach(() => {
    cy.viewport(375, 667);
    cy.visit('/');
  });

  it('should open mobile menu when menu button is clicked', () => {
    cy.get('[data-testid="menu-button"]').click();
    cy.get('[data-testid="mobile-menu"]').should('be.visible');
  });

  it('should navigate to dashboard when dashboard link is clicked', () => {
    cy.get('[data-testid="menu-button"]').click();
    cy.get('[data-testid="dashboard-link"]').click();
    cy.url().should('include', '/dashboard');
  });
});
```

### 端到端测试工具

#### Playwright
```typescript
// Playwright配置
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
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
});
```

#### 测试示例
```typescript
// Playwright测试示例
import { test, expect } from '@playwright/test';

test('mobile navigation flow', async ({ page }) => {
  // 设置移动设备视口
  await page.setViewportSize({ width: 375, height: 667 });
  
  // 访问首页
  await page.goto('/');
  
  // 点击菜单按钮
  await page.click('[data-testid="menu-button"]');
  
  // 验证菜单可见
  await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible();
  
  // 点击仪表板链接
  await page.click('[data-testid="dashboard-link"]');
  
  // 验证导航到仪表板
  await expect(page).toHaveURL(/.*dashboard/);
});
```

---

## 移动端特定测试

### 触摸交互测试

#### 触摸事件测试
```typescript
// 触摸事件测试
describe('Touch Interactions', () => {
  it('should handle touch start event', () => {
    const handleTouchStart = jest.fn();
    const { getByTestId } = render(
      <div data-testid="touch-element" onTouchStart={handleTouchStart}>
        Touch me
      </div>
    );
    
    const element = getByTestId('touch-element');
    fireEvent.touchStart(element, {
      touches: [{ clientX: 100, clientY: 100 }]
    });
    
    expect(handleTouchStart).toHaveBeenCalled();
  });

  it('should handle touch move event', () => {
    const handleTouchMove = jest.fn();
    const { getByTestId } = render(
      <div data-testid="touch-element" onTouchMove={handleTouchMove}>
        Touch me
      </div>
    );
    
    const element = getByTestId('touch-element');
    fireEvent.touchMove(element, {
      touches: [{ clientX: 150, clientY: 150 }]
    });
    
    expect(handleTouchMove).toHaveBeenCalled();
  });
});
```

#### 手势测试
```typescript
// 手势测试
describe('Swipe Gestures', () => {
  it('should detect left swipe', () => {
    const onSwipeLeft = jest.fn();
    const { getByTestId } = render(
      <Swipeable onSwipeLeft={onSwipeLeft}>
        <div data-testid="swipe-element">Swipe me</div>
      </Swipeable>
    );
    
    const element = getByTestId('swipe-element');
    
    // 模拟左滑
    fireEvent.touchStart(element, {
      touches: [{ clientX: 200, clientY: 100 }]
    });
    fireEvent.touchMove(element, {
      touches: [{ clientX: 100, clientY: 100 }]
    });
    fireEvent.touchEnd(element);
    
    expect(onSwipeLeft).toHaveBeenCalled();
  });
});
```

### 响应式布局测试

#### 视口测试
```typescript
// 视口测试
describe('Responsive Layout', () => {
  it('should show mobile navigation on mobile viewport', () => {
    window.innerWidth = 375;
    render(<App />);
    
    expect(screen.getByTestId('mobile-nav')).toBeInTheDocument();
    expect(screen.queryByTestId('desktop-nav')).not.toBeInTheDocument();
  });

  it('should show desktop navigation on desktop viewport', () => {
    window.innerWidth = 1024;
    render(<App />);
    
    expect(screen.getByTestId('desktop-nav')).toBeInTheDocument();
    expect(screen.queryByTestId('mobile-nav')).not.toBeInTheDocument();
  });
});
```

#### 断点测试
```typescript
// 断点测试
describe('Breakpoints', () => {
  const breakpoints = {
    mobile: 375,
    tablet: 768,
    desktop: 1024
  };

  Object.entries(breakpoints).forEach(([name, width]) => {
    it(`should render correctly at ${name} breakpoint (${width}px)`, () => {
      window.innerWidth = width;
      render(<App />);
      
      // 验证布局
      const container = screen.getByTestId('main-container');
      expect(container).toHaveStyle({
        maxWidth: `${width}px`
      });
    });
  });
});
```

### 性能测试

#### Lighthouse测试
```typescript
// Lighthouse测试
describe('Lighthouse Performance', () => {
  it('should meet Lighthouse performance target', async () => {
    const lighthouse = require('lighthouse');
    const chromeLauncher = require('chrome-launcher');
    
    const chrome = await chromeLauncher.launch();
    const options = {
      logLevel: 'info',
      output: 'json',
      onlyCategories: ['performance'],
      port: chrome.port
    };
    
    const runnerResult = await lighthouse('http://localhost:3000', options);
    await chrome.kill();
    
    const score = runnerResult.lhr.categories.performance.score * 100;
    expect(score).toBeGreaterThanOrEqual(90);
  });
});
```

#### Core Web Vitals测试
```typescript
// Core Web Vitals测试
describe('Core Web Vitals', () => {
  it('should meet LCP target', async () => {
    const lcp = await measureLCP();
    expect(lcp).toBeLessThan(2500);
  });

  it('should meet FID target', async () => {
    const fid = await measureFID();
    expect(fid).toBeLessThan(100);
  });

  it('should meet CLS target', async () => {
    const cls = await measureCLS();
    expect(cls).toBeLessThan(0.1);
  });
});
```

---

## 设备测试

### iOS设备测试

#### 测试设备列表
- iPhone 12 Pro (iOS 15)
- iPhone 13 Pro (iOS 16)
- iPhone 14 Pro (iOS 17)
- iPad Pro (iOS 15)
- iPad Air (iOS 16)

#### iOS测试配置
```typescript
// iOS测试配置
const iOSDevices = [
  {
    name: 'iPhone 12 Pro',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    viewport: { width: 390, height: 844 }
  },
  {
    name: 'iPhone 13 Pro',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    viewport: { width: 390, height: 844 }
  }
];
```

#### iOS测试执行
```typescript
// iOS测试执行
const runIOSTests = async () => {
  for (const device of iOSDevices) {
    console.log(`Testing on ${device.name}`);
    
    // 设置用户代理
    await page.setUserAgent(device.userAgent);
    
    // 设置视口
    await page.setViewportSize(device.viewport);
    
    // 运行测试
    await runTests();
    
    // 生成报告
    await generateReport(device.name);
  }
};
```

### Android设备测试

#### 测试设备列表
- Samsung Galaxy S21 (Android 11)
- Google Pixel 6 (Android 12)
- OnePlus 9 Pro (Android 11)
- Samsung Galaxy Tab S8 (Android 12)

#### Android测试配置
```typescript
// Android测试配置
const androidDevices = [
  {
    name: 'Samsung Galaxy S21',
    userAgent: 'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
    viewport: { width: 360, height: 800 }
  },
  {
    name: 'Google Pixel 6',
    userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
    viewport: { width: 412, height: 915 }
  }
];
```

#### Android测试执行
```typescript
// Android测试执行
const runAndroidTests = async () => {
  for (const device of androidDevices) {
    console.log(`Testing on ${device.name}`);
    
    // 设置用户代理
    await page.setUserAgent(device.userAgent);
    
    // 设置视口
    await page.setViewportSize(device.viewport);
    
    // 运行测试
    await runTests();
    
    // 生成报告
    await generateReport(device.name);
  }
};
```

---

## 测试自动化

### CI/CD集成

#### GitHub Actions配置
```yaml
# GitHub Actions配置
name: Mobile Tests

on: [push, pull_request]

jobs:
  mobile-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        device: ['iPhone 12 Pro', 'Samsung Galaxy S21', 'Google Pixel 6']
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm ci
      - name: Run mobile tests
        run: npm run test:mobile -- --device="${{ matrix.device }}"
      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: test-results-${{ matrix.device }}
          path: test-results/
```

#### 测试脚本
```json
// package.json
{
  "scripts": {
    "test:mobile": "playwright test --project=mobile",
    "test:ios": "playwright test --project='Mobile Safari'",
    "test:android": "playwright test --project='Mobile Chrome'",
    "test:all-devices": "playwright test --project='Mobile Chrome' --project='Mobile Safari'"
  }
}
```

### 测试报告

#### 测试报告生成
```typescript
// 测试报告生成
const generateTestReport = (testResults: TestResults) => {
  const report = {
    summary: {
      total: testResults.total,
      passed: testResults.passed,
      failed: testResults.failed,
      skipped: testResults.skipped,
      duration: testResults.duration
    },
    device: testResults.device,
    browser: testResults.browser,
    platform: testResults.platform,
    timestamp: new Date().toISOString(),
    results: testResults.results
  };

  // 生成HTML报告
  const htmlReport = generateHTMLReport(report);
  
  // 生成JSON报告
  const jsonReport = JSON.stringify(report, null, 2);
  
  // 保存报告
  fs.writeFileSync('test-report.html', htmlReport);
  fs.writeFileSync('test-report.json', jsonReport);
  
  return report;
};
```

#### 测试报告展示
```typescript
// 测试报告展示组件
const TestReport = ({ report }: { report: TestReport }) => {
  return (
    <div className="test-report">
      <h2>Test Report</h2>
      <div className="summary">
        <div>Total: {report.summary.total}</div>
        <div>Passed: {report.summary.passed}</div>
        <div>Failed: {report.summary.failed}</div>
        <div>Skipped: {report.summary.skipped}</div>
        <div>Duration: {report.summary.duration}ms</div>
      </div>
      <div className="device-info">
        <div>Device: {report.device}</div>
        <div>Browser: {report.browser}</div>
        <div>Platform: {report.platform}</div>
      </div>
      <div className="results">
        {report.results.map((result, index) => (
          <div key={index} className={`test-result ${result.status}`}>
            <div>{result.name}</div>
            <div>{result.status}</div>
            <div>{result.duration}ms</div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 测试最佳实践

### 1. 测试组织
- 按功能模块组织测试
- 使用描述性的测试名称
- 保持测试独立和可重复

### 2. 测试覆盖
- 单元测试覆盖率≥70%
- 集成测试覆盖率≥60%
- E2E测试覆盖关键用户流程

### 3. 测试性能
- 使用并行测试提高效率
- 优化测试执行时间
- 避免不必要的等待

### 4. 测试维护
- 定期更新测试用例
- 移除过时的测试
- 保持测试代码质量

---

## 测试检查清单

### 功能测试
- [ ] 所有核心功能正常工作
- [ ] 用户交互流畅无卡顿
- [ ] 表单验证正确
- [ ] 错误处理正确

### 性能测试
- [ ] Lighthouse评分≥90
- [ ] LCP <2.5s
- [ ] FID <100ms
- [ ] CLS <0.1

### 兼容性测试
- [ ] iOS设备测试通过
- [ ] Android设备测试通过
- [ ] 不同浏览器测试通过
- [ ] 不同屏幕尺寸测试通过

### 可访问性测试
- [ ] 屏幕阅读器测试通过
- [ ] 键盘导航测试通过
- [ ] 触摸交互测试通过
- [ ] ARIA属性正确

---

## 测试故障排除

### 常见问题

#### 测试不稳定
```typescript
// 解决方案：增加重试机制
test('unstable test', async () => {
  await retry(3, async () => {
    // 测试逻辑
  });
});
```

#### 测试超时
```typescript
// 解决方案：增加超时时间
test('slow test', async () => {
  await slowOperation();
}, { timeout: 10000 });
```

#### 设备兼容性问题
```typescript
// 解决方案：设备特定测试
const deviceSpecificTest = (device: string) => {
  if (device === 'iPhone') {
    // iOS特定测试
  } else if (device === 'Android') {
    // Android特定测试
  }
};
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队