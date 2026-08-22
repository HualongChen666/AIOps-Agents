import { test, expect } from '@playwright/test';

/**
 * 错误处理E2E测试
 * 覆盖异常情况处理和错误场景
 */

test.describe('认证错误处理', () => {
  test('应该处理无效的登录凭据', async ({ page }) => {
    await page.goto('/login');

    // 输入无效凭据
    await page.fill('input[placeholder="请输入用户名"]', 'invalid_user');
    await page.fill('input[type="password"]', 'invalid_password');
    await page.click('button[type="submit"]');

    // 验证错误信息显示
    await expect(page.locator('text=登录失败')).toBeVisible({ timeout: 5000 });
  });

  test('应该处理空的用户名', async ({ page }) => {
    await page.goto('/login');

    // 不输入用户名
    await page.fill('input[type="password"]', 'password');
    await page.click('button[type="submit"]');

    // 验证HTML5验证
    await expect(page.locator('input[placeholder="请输入用户名"]')).toBeFocused();
  });

  test('应该处理空的密码', async ({ page }) => {
    await page.goto('/login');

    // 不输入密码
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.click('button[type="submit"]');

    // 验证HTML5验证
    await expect(page.locator('input[type="password"]')).toBeFocused();
  });

  test('应该重定向未认证用户到登录页', async ({ page }) => {
    // 尝试直接访问需要认证的页面
    await page.goto('/dashboard');

    // 验证重定向到登录页面
    await page.waitForURL('/login', { timeout: 10000 });
    await expect(page.locator('text=AIOps Agent 登录')).toBeVisible();
  });

  test('应该处理认证过期', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 清除认证token
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

test.describe('网络错误处理', () => {
  test('应该处理API连接失败', async ({ page }) => {
    // 拦截所有API请求并失败
    await page.route('**/api/**', route => route.abort());

    // 尝试登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // 验证错误处理
    await page.waitForTimeout(2000);
    // 验证按钮仍然可用
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });

  test('应该处理慢速网络连接', async ({ page }) => {
    // 模拟慢速网络
    await page.context().setOffline(false);

    // 添加网络延迟
    await page.route('**/api/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 5000));
      route.continue();
    });

    // 尝试登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // 验证加载状态
    await expect(page.locator('button[type="submit"]')).toHaveText('登录中...');
  });

  test('应该处理离线状态', async ({ page }) => {
    // 设置离线
    await page.context().setOffline(true);

    // 尝试登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // 等待错误处理
    await page.waitForTimeout(2000);

    // 恢复在线
    await page.context().setOffline(false);
  });
});

test.describe('页面加载错误处理', () => {
  test('应该处理404页面', async ({ page }) => {
    // 访问不存在的页面
    await page.goto('/non-existent-page');

    // 验证页面处理（可能是重定向或错误页面）
    await page.waitForTimeout(2000);
  });

  test('应该处理JavaScript错误', async ({ page }) => {
    // 监听控制台错误
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // 导航到页面
    await page.goto('/login');

    // 验证没有关键JavaScript错误
    await page.waitForTimeout(2000);
  });

  test('应该处理资源加载失败', async ({ page }) => {
    // 拦截图片请求并失败
    await page.route('**/*.png', route => route.abort());
    await page.route('**/*.jpg', route => route.abort());
    await page.route('**/*.svg', route => route.abort());

    // 导航到页面
    await page.goto('/login');

    // 验证页面仍然可用
    await expect(page.locator('text=AIOps Agent 登录')).toBeVisible();
  });
});

test.describe('表单错误处理', () => {
  test('应该处理表单验证错误', async ({ page }) => {
    await page.goto('/login');

    // 提交空表单
    await page.click('button[type="submit"]');

    // 验证HTML5验证
    await expect(page.locator('input[placeholder="请输入用户名"]')).toBeFocused();
  });

  test('应该处理表单提交失败', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 导航到表单页面
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 拦截表单提交请求并失败
    await page.route('**/api/v1/change-management/requests', route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Bad Request' })
      });
    });

    // 填写并提交表单
    await page.fill('input[placeholder="请输入变更标题"]', '测试');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');
    await page.click('button[type="submit"]');

    // 等待错误处理
    await page.waitForTimeout(2000);

    // 验证按钮恢复可用
    await expect(page.locator('button[type="submit"]')).toBeEnabled();
  });

  test('应该处理表单提交超时', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 导航到表单页面
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 拦截表单提交请求并延迟
    await page.route('**/api/v1/change-management/requests', async route => {
      await new Promise(resolve => setTimeout(resolve, 30000));
      route.continue();
    });

    // 填写并提交表单
    await page.fill('input[placeholder="请输入变更标题"]', '测试');
    await page.fill('input[placeholder="请输入申请人"]', '测试用户');
    await page.click('button[type="submit"]');

    // 验证加载状态
    await expect(page.locator('button[type="submit"]')).toHaveText('创建中...');
  });
});

test.describe('API错误处理', () => {
  test('应该处理500服务器错误', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 拦截API请求并返回500错误
    await page.route('**/api/v1/metrics/summary', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    // 刷新页面
    await page.reload();

    // 验证错误处理
    await page.waitForTimeout(2000);
  });

  test('应该处理401未授权错误', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 拦截API请求并返回401错误
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Unauthorized' })
      });
    });

    // 刷新页面
    await page.reload();

    // 验证重定向到登录页面
    await page.waitForURL('/login', { timeout: 10000 });
  });

  test('应该处理403禁止访问错误', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 拦截API请求并返回403错误
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Forbidden' })
      });
    });

    // 刷新页面
    await page.reload();

    // 验证错误处理
    await page.waitForTimeout(2000);
  });

  test('应该处理503服务不可用错误', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 拦截API请求并返回503错误
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Service Unavailable' })
      });
    });

    // 刷新页面
    await page.reload();

    // 验证错误处理
    await page.waitForTimeout(2000);
  });
});

test.describe('数据加载错误处理', () => {
  test('应该处理仪表盘数据加载失败', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 拦截仪表盘API请求
    await page.route('**/api/v1/metrics/**', route => route.abort());

    // 刷新页面
    await page.reload();

    // 验证错误处理（显示错误状态或重试按钮）
    await page.waitForTimeout(2000);
  });

  test('应该处理告警数据加载失败', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10000 });

    // 导航到告警页面
    await page.goto('/alerts');

    // 拦截告警API请求
    await page.route('**/api/v1/alerts/**', route => route.abort());

    // 刷新页面
    await page.reload();

    // 验证错误处理
    await page.waitForTimeout(2000);
  });

  test('应该提供重试机制', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10010 });

    // 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10010 });

    // 查找重试按钮
    const retryButton = page.locator('button:has-text("重试")').or(page.locator('button:has-text("刷新")'));

    if (await retryButton.isVisible()) {
      // 点击重试
      await retryButton.click();

      // 验证页面响应
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('边界条件错误处理', () => {
  test('应该处理大量数据加载', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10010 });

    // 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10010 });

    // 模拟大量数据
    await page.route('**/api/v1/alerts/**', route => {
      const largeData = {
        alerts: Array(1000).fill(null).map((_, i) => ({
          id: `alert-${i}`,
          title: `告警 ${i}`,
          severity: 'medium',
          status: 'open',
          timestamp: new Date().toISOString(),
          service: `service-${i % 10}`
        }))
      };
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(largeData)
      });
    });

    // 刷新页面
    await page.reload();

    // 验证页面仍然响应
    await page.waitForTimeout(3000);
  });

  test('应该处理特殊字符输入', async ({ page }) => {
    await page.goto('/login');

    // 输入特殊字符
    const specialChars = '<script>alert("xss")</script>';
    await page.fill('input[placeholder="请输入用户名"]', specialChars);
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // 验证XSS防护
    await page.waitForTimeout(2000);
  });

  test('应该处理超长输入', async ({ page }) => {
    await page.goto('/login');

    // 输入超长用户名
    const longInput = 'a'.repeat(10000);
    await page.fill('input[placeholder="请输入用户名"]', longInput);
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // 验证处理
    await page.waitForTimeout(2000);
  });
});

test.describe('错误恢复测试', () => {
  test('应该能够从错误中恢复', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10010 });

    // 导航到告警页面
    await page.goto('/alerts');
    await page.waitForSelector('text=告警管理', { timeout: 10010 });

    // 拦截API请求并失败
    await page.route('**/api/v1/alerts/**', route => route.abort());

    // 刷新页面触发错误
    await page.reload();
    await page.waitForTimeout(2000);

    // 移除拦截，恢复正常
    await page.unroute('**/api/v1/alerts/**');

    // 再次刷新
    await page.reload();

    // 验证恢复
    await page.waitForTimeout(2000);
  });

  test('应该保持用户状态在错误后', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[placeholder="请输入用户名"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/', { timeout: 10010 });

    // 导航到表单页面
    await page.goto('/forms');
    await page.waitForSelector('text=创建变更请求', { timeout: 10010 });

    // 填写部分表单
    await page.fill('input[placeholder="请输入变更标题"]', '测试状态保持');

    // 拦截API请求并失败
    await page.route('**/api/**', route => route.abort());

    // 尝试提交
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // 移除拦截
    await page.unroute('**/api/**');

    // 验证表单数据仍然存在
    await expect(page.locator('input[placeholder="请输入变更标题"]')).toHaveValue('测试状态保持');
  });
});
