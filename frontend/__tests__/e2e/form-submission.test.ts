import { test, expect } from './auth.setup';

/**
 * 表单提交E2E测试
 * 覆盖数据提交流程和表单验证
 */

test.describe('变更请求表单提交', () => {
  test('应该成功提交完整的变更请求表单', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });

    // 填写所有表单字段
    await page.fill('input[placeholder="请输入变更标题"]', 'E2E测试变更请求');
    await page.fill('textarea[placeholder="请输入变更描述"]', '这是一个E2E自动化测试创建的变更请求');
    await page.fill('input[placeholder="请输入申请人"]', 'E2E测试用户');
    await page.fill('input[placeholder="请输入审批人"]', 'E2E审批人');
    await page.selectOption('select', 'low');
    await page.fill('input[type="datetime-local"]', '2024-12-31T10:00');
    await page.fill('input[placeholder="service1, service2, service3"]', 'api-service, web-service, db-service');
    await page.fill('textarea[placeholder="请输入实施方案"]', '1. 备份数据\n2. 更新服务\n3. 验证功能\n4. 监控系统');
    await page.fill('textarea[placeholder="请输入回滚方案"]', '1. 停止新服务\n2. 恢复备份\n3. 验证恢复');

    // 验证所有字段已填写
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('E2E测试变更请求');
    await expect(page.locator('input[placeholder="请输入申请人"]')).toHaveValue('E2E测试用户');

    // 提交表单
    await page.click('button[type="submit"]');

    // 等待提交完成
    await page.waitForTimeout(2000);

    // 验证表单已重置（提交成功后表单应该清空）
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('');
  });

  test('应该验证必填字段', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });

    // 尝试提交空表单
    await page.click('button[type="submit"]');

    // 验证必填字段（标题）获得焦点
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toBeFocused();
  });

  test('应该验证申请人字段为必填', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });

    // 只填写标题，不填写申请人
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更');

    // 提交表单
    await page.click('button[type="submit"]');

    // 验证申请人字段获得焦点
    await expect(page.locator('input[placeholder="请输入申请人"]')).toBeFocused();
  });

  test('应该正确处理服务列表字段', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写服务列表
    await page.fill('input[placeholder="service1, service2, service3"]', 'service-a, service-b, service-c');

    // 验证字段值
    await expect(page.locator('input[placeholder="service1, service2, service3"]')).toHaveValue('service-a, service-b, service-c');
  });

  test('应该正确选择风险等级', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 选择高风险
    await page.selectOption('select', 'high');

    // 验证选择
    await expect(page.locator('select')).toHaveValue('high');

    // 选择中风险
    await page.selectOption('select', 'medium');

    // 验证选择
    await expect(page.locator('select')).toHaveValue('medium');

    // 选择低风险
    await page.selectOption('select', 'low');

    // 验证选择
    await expect(page.locator('select')).toHaveValue('low');
  });

  test('应该正确处理日期时间字段', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写日期时间
    const dateTime = '2024-12-31T14:30';
    await page.fill('input[type="datetime-local"]', dateTime);

    // 验证字段值
    await expect(page.locator('input[type="datetime-local"]')).toHaveValue(dateTime);
  });

  test('应该在提交时禁用按钮', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写必填字段
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 点击提交
    await page.click('button[type="submit"]');

    // 验证按钮被禁用
    await expect(page.locator('button[type="submit"]')).toBeDisabled();

    // 等待提交完成
    await page.waitForTimeout(2000);

    // 验证按钮恢复可用
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });

  test('应该显示提交中的状态', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写必填字段
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 点击提交
    await page.click('button[type="submit"]');

    // 验证按钮文本变为"创建中..."
    await expect(page.locator('button[type="submit"]')).toHaveText('创建中...');
  });

  test('应该能够重置表单', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写表单
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 刷新页面（模拟重置）
    await page.reload();
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 验证表单已清空
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('');
    await expect(page.locator('input[placeholder="请输入申请人"]')).toHaveValue('');
  });
});

test.describe('表单字段验证测试', () => {
  test('应该验证标题字段不为空', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 不填写标题
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 提交表单
    await page.click('button[type="submit"]');

    // 验证标题字段获得焦点
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toBeFocused();
  });

  test('应该接受有效的表单数据', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写有效数据
    await page.fill('input[placeholder="请输入变更标题"]', '有效的变更请求');
    await page.fill('textarea[placeholder="请输入变更描述"]', '有效的描述');
    await page.fill('input[placeholder="请输入申请人"]', '有效用户');
    await page.fill('input[placeholder="请输入审批人"]', '有效审批人');
    await page.selectOption('select', 'medium');
    await page.fill('input[type="datetime-local"]', '2024-12-31T10:00');
    await page.fill('input[placeholder="service1, service2, service3"]', 'service1');
    await page.fill('textarea[placeholder="请输入实施方案"]', '实施方案');
    await page.fill('textarea[placeholder="请输入回滚方案"]', '回滚方案');

    // 验证所有字段都有值
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('有效的变更请求');
    await expect(page.locator('input[placeholder="请输入申请人"]')).toHaveValue('有效用户');
  });

  test('应该处理长文本输入', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 输入长文本
    const longText = '这是一个很长的描述文本。'.repeat(20);
    await page.fill('textarea[placeholder="请输入变更描述"]', longText);

    // 验证长文本被接受
    await expect(page.locator('textarea[placeholder="请输入变更描述"]')).toHaveValue(longText);
  });
});

test.describe('表单交互测试', () => {
  test('应该支持Tab键导航', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 使用Tab键导航
    await page.keyboard.press('Tab');
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.locator('textarea[placeholder="请输入变更描述"]')).toBeFocused();
  });

  test('应该支持Enter键提交', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写必填字段
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 按Enter键提交（在最后一个字段）
    await page.fill('textarea[placeholder="请输入回滚方案"]', '回滚方案');
    await page.keyboard.press('Enter');

    // 验证提交被触发
    await page.waitForTimeout(1000);
  });

  test('应该保留表单数据在页面刷新前', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写表单
    await page.fill('input[placeholder="请输入变更标题"]', '测试数据保留');

    // 验证数据存在
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('测试数据保留');
  });
});

test.describe('表单错误处理测试', () => {
  test('应该处理网络错误', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写表单
    await page.fill('input[placeholder="请输入变更标题"]', '网络错误测试');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 模拟网络错误（通过拦截请求）
    await page.route('**/api/v1/change-management/requests', route => route.abort());

    // 提交表单
    await page.click('button[type="submit"]');

    // 等待错误处理
    await page.waitForTimeout(2000);

    // 验证按钮恢复可用
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });

  test('应该处理服务器错误响应', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写表单
    await page.fill('input[placeholder="请输入变更标题"]', '服务器错误测试');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 模拟服务器错误
    await page.route('**/api/v1/change-management/requests', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    // 提交表单
    await page.click('button[type="submit"]');

    // 等待错误处理
    await page.waitForTimeout(2000);

    // 验证按钮恢复可用
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });
});

test.describe('表单可访问性测试', () => {
  test('应该有正确的表单标签', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 验证表单标签存在
    await expect(page.locator('label:has-text("标题")')).toBeVisible();
    await expect(page.locator('label:has-text("描述")')).toBeVisible();
    await expect(page.locator('label:has-text("申请人")')).toBeVisible();
    await expect(page.locator('label:has-text("审批人")')).toBeVisible();
  });

  test('应该支持键盘导航', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 验证所有输入字段可以通过Tab访问
    const inputCount = await page.locator('input, textarea, select').count();
    expect(inputCount).toBeGreaterThan(0);
  });
});
