# -*- coding: utf-8 -*-
"""测试插件市场管理器模块"""

import pytest


class TestPluginMarketplaceManagerModule:
    """测试插件市场管理器模块"""

    def test_plugin_marketplace_manager_module_exists(self):
        """测试插件市场管理器模块存在"""
        from core import plugin_marketplace_manager

        assert plugin_marketplace_manager is not None

    def test_plugin_marketplace_manager_has_enums(self):
        """测试插件市场管理器模块有枚举"""
        from core import plugin_marketplace_manager

        # 检查模块有枚举
        assert hasattr(plugin_marketplace_manager, "PluginQuality")
        assert hasattr(plugin_marketplace_manager, "PluginReviewStatus")

    def test_plugin_marketplace_manager_has_typeddicts(self):
        """测试插件市场管理器模块有TypedDict"""
        from core import plugin_marketplace_manager

        # 检查模块有TypedDict
        assert hasattr(plugin_marketplace_manager, "QualityCheckResult")

    def test_plugin_marketplace_manager_has_dataclasses(self):
        """测试插件市场管理器模块有数据类"""
        from core import plugin_marketplace_manager

        # 检查模块有数据类
        assert hasattr(plugin_marketplace_manager, "PluginListing")
        assert hasattr(plugin_marketplace_manager, "PluginReview")

    def test_plugin_marketplace_manager_has_classes(self):
        """测试插件市场管理器模块有类"""
        from core import plugin_marketplace_manager

        # 检查模块有类
        assert hasattr(plugin_marketplace_manager, "PluginMarketplaceManager")

    def test_plugin_marketplace_manager_has_functions(self):
        """测试插件市场管理器模块有函数"""
        from core import plugin_marketplace_manager

        # 检查模块有函数
        assert hasattr(plugin_marketplace_manager, "get_marketplace_manager")


class TestPluginQuality:
    """测试插件质量枚举"""

    def test_plugin_quality_values(self):
        """测试插件质量值"""
        from core.plugin_marketplace_manager import PluginQuality

        assert PluginQuality.CERTIFIED.value == "certified"
        assert PluginQuality.VERIFIED.value == "verified"
        assert PluginQuality.COMMUNITY.value == "community"
        assert PluginQuality.EXPERIMENTAL.value == "experimental"


class TestPluginReviewStatus:
    """测试插件审核状态枚举"""

    def test_plugin_review_status_values(self):
        """测试插件审核状态值"""
        from core.plugin_marketplace_manager import PluginReviewStatus

        assert PluginReviewStatus.PENDING.value == "pending"
        assert PluginReviewStatus.APPROVED.value == "approved"
        assert PluginReviewStatus.REJECTED.value == "rejected"
        assert PluginReviewStatus.UNDER_REVIEW.value == "under_review"


class TestPluginListing:
    """测试插件列表数据类"""

    def test_plugin_listing_creation(self):
        """测试插件列表创建"""
        from core.plugin_marketplace_manager import (
            PluginListing,
            PluginQuality,
            PluginReviewStatus,
        )

        listing = PluginListing(
            plugin_id="plugin_1",
            plugin_name="Plugin 1",
            version="1.0.0",
            description="Test plugin",
            author="Author",
            quality=PluginQuality.COMMUNITY,
            review_status=PluginReviewStatus.PENDING,
        )

        assert listing.plugin_id == "plugin_1"
        assert listing.plugin_name == "Plugin 1"
        assert listing.quality == PluginQuality.COMMUNITY


class TestPluginReview:
    """测试插件审核数据类"""

    def test_plugin_review_creation(self):
        """测试插件审核创建"""
        from datetime import datetime, timezone

        from core.plugin_marketplace_manager import PluginReview

        review = PluginReview(
            review_id="review_1",
            plugin_id="plugin_1",
            reviewer="reviewer",
            rating=5,
            comment="Great plugin",
            timestamp=datetime.now(timezone.utc),
        )

        assert review.review_id == "review_1"
        assert review.plugin_id == "plugin_1"
        assert review.rating == 5


class TestPluginMarketplaceManager:
    """测试插件市场管理器类"""

    def test_plugin_marketplace_manager_initialization(self):
        """测试插件市场管理器初始化"""
        from core.plugin_marketplace_manager import PluginMarketplaceManager

        manager = PluginMarketplaceManager()

        assert manager.config == {}
        assert len(manager.listings) == 0
        assert len(manager.reviews) == 0

    def test_plugin_marketplace_manager_initialization_with_config(self):
        """测试插件市场管理器初始化（带配置）"""
        from core.plugin_marketplace_manager import PluginMarketplaceManager

        config = {"custom_key": "custom_value"}
        manager = PluginMarketplaceManager(config)

        assert manager.config == config

    def test_publish_plugin(self):
        """测试发布插件"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
            PluginReviewStatus,
        )

        manager = PluginMarketplaceManager()

        result = manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        assert result is True
        assert "plugin_1" in manager.listings
        assert manager.listings["plugin_1"].review_status == PluginReviewStatus.PENDING

    def test_publish_plugin_with_syntax_error(self):
        """测试发布插件（语法错误）"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        result = manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(:",  # Syntax error
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        assert result is True  # Still publishes but with quality issues
        assert manager.quality_checks["plugin_1"]["syntax_check"] is False

    def test_approve_plugin(self):
        """测试批准插件"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
            PluginReviewStatus,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        result = manager.approve_plugin("plugin_1", "reviewer_1")

        assert result is True
        assert manager.listings["plugin_1"].review_status == PluginReviewStatus.APPROVED

    def test_approve_plugin_invalid(self):
        """测试批准插件（无效）"""
        from core.plugin_marketplace_manager import PluginMarketplaceManager

        manager = PluginMarketplaceManager()

        result = manager.approve_plugin("invalid_plugin", "reviewer_1")

        assert result is False

    def test_reject_plugin(self):
        """测试拒绝插件"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
            PluginReviewStatus,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        result = manager.reject_plugin("plugin_1", "Test reason")

        assert result is True
        assert manager.listings["plugin_1"].review_status == PluginReviewStatus.REJECTED

    def test_reject_plugin_invalid(self):
        """测试拒绝插件（无效）"""
        from core.plugin_marketplace_manager import PluginMarketplaceManager

        manager = PluginMarketplaceManager()

        result = manager.reject_plugin("invalid_plugin", "reason")

        assert result is False

    def test_download_plugin(self):
        """测试下载插件"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        manager.approve_plugin("plugin_1", "reviewer_1")

        result = manager.download_plugin("plugin_1")

        assert result is not None
        assert result["plugin_id"] == "plugin_1"

    def test_download_plugin_not_approved(self):
        """测试下载插件（未批准）"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        result = manager.download_plugin("plugin_1")

        assert result is None

    def test_download_plugin_invalid(self):
        """测试下载插件（无效）"""
        from core.plugin_marketplace_manager import PluginMarketplaceManager

        manager = PluginMarketplaceManager()

        result = manager.download_plugin("invalid_plugin")

        assert result is None

    def test_add_review(self):
        """测试添加审核"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        result = manager.add_review(
            plugin_id="plugin_1",
            reviewer="reviewer_1",
            rating=5,
            comment="Great plugin",
        )

        assert result is True
        assert len(manager.reviews["plugin_1"]) == 1
        assert manager.listings["plugin_1"].review_count == 1

    def test_add_review_invalid_rating(self):
        """测试添加审核（无效评分）"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        result = manager.add_review(
            plugin_id="plugin_1",
            reviewer="reviewer_1",
            rating=6,  # Invalid rating
            comment="Great plugin",
        )

        assert result is False

    def test_add_review_invalid_plugin(self):
        """测试添加审核（无效插件）"""
        from core.plugin_marketplace_manager import PluginMarketplaceManager

        manager = PluginMarketplaceManager()

        result = manager.add_review(
            plugin_id="invalid_plugin",
            reviewer="reviewer_1",
            rating=5,
            comment="Great plugin",
        )

        assert result is False

    def test_get_plugin_listings(self):
        """测试获取插件列表"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        listings = manager.get_plugin_listings()

        assert len(listings) == 1

    def test_get_plugin_listings_with_filter(self):
        """测试获取插件列表（带过滤器）"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
            PluginReviewStatus,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        listings = manager.get_plugin_listings(
            quality=PluginQuality.COMMUNITY, review_status=PluginReviewStatus.PENDING
        )

        assert len(listings) == 1

    def test_get_marketplace_summary(self):
        """测试获取市场摘要"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
        )

        manager = PluginMarketplaceManager()

        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code="def test(): pass",
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )

        summary = manager.get_marketplace_summary()

        assert "total_listings" in summary
        assert "total_downloads" in summary
        assert "total_reviews" in summary
        assert "approved_plugins" in summary
        assert "pending_reviews" in summary
        assert "plugins_by_quality" in summary
        assert summary["total_listings"] == 1


class TestGetMarketplaceManager:
    """测试获取市场管理器"""

    def test_get_marketplace_manager(self):
        """测试获取市场管理器"""
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager = get_marketplace_manager()

        assert manager is not None
        assert hasattr(manager, "listings")

    def test_get_marketplace_manager_singleton(self):
        """测试获取市场管理器（单例）"""
        from core.plugin_marketplace_manager import get_marketplace_manager

        manager1 = get_marketplace_manager()
        manager2 = get_marketplace_manager()

        assert manager1 is manager2


class TestPluginMarketplaceManagerIntegration:
    """测试插件市场管理器集成"""

    def test_complete_marketplace_workflow(self):
        """测试完整市场工作流"""
        from core.plugin_marketplace_manager import (
            PluginMarketplaceManager,
            PluginQuality,
            PluginReviewStatus,
        )

        manager = PluginMarketplaceManager()

        # Publish plugin
        manager.publish_plugin(
            plugin_id="plugin_1",
            plugin_name="Test Plugin",
            version="1.0.0",
            description="Test description",
            author="Test Author",
            plugin_code='"""Test plugin"""\ndef test(): pass',
            plugin_config={},
            quality=PluginQuality.COMMUNITY,
        )
        assert "plugin_1" in manager.listings

        # Approve plugin
        manager.approve_plugin("plugin_1", "reviewer_1")
        assert manager.listings["plugin_1"].review_status == PluginReviewStatus.APPROVED

        # Download plugin
        download = manager.download_plugin("plugin_1")
        assert download is not None

        # Add review
        manager.add_review(
            plugin_id="plugin_1",
            reviewer="user_1",
            rating=5,
            comment="Great plugin",
        )
        assert len(manager.reviews["plugin_1"]) == 1

        # Get summary
        summary = manager.get_marketplace_summary()
        assert summary["total_listings"] == 1
        assert summary["approved_plugins"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
