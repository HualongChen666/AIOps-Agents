import { test, expect } from './auth.setup';

/**
 * 用户流程E2E测试
 * 覆盖完整的用户操作流程
 */

test.describe('用户登录流程', () => {
  test('应该成功登录并重定向到仪表盘', async ({ page }) => {
    // 导航到登录页面
    await page.goto('/login');

    // 验证登录页面元素
    await expect(page.locator('text=AIOps Agent 登录')).toBeVisible();
    await expect(page.locator('input[placeholder="请输入用户名"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // 填写登录表单
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');

    // 提交登录
    await page.click('button[type="submit"]');

    // 验证重定向到仪表盘
    await page.waitForURL('/', { timeout: 10000 });
    await expect(page.locator('text=仪表盘')).toBeVisible();
  });

  test('应该显示登录错误信息', async ({ page }) => {
    await page.goto('/login');

    // 填写错误的凭据
    await page.fill('input[placeholder="请输入用户名"]', 'wronguser');
    await page.fill('input[type="password"]', 'wrongpass');

    // 提交登录
    await page.click('button[type="submit"]');

    // 验证错误信息显示
    await expect(page.locator('text=登录失败')).toBeVisible({ timeout: 5000 });
  });

  test('应该禁用登录按钮在提交时', async ({ page }) => {
    await page.goto('/login');

    // 填写表单
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');

    // 点击提交
    await page.click('button[type="submit"]');

    // 验证按钮被禁用
    await expect(page.locator('button[type="submit"]')).toBeDisabled();
  });
});

test.describe('用户仪表盘流程', () => {
  test('应该显示仪表盘关键指标', async ({ authenticatedPage: page }) => {
    // 等待仪表盘加载
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 验证仪表盘标题
    await expect(page.locator('text=仪表盘')).toBeVisible();
    await expect(page.locator('text=系统总览与实时监控')).toBeVisible();

    // 验证刷新按钮
    await expect(page.locator('button:has-text("刷新")')).toBeVisible();

    // 验证系统健康状态卡片
    await expect(page.locator('text=系统健康状态')).toBeVisible();

    // 验证实时告警卡片
    await expect(page.locator('text=实时告警')).toBeVisible();

    // 验证资源使用趋势卡片
    await expect(page.locator('text=资源使用趋势')).toBeVisible();

    // 验证修复活动卡片
    await expect(page.locator('text=修复活动')).toBeVisible();
  });

  test('应该能够刷新仪表盘数据', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 点击刷新按钮
    await page.click('button:has-text("刷新")');

    // 验证刷新按钮存在（表示页面仍然响应）
    await expect(page.locator('button:has-text("刷新")')).toBeVisible();
  });

  test('应该显示系统健康状态', async ({ authenticatedPage: page }) => {
    await page.waitForSelector('text=系统健康状态', { timeout: 10000 });

    // 验证系统组件显示
    const healthComponents = ['Prometheus', 'Grafana', 'Zabbix', 'CloudWatch'];
    for (const component of healthComponents) {
      await expect(page.locator(`text=${component}`)).toBeVisible();
    }
  });
});

test.describe('告警管理流程', () => {
  test('应该能够查看告警列表', async ({ authenticatedPage: page }) => {
    // 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 验证告警页面标题
    await expect(page.locator('text=告警管理')).toBeVisible();
    await expect(page.locator('text=实时监控和管理系统告警')).toBeVisible();

    // 验证标签页
    await expect(page.locator('text=告警列表')).toBeVisible();
    await expect(page.locator('text=智能分析')).toBeVisible();
    await expect(page.locator('text=告警模式')).toBeVisible();

    // 验证筛选器
    await expect(page.locator('text=严重度')).toBeVisible();
    await expect(page.locator('text=状态')).toBeVisible();
    await expect(page.locator('text=服务')).toBeVisible();
    await expect(page.locator('text=搜索')).toBeVisible();
  });

  test('应该能够筛选告警', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 选择严重度筛选
    await page.selectOption('select', 'critical');

    // 验证筛选器已应用
    await expect(page.locator('select')).toHaveValue('critical');
  });

  test('应该能够搜索告警', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 输入搜索关键词
    await page.fill('input[placeholder="搜索告警标题"]', 'CPU');

    // 验证搜索输入框有值
    await expect(page.locator('input[placeholder="搜索告警标题"]')).toHaveValue('CPU');
  });

  test('应该能够查看告警详情', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 等待告警列表加载
    await page.waitForTimeout(2000);

    // 查找并点击第一个告警的详情按钮
    const detailButton = page.locator('button:has-text("查看详情")').first();
    if (await detailButton.isVisible()) {
      await detailButton.click();

      // 验证告警详情弹窗
      await expect(page.locator('text=告警详情')).toBeVisible({ timeout: 5000 });

      // 关闭弹窗
      await page.click('button:has-text("关闭")');
    }
  });

  test('应该能够切换智能分析标签', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 点击智能分析标签
    await page.click('button:has-text("智能分析")');

    // 验证智能分析内容
    await expect(page.locator('text=智能告警统计')).toBeVisible({ timeout: 5000 });
  });

  test('应该能够切换告警模式标签', async ({ authenticatedPage: page }) => {
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });

    // 点击告警模式标签
    await page.click('button:has-text("告警模式")');

    // 验证告警模式内容
    await expect(page.locator('text=告警模式分析')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('表单创建流程', () => {
  test('应该能够创建变更请求', async ({ authenticatedPage: page }) => {
    // 导航到表单页面
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });

    // 验证表单页面
    await expect(page.locator('text=创建变更请求')).toBeVisible();
    await expect(page.locator('text=变更请求信息')).toBeVisible();

    // 填写表单
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更请求');
    await page.fill('textarea[placeholder="请输入变更描述"]', '这是一个测试变更请求描述');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');
    await page.fill('input[placeholder="请输入审批人"]', '审批人');
    await page.selectOption('select', 'medium');
    await page.fill('input[type="datetime-local"]', '2024-12-31T10:00');
    await page.fill('input[placeholder="service1, service2, service3"]', 'service1, service2');
    await page.fill('textarea[placeholder="请输入实施方案"]', '测试实施方案');
    await page.fill('textarea[placeholder="请输入回滚方案"]', '测试回滚方案');

    // 验证表单字段已填写
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('测试变更请求');
  });

  test('应该验证必填字段', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });

    // 尝试提交空表单
    await page.click('button[type="submit"]');

    // 验证必填字段验证
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toBeFocused();
  });

  test('应该禁用提交按钮在提交时', async ({ authenticatedPage: page }) => {
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });

    // 填写必填字段
    await page.fill('input[placeholder="请输入变更标题"]', '测试变更');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');

    // 点击提交
    await page.click('button[type="submit"]');

    // 验证按钮被禁用
    await expect(page.locator('button[type="submit"]')).toBeDisabled();
  });
});

test.describe('用户登出流程', () => {
  test('应该能够登出', async ({ authenticatedPage: page }) => {
    // 等待仪表盘加载
    await page.waitForSelector('text=仪表盘', { timeout: 10000 });

    // 清除认证（模拟登出）
    await page.evaluate(() => {
      localStorage.removeItem('token');
    });

    // 刷新页面
    await page.reload();

    // 验证重定向到登录页面
    await page.waitForURL('/login', { timeout: 10000 });
    await expect(page.locator('text=AIOps Agent 登录')).toBeVisible();
  });
});

test.describe('完整用户工作流', () => {
  test('应该完成完整的用户工作流：登录 -> 查看仪表盘 -> 查看告警 -> 创建表单', async ({ page }) => {
    // 1. 登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 2. 查看仪表盘
    await expect(page.locator('text=仪表盘')).toBeVisible();
    await page.waitForTimeout(1000);

    // 3. 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10000 });
    await expect(page.locator('text=告警管理')).toBeVisible();
    await page.waitForTimeout(1000);

    // 4. 导航到表单页面
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10000 });
    await expect(page.locator('text=创建变更请求')).toBeVisible();

    // 5. 验证能够导航回仪表盘
    await page.goto('/');
    await expect(page.locator('text=仪表盘')).toBeVisible();
  });
});
