# -*- coding: utf-8 -*-
# tests/e2e/test_alert_workflow.py
# Alert workflow end-to-end tests
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.e2e
async def test_alert_creation_workflow(page, base_url, api_base_url):
    """测试告警创建工作流"""

    # 导航到仪表盘
    await page.goto(f"{base_url}/dashboard")
    await page.wait_for_load_state("networkidle")

    # 验证仪表盘加载
    assert await page.title() != ""

    # 点击创建告警按钮
    await page.click('[data-testid="create-alert-button"]')
    await page.wait_for_selector('[data-testid="alert-form"]')

    # 填写告警表单
    await page.fill('[data-testid="alert-title-input"]', "Test Alert")
    await page.select_option('[data-testid="alert-severity-select"]', "high")
    await page.fill('[data-testid="alert-description-input"]', "This is a test alert")

    # 提交表单
    await page.click('[data-testid="submit-alert-button"]')

    # 等待成功消息
    await page.wait_for_selector('[data-testid="alert-success-message"]')

    # 验证告警创建成功
    success_message = await page.text_content('[data-testid="alert-success-message"]')
    assert "success" in success_message.lower() or "成功" in success_message


@pytest.mark.e2e
async def test_alert_list_pagination(page, base_url):
    """测试告警列表分页"""

    # 导航到告警列表
    await page.goto(f"{base_url}/alerts")
    await page.wait_for_load_state("networkidle")

    # 验证告警列表加载
    await page.wait_for_selector('[data-testid="alert-list"]')

    # 检查是否有分页控件
    pagination = await page.query_selector('[data-testid="pagination"]')
    if pagination:
        # 点击下一页
        await page.click('[data-testid="next-page"]')
        await page.wait_for_load_state("networkidle")

        # 验证页面变化
        current_page = await page.text_content('[data-testid="current-page"]')
        assert current_page is not None


@pytest.mark.e2e
async def test_alert_filtering(page, base_url):
    """测试告警过滤功能"""

    # 导航到告警列表
    await page.goto(f"{base_url}/alerts")
    await page.wait_for_load_state("networkidle")

    # 选择严重程度过滤器
    await page.select_option('[data-testid="severity-filter"]', "high")
    await page.wait_for_load_state("networkidle")

    # 验证过滤结果
    alert_items = await page.query_selector_all('[data-testid="alert-item"]')

    # 验证所有告警都是高严重程度
    for item in alert_items:
        severity = await item.get_attribute("data-severity")
        assert severity == "high"


@pytest.mark.e2e
async def test_alert_detail_view(page, base_url):
    """测试告警详情查看"""

    # 导航到告警列表
    await page.goto(f"{base_url}/alerts")
    await page.wait_for_load_state("networkidle")

    # 点击第一个告警
    await page.click('[data-testid="alert-item"]:first-child')
    await page.wait_for_selector('[data-testid="alert-detail"]')

    # 验证详情页加载
    detail_title = await page.text_content('[data-testid="alert-detail-title"]')
    assert detail_title is not None

    # 验证详情信息显示
    assert await page.query_selector('[data-testid="alert-timestamp"]')
    assert await page.query_selector('[data-testid="alert-severity"]')


@pytest.mark.e2e
async def test_alert_resolution_workflow(page, base_url):
    """测试告警解决工作流"""

    # 导航到告警列表
    await page.goto(f"{base_url}/alerts")
    await page.wait_for_load_state("networkidle")

    # 点击第一个告警
    await page.click('[data-testid="alert-item"]:first-child')
    await page.wait_for_selector('[data-testid="alert-detail"]')

    # 点击解决按钮
    await page.click('[data-testid="resolve-alert-button"]')

    # 填写解决表单
    await page.fill('[data-testid="resolution-notes"]', "Issue resolved by automated test")

    # 提交解决
    await page.click('[data-testid="submit-resolution"]')

    # 验证解决成功
    await page.wait_for_selector('[data-testid="resolution-success"]')
    success_message = await page.text_content('[data-testid="resolution-success"]')
    assert "resolved" in success_message.lower() or "解决" in success_message
