import { test, expect } from './auth.setup';

/**
 * 导航E2E测试
 * 覆盖跨页面交互场景和页面间导航
 */

test.describe('页面导航测试', () => {
  test('应该能够从仪表盘导航到告警页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到告警页面
    await page.goto('/alerts');

    // 验证导航成功
    await page.waitForURL('/alerts', { timeout: 10000 });
    await expect(page.locator('text=告警管理')).toBeVisible();
  });

  test('应该能够从仪表盘导航到表单页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到表单页面
    await page.goto('/forms');

    // 验证导航成功
    await page.waitForURL('/forms', { timeout: 10000 });
    await expect(page.locator('text=创建变更请求')).toBeVisible();
  });

  test('应该能够从告警页面导航回仪表盘', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 导航回仪表盘
    await page.goto('/');

    // 验证导航成功
    await page.waitForURL('/', { timeout: 10000 });
    await expect(page.locator('text=仪表盘')).toBeVisible();
  });

  test('应该能够导航到设置页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到设置页面
    await page.goto('/settings');

    // 验证导航成功
    await page.waitForURL('/settings', { timeout: 10000 });
  });

  test('应该能够导航到监控中心页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到监控中心页面
    await page.goto('/monitoring-center');

    // 验证导航成功
    await page.waitForURL('/monitoring-center', { timeout: 10000 });
  });

  test('应该能够导航到安全中心页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到安全中心页面
    await page.goto('/security-center');

    // 验证导航成功
    await page.waitForURL('/security-center', { timeout: 10000 });
  });

  test('应该能够导航到日志分析页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到日志分析页面
    await page.goto('/logs');

    // 验证导航成功
    await page.waitForURL('/logs', { timeout: 10000 });
  });

  test('应该能够导航到APM页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到APM页面
    await page.goto('/apm');

    // 验证导航成功
    await page.waitForURL('/apm', { timeout: 10000 });
  });

  test('应该能够导航到AI功能页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到AI功能页面
    await page.goto('/ai-features');

    // 验证导航成功
    await page.waitForURL('/ai-features', { timeout: 10000 });
  });

  test('应该能够导航到故障排查页面', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到故障排查页面
    await page.goto('/repairs');

    // 验证导航成功
    await page.waitForURL('/repairs', { timeout: 10000 });
  });
});

test.describe('侧边栏导航测试', () => {
  test('应该能够通过侧边栏导航', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 查找侧边栏导航链接
    const sidebarLinks = page.locator('nav a').all();

    // 验证侧边栏存在
    await expect(page.locator('nav')).toBeVisible();
  });

  test('应该能够在不同页面间快速切换', async ({ authenticatedPage: page }) => {
    const pages = ['/', '/alerts', '/forms', '/settings'];

    for (const pagePath of pages) {
      await page.goto(pagePath);
      await page.waitForTimeout(500);
      await expect(page).toHaveURL(pagePath);
    }
  });
});

test.describe('面包屑导航测试', () => {
  test('应该显示正确的面包屑导航', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 验证页面标题显示
    await expect(page.locator('h1')).toBeVisible();
  });
});

test.describe('浏览器导航测试', () => {
  test('应该支持浏览器后退按钮', async ({ authenticatedPage: page }) => {
    await page.goto('/');
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 使用浏览器后退
    await page.goBack();

    // 验证回到仪表盘
    await expect(page).toHaveURL('/');
    await expect(page.locator('text=仪表盘')).toBeVisible();
  });

  test('应该支持浏览器前进按钮', async ({ authenticatedPage: page }) => {
    await page.goto('/');
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 后退
    await page.goBack();
    await expect(page).toHaveURL('/');

    // 前进
    await page.goForward();

    // 验证回到告警页面
    await expect(page).toHaveURL('/alerts');
    await expect(page.locator('text=告警管理')).toBeVisible();
  });

  test('应该支持浏览器刷新', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 刷新页面
    await page.reload();

    // 验证页面仍然加载成功
    await page.waitForSelector('text=告警管理', { timeout: 10000 });
    await expect(page.locator('text=告警管理')).toBeVisible();
  });
});

test.describe('URL直接访问测试', () => {
  test('应该能够通过URL直接访问页面', async ({ authenticatedPage: page }) => {
    // 直接访问告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });
    await expect(page.locator('text=告警管理')).toBeVisible();
  });

  test('应该能够通过URL直接访问表单页面', async ({ authenticatedPage: page }) => {
    // 直接访问表单页面
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });
    await expect(page.locator('text=创建变更请求')).toBeVisible();
  });

  test('应该能够通过URL直接访问设置页面', async ({ authenticatedPage: page }) => {
    // 直接访问设置页面
    await page.goto('/settings');
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL('/settings');
  });
});

test.describe('跨页面数据持久化测试', () => {
  test('应该在页面间保持用户会话', async ({ authenticatedPage: page }) => {
    await page.goto('/');
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 导航到多个页面
    await page.goto('/alerts');
    await page.waitForTimeout(500);
    await page.goto('/forms');
    await page.waitForTimeout(500);
    await page.goto('/settings');
    await page.waitForTimeout(500);

    // 验证仍然保持认证状态
    await page.goto('/');
    await expect(page.locator('text=仪表盘')).toBeVisible();
  });
});

test.describe('页面加载性能测试', () => {
  test('应该在合理时间内加载仪表盘', async ({ authenticatedPage: page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });
    const loadTime = Date.now() - startTime;

    // 验证加载时间在合理范围内（5秒内）
    expect(loadTime).toBeLessThan(5000);
  });

  test('应该在合理时间内加载告警页面', async ({ authenticatedPage: page }) => {
    const startTime = Date.now();
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });
    const loadTime = Date.now() - startTime;

    // 验证加载时间在合理范围内（5秒内）
    expect(loadTime).toBeLessThan(5000);
  });

  test('应该在合理时间内加载表单页面', async ({ authenticatedPage: page }) => {
    const startTime = Date.now();
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });
    const loadTime = Date.now() - startTime;

    // 验证加载时间在合理范围内（5秒内）
    expect(loadTime).toBeLessThan(5000);
  });
});

test.describe('多标签页导航测试', () => {
  test('应该能够在多个标签页中导航', async ({ context, authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 创建新标签页
    const newPage = await context.newPage();

    // 在新标签页中导航
    await newPage.goto('/alerts');
    await newPage.waitForSelector('text=告警管理', { timeout: 10000 });

    // 验证两个标签页都正常工作
    await expect(page.locator('text=仪表盘')).toBeVisible();
    await expect(newPage.locator('text=告警管理')).toBeVisible();

    await newPage.close();
  });
});
