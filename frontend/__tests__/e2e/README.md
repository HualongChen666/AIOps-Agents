# E2E测试文档

## 概述

这个目录包含AIOps Agent前端应用的端到端(E2E)测试，使用Playwright框架编写。

## 测试文件

- `user-flows.test.ts` - 用户流程测试，覆盖完整的用户操作流程
- `navigation.test.ts` - 导航测试，覆盖跨页面交互场景
- `form-submission.test.ts` - 表单提交测试，覆盖数据提交流程
- `error-handling.test.ts` - 错误处理测试，覆盖异常情况处理
- `auth.setup.ts` - 认证设置，为需要认证的测试提供登录功能
- `helpers.ts` - 测试辅助函数

## 运行测试

### 运行所有E2E测试

```bash
npm run test:e2e
```

### 运行特定测试文件

```bash
npx playwright test user-flows.test.ts
```

### 运行特定测试用例

```bash
npx playwright test -g "应该成功登录并重定向到仪表盘"
```

### 使用UI模式运行测试

```bash
npm run test:e2e:ui
```

### 运行特定浏览器

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### 查看测试报告

```bash
npx playwright show-report
```

## 测试配置

测试配置在 `playwright.config.ts` 文件中：

- **基础URL**: `http://localhost:3000`
- **超时设置**: 操作超时10秒，导航超时30秒
- **重试策略**: CI环境中重试2次，本地环境不重试
- **追踪**: 第一次重试时启用追踪
- **截图**: 失败时截图
- **视频**: 失败时录制视频

## 测试覆盖范围

### 用户流程测试 (user-flows.test.ts)

- ✅ 用户登录流程
- ✅ 用户仪表盘流程
- ✅ 告警管理流程
- ✅ 表单创建流程
- ✅ 用户登出流程
- ✅ 完整用户工作流

### 导航测试 (navigation.test.ts)

- ✅ 页面导航测试
- ✅ 侧边栏导航测试
- ✅ 面包屑导航测试
- ✅ 浏览器导航测试
- ✅ URL直接访问测试
- ✅ 跨页面数据持久化测试
- ✅ 页面加载性能测试
- ✅ 多标签页导航测试

### 表单提交测试 (form-submission.test.ts)

- ✅ 变更请求表单提交
- ✅ 表单字段验证测试
- ✅ 表单交互测试
- ✅ 表单错误处理测试
- ✅ 表单可访问性测试

### 错误处理测试 (error-handling.test.ts)

- ✅ 认证错误处理
- ✅ 网络错误处理
- ✅ 页面加载错误处理
- ✅ 表单错误处理
- ✅ API错误处理
- ✅ 数据加载错误处理
- ✅ 边界条件错误处理
- ✅ 错误恢复测试

## 测试统计

- **测试文件数**: 4
- **测试用例数**: 50+
- **覆盖页面数**: 10+
- **覆盖用户流程**: 6+

## 前置条件

1. 确保后端API服务正在运行
2. 确保前端开发服务器可以启动
3. 确保有有效的测试用户凭据（默认: admin/admin123）

## 注意事项

1. E2E测试会启动开发服务器，确保端口3000未被占用
2. 测试过程中会创建和修改数据，建议使用测试环境
3. 某些测试可能需要真实的API响应
4. 测试运行时间可能较长，建议在CI/CD中运行

## 故障排除

### 测试超时

如果测试经常超时，可以增加超时时间：

```typescript
// playwright.config.ts
use: {
  actionTimeout: 20000,  // 增加到20秒
  navigationTimeout: 60000,  // 增加到60秒
}
```

### API请求失败

如果API请求失败，检查：
1. 后端服务是否正在运行
2. API端点是否正确
3. 认证凭据是否有效

### 浏览器启动失败

如果浏览器启动失败，尝试：
```bash
npx playwright install
```

## 持续集成

在CI/CD环境中运行E2E测试：

```yaml
# .github/workflows/e2e.yml
- name: Run E2E tests
  run: npm run test:e2e
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v2
  with:
    name: playwright-report
    path: playwright-report/
```

## 贡献指南

添加新的E2E测试时：

1. 确定测试类型（用户流程、导航、表单、错误处理）
2. 在相应的测试文件中添加测试用例
3. 使用描述性的测试名称
4. 添加必要的注释说明测试目的
5. 确保测试独立且可重复运行
