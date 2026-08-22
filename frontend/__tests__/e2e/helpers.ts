import { Page, expect } from '@playwright/test';

/**
 * E2E测试辅助函数
 */

/**
 * 等待页面加载完成
 */
export async function waitForPageLoad(page: Page, timeout: number = 10000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * 登录到应用
 */
export async function login(page: Page, username: string = 'admin', password: string = 'admin123') {
  await page.goto('/login');
  await page.fill('input[placeholder="请输入用户名"]', username);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL('/', { timeout: 10000 });
}

/**
 * 导航到指定页面
 */
export async function navigateTo(page: Page, path: string) {
  await page.goto(path);
  await waitForPageLoad(page);
}

/**
 * 填写表单字段
 */
export async function fillFormField(page: Page, placeholder: string, value: string) {
  await page.fill(`input[placeholder="${placeholder}"]`, value);
}

/**
 * 选择下拉选项
 */
export async function selectOption(page: Page, selector: string, value: string) {
  await page.selectOption(selector, value);
}

/**
 * 点击按钮
 */
export async function clickButton(page: Page, text: string) {
  await page.click(`button:has-text("${text}")`);
}

/**
 * 验证元素可见
 */
export async function expectVisible(page: Page, selector: string) {
  await expect(page.locator(selector)).toBeVisible();
}

/**
 * 验证元素包含文本
 */
export async function expectText(page: Page, selector: string, text: string) {
  await expect(page.locator(selector)).toContainText(text);
}

/**
 * 等待元素出现
 */
export async function waitForElement(page: Page, selector: string, timeout: number = 5000) {
  await page.waitForSelector(selector, { timeout });
}

/**
 * 获取元素文本
 */
export async function getElementText(page: Page, selector: string): Promise<string> {
  return await page.locator(selector).textContent() || '';
}

/**
 * 验证URL
 */
export async function expectURL(page: Page, url: string) {
  await expect(page).toHaveURL(url);
}

/**
 * 截图
 */
export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `test-results/screenshots/${name}.png` });
}

/**
 * 模拟API响应
 */
export async function mockAPIResponse(page: Page, pattern: string, response: any) {
  await page.route(pattern, route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response)
    });
  });
}

/**
 * 模拟API错误
 */
export async function mockAPIError(page: Page, pattern: string, status: number = 500) {
  await page.route(pattern, route => {
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Error' })
    });
  });
}

/**
 * 清除所有mock
 */
export async function clearMocks(page: Page) {
  // Playwright会自动清理路由，这个函数用于语义化
}

/**
 * 等待指定时间
 */
export async function wait(ms: number) {
  await new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 获取当前URL
 */
export async function getCurrentURL(page: Page): Promise<string> {
  return page.url();
}

/**
 * 刷新页面
 */
export async function refreshPage(page: Page) {
  await page.reload();
}

/**
 * 后退
 */
export async function goBack(page: Page) {
  await page.goBack();
}

/**
 * 前进
 */
export async function goForward(page: Page) {
  await page.goForward();
}
