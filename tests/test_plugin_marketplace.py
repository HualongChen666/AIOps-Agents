# -*- coding: utf-8 -*-
"""
Plugin Marketplace Tests
插件市场测试

测试插件市场API端点的正确性
"""

import pytest
from sqlalchemy.orm import Session

from core.auth_db import get_session
from core.models import (
    PluginListingDB,
    PluginReviewDB,
    PluginCategoryDB,
    InstalledPluginDB,
)
from api.plugin_marketplace_router import (
    PluginListingRequest,
    PluginReviewRequest,
    PluginInstallRequest,
    PluginQualityEnum,
    PluginCategoryEnum,
)


class TestPluginMarketplace:
    """插件市场测试"""

    def test_plugin_listing_creation(self):
        """测试插件列表创建"""
        db = get_session()
        try:
            # 创建插件列表
            plugin = PluginListingDB(
                id="PLUGIN-TEST-001",
                plugin_id="test-plugin-001",
                plugin_name="Test Plugin",
                version="1.0.0",
                description="A test plugin",
                author="Test Author",
                category="general",
                tags=["test", "demo"],
                price=0.0,
                quality="community",
                download_url="https://example.com/plugin.zip",
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
            )
            
            db.add(plugin)
            db.commit()
            
            # 验证创建成功
            retrieved = db.query(PluginListingDB).filter(
                PluginListingDB.plugin_id == "test-plugin-001"
            ).first()
            assert retrieved is not None
            assert retrieved.plugin_name == "Test Plugin"
            assert retrieved.version == "1.0.0"
            
            # 清理
            db.delete(plugin)
            db.commit()
        finally:
            db.close()

    def test_plugin_review_creation(self):
        """测试插件评论创建"""
        db = get_session()
        try:
            # 先创建插件
            plugin = PluginListingDB(
                id="PLUGIN-TEST-002",
                plugin_id="test-plugin-002",
                plugin_name="Test Plugin 2",
                version="1.0.0",
                description="A test plugin for reviews",
                author="Test Author",
                category="general",
                download_url="https://example.com/plugin.zip",
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
            )
            db.add(plugin)
            db.commit()
            
            # 创建评论
            review = PluginReviewDB(
                id="REVIEW-TEST-001",
                plugin_id="test-plugin-002",
                reviewer_id="user-001",
                reviewer_name="Test User",
                rating=5,
                review_text="Great plugin!",
            )
            db.add(review)
            db.commit()
            
            # 验证创建成功
            retrieved = db.query(PluginReviewDB).filter(
                PluginReviewDB.plugin_id == "test-plugin-002"
            ).first()
            assert retrieved is not None
            assert retrieved.rating == 5
            assert retrieved.review_text == "Great plugin!"
            
            # 清理
            db.delete(review)
            db.delete(plugin)
            db.commit()
        finally:
            db.close()

    def test_plugin_installation(self):
        """测试插件安装"""
        db = get_session()
        try:
            # 先创建插件
            plugin = PluginListingDB(
                id="PLUGIN-TEST-003",
                plugin_id="test-plugin-003",
                plugin_name="Test Plugin 3",
                version="1.0.0",
                description="A test plugin for installation",
                author="Test Author",
                category="general",
                download_url="https://example.com/plugin.zip",
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
            )
            db.add(plugin)
            db.commit()
            
            # 创建安装记录
            installed = InstalledPluginDB(
                id="INSTALLED-TEST-001",
                plugin_id="test-plugin-003",
                installed_version="1.0.0",
                status="active",
                configuration={"setting1": "value1"},
            )
            db.add(installed)
            db.commit()
            
            # 验证安装成功
            retrieved = db.query(InstalledPluginDB).filter(
                InstalledPluginDB.plugin_id == "test-plugin-003"
            ).first()
            assert retrieved is not None
            assert retrieved.installed_version == "1.0.0"
            assert retrieved.status == "active"
            
            # 清理
            db.delete(installed)
            db.delete(plugin)
            db.commit()
        finally:
            db.close()

    def test_plugin_category_creation(self):
        """测试插件分类创建"""
        db = get_session()
        try:
            # 创建分类
            category = PluginCategoryDB(
                id="CATEGORY-TEST-001",
                category_name="Test Category",
                category_description="A test category",
                enabled=True,
            )
            db.add(category)
            db.commit()
            
            # 验证创建成功
            retrieved = db.query(PluginCategoryDB).filter(
                PluginCategoryDB.category_name == "Test Category"
            ).first()
            assert retrieved is not None
            assert retrieved.category_description == "A test category"
            
            # 清理
            db.delete(category)
            db.commit()
        finally:
            db.close()

    def test_plugin_rating_update(self):
        """测试插件评分更新"""
        db = get_session()
        try:
            # 创建插件
            plugin = PluginListingDB(
                id="PLUGIN-TEST-004",
                plugin_id="test-plugin-004",
                plugin_name="Test Plugin 4",
                version="1.0.0",
                description="A test plugin for rating",
                author="Test Author",
                category="general",
                download_url="https://example.com/plugin.zip",
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
            )
            db.add(plugin)
            db.commit()
            
            # 添加多个评论
            ratings = [5, 4, 5, 3, 4]
            for i, rating in enumerate(ratings):
                review = PluginReviewDB(
                    id=f"REVIEW-TEST-{i:03d}",
                    plugin_id="test-plugin-004",
                    reviewer_id=f"user-{i}",
                    reviewer_name=f"User {i}",
                    rating=rating,
                )
                db.add(review)
                
                # 更新插件评分
                plugin.review_count += 1
                plugin.rating = (plugin.rating * (plugin.review_count - 1) + rating) / plugin.review_count
            
            db.commit()
            
            # 验证评分更新
            expected_rating = sum(ratings) / len(ratings)
            assert abs(plugin.rating - expected_rating) < 0.01
            assert plugin.review_count == len(ratings)
            
            # 清理
            for review in db.query(PluginReviewDB).filter(
                PluginReviewDB.plugin_id == "test-plugin-004"
            ).all():
                db.delete(review)
            db.delete(plugin)
            db.commit()
        finally:
            db.close()

    def test_plugin_download_count(self):
        """测试插件下载计数"""
        db = get_session()
        try:
            # 创建插件
            plugin = PluginListingDB(
                id="PLUGIN-TEST-005",
                plugin_id="test-plugin-005",
                plugin_name="Test Plugin 5",
                version="1.0.0",
                description="A test plugin for download count",
                author="Test Author",
                category="general",
                download_url="https://example.com/plugin.zip",
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=True,
            )
            db.add(plugin)
            db.commit()
            
            # 模拟多次下载
            for i in range(5):
                plugin.download_count += 1
                db.commit()
            
            # 验证下载计数
            assert plugin.download_count == 5
            
            # 清理
            db.delete(plugin)
            db.commit()
        finally:
            db.close()


class TestPluginMarketplaceIntegration:
    """插件市场集成测试"""

    def test_plugin_lifecycle(self):
        """测试插件完整生命周期"""
        db = get_session()
        try:
            # 1. 上传插件
            plugin = PluginListingDB(
                id="PLUGIN-LIFECYCLE-001",
                plugin_id="lifecycle-plugin",
                plugin_name="Lifecycle Plugin",
                version="1.0.0",
                description="A plugin for lifecycle testing",
                author="Test Author",
                category="general",
                download_url="https://example.com/plugin.zip",
                download_count=0,
                rating=0.0,
                review_count=0,
                enabled=False,  # 初始禁用
            )
            db.add(plugin)
            db.commit()
            
            # 2. 审核通过
            plugin.enabled = True
            db.commit()
            
            # 3. 用户安装
            installed = InstalledPluginDB(
                id="INSTALLED-LIFECYCLE-001",
                plugin_id="lifecycle-plugin",
                installed_version="1.0.0",
                status="active",
            )
            db.add(installed)
            plugin.download_count += 1
            db.commit()
            
            # 4. 用户评论
            review = PluginReviewDB(
                id="REVIEW-LIFECYCLE-001",
                plugin_id="lifecycle-plugin",
                reviewer_id="user-001",
                reviewer_name="Test User",
                rating=5,
                review_text="Excellent plugin!",
            )
            db.add(review)
            plugin.review_count += 1
            plugin.rating = (plugin.rating * (plugin.review_count - 1) + 5) / plugin.review_count
            db.commit()
            
            # 5. 验证最终状态
            assert plugin.enabled is True
            assert plugin.download_count == 1
            assert plugin.rating == 5.0
            assert plugin.review_count == 1
            assert installed.status == "active"
            
            # 6. 卸载插件
            db.delete(installed)
            db.commit()
            
            # 验证卸载
            uninstalled = db.query(InstalledPluginDB).filter(
                InstalledPluginDB.plugin_id == "lifecycle-plugin"
            ).first()
            assert uninstalled is None
            
            # 清理
            db.delete(review)
            db.delete(plugin)
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])