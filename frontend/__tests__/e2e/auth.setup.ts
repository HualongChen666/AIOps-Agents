import { test as base } from '@playwright/test';

/**
 * 认证扩展 - 为需要认证的测试提供登录功能
 */
export const test = base.extend<{
  authenticatedPage: typeof base['page'];
}>({
  authenticatedPage: async ({ page }, use) => {
    // 导航到登录页面
    await page.goto('/login');

    // 填写登录表单
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');

    // 提交登录
    await page.click('button[type="submit"]');

    // 等待导航到仪表盘
    await page.waitForURL('/', { timeout: 10000 });

    // 使用认证后的页面
    await use(page);
  },
});

export const expect = base.expect;
