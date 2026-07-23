# -*- coding: utf-8 -*-
# tests/e2e/test_authentication_workflow.py
# Authentication workflow end-to-end tests
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.e2e
async def test_user_login_workflow(page, base_url):
    """测试用户登录工作流"""

    # 导航到登录页面
    await page.goto(f"{base_url}/login")
    await page.wait_for_load_state("networkidle")

    # 验证登录页面加载
    assert await page.title() != ""

    # 填写登录表单
    await page.fill('[data-testid="username-input"]', "admin")
    await page.fill('[data-testid="password-input"]', "admin123")

    # 提交登录
    await page.click('[data-testid="login-button"]')

    # 等待登录成功重定向
    await page.wait_for_load_state("networkidle")

    # 验证登录成功（应该重定向到仪表盘）
    current_url = page.url
    assert "/dashboard" in current_url or "/login" not in current_url


@pytest.mark.e2e
async def test_user_logout_workflow(page, base_url):
    """测试用户登出工作流"""

    # 先登录
    await page.goto(f"{base_url}/login")
    await page.fill('[data-testid="username-input"]', "admin")
    await page.fill('[data-testid="password-input"]', "admin123")
    await page.click('[data-testid="login-button"]')
    await page.wait_for_load_state("networkidle")

    # 点击登出按钮
    await page.click('[data-testid="logout-button"]')
    await page.wait_for_load_state("networkidle")

    # 验证登出成功（应该重定向到登录页面）
    current_url = page.url
    assert "/login" in current_url


@pytest.mark.e2e
async def test_jwt_token_validation(page, base_url, api_base_url):
    """测试JWT令牌验证"""

    # 登录获取令牌
    await page.goto(f"{base_url}/login")
    await page.fill('[data-testid="username-input"]', "admin")
    await page.fill('[data-testid="password-input"]', "admin123")
    await page.click('[data-testid="login-button"]')
    await page.wait_for_load_state("networkidle")

    # 验证登录成功后可以访问需要认证的页面
    # 如果JWT令牌验证正常，用户应该能够访问受保护的资源
    current_url = page.url
    assert "/login" not in current_url, "登录后应该不在登录页面"

    # 尝试访问需要认证的API端点
    # 注意：这需要实际的API实现和JWT认证功能
    # 当前实现验证基本的登录流程，完整的JWT令牌验证需要API端点支持
    # 当JWT认证功能实现后，可以添加实际的API调用测试


@pytest.mark.e2e
async def test_password_change_workflow(page, base_url):
    """测试密码修改工作流"""

    # 登录
    await page.goto(f"{base_url}/login")
    await page.fill('[data-testid="username-input"]', "admin")
    await page.fill('[data-testid="password-input"]', "admin123")
    await page.click('[data-testid="login-button"]')
    await page.wait_for_load_state("networkidle")

    # 导航到用户设置
    await page.goto(f"{base_url}/settings")
    await page.wait_for_load_state("networkidle")

    # 点击修改密码
    await page.click('[data-testid="change-password-button"]')
    await page.wait_for_selector('[data-testid="password-change-form"]')

    # 填写密码修改表单
    await page.fill('[data-testid="current-password"]', "admin123")
    await page.fill('[data-testid="new-password"]', "newPassword123")
    await page.fill('[data-testid="confirm-password"]', "newPassword123")

    # 提交修改
    await page.click('[data-testid="submit-password-change"]')

    # 验证修改成功
    await page.wait_for_selector('[data-testid="password-change-success"]')


@pytest.mark.e2e
async def test_role_based_access_control(page, base_url):
    """测试基于角色的访问控制"""

    # 以普通用户身份登录
    await page.goto(f"{base_url}/login")
    await page.fill('[data-testid="username-input"]', "user")
    await page.fill('[data-testid="password-input"]', "user123")
    await page.click('[data-testid="login-button"]')
    await page.wait_for_load_state("networkidle")

    # 尝试访问管理员页面
    await page.goto(f"{base_url}/admin")
    await page.wait_for_load_state("networkidle")

    # 验证访问被拒绝
    current_url = page.url
    page_title = await page.title()
    assert "/forbidden" in current_url or "/403" in current_url or "access denied" in page_title
