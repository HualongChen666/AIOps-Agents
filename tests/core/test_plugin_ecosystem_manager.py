# -*- coding: utf-8 -*-
"""测试插件生态系统管理器模块"""

from datetime import datetime, timedelta, timezone

import pytest


class TestPluginEcosystemManagerModule:
    """测试插件生态系统管理器模块"""

    def test_plugin_ecosystem_manager_module_exists(self):
        """测试插件生态系统管理器模块存在"""
        from core import plugin_ecosystem_manager

        assert plugin_ecosystem_manager is not None

    def test_plugin_ecosystem_manager_has_enums(self):
        """测试插件生态系统管理器模块有枚举"""
        from core import plugin_ecosystem_manager

        # 检查模块有枚举
        assert hasattr(plugin_ecosystem_manager, "PluginActivityType")
        assert hasattr(plugin_ecosystem_manager, "PluginSupportLevel")

    def test_plugin_ecosystem_manager_has_dataclasses(self):
        """测试插件生态系统管理器模块有数据类"""
        from core import plugin_ecosystem_manager

        # 检查模块有数据类
        assert hasattr(plugin_ecosystem_manager, "PluginActivity")
        assert hasattr(plugin_ecosystem_manager, "PluginDeveloper")

    def test_plugin_ecosystem_manager_has_classes(self):
        """测试插件生态系统管理器模块有类"""
        from core import plugin_ecosystem_manager

        # 检查模块有类
        assert hasattr(plugin_ecosystem_manager, "PluginEcosystemManager")

    def test_plugin_ecosystem_manager_has_functions(self):
        """测试插件生态系统管理器模块有函数"""
        from core import plugin_ecosystem_manager

        # 检查模块有函数
        assert hasattr(plugin_ecosystem_manager, "get_ecosystem_manager")


class TestPluginActivityType:
    """测试插件活动类型枚举"""

    def test_plugin_activity_type_values(self):
        """测试插件活动类型值"""
        from core.plugin_ecosystem_manager import PluginActivityType

        assert PluginActivityType.INSTALL.value == "install"
        assert PluginActivityType.UPDATE.value == "update"
        assert PluginActivityType.UNINSTALL.value == "uninstall"
        assert PluginActivityType.ENABLE.value == "enable"
        assert PluginActivityType.DISABLE.value == "disable"
        assert PluginActivityType.REVIEW.value == "review"
        assert PluginActivityType.DOWNLOAD.value == "download"


class TestPluginSupportLevel:
    """测试插件支持级别枚举"""

    def test_plugin_support_level_values(self):
        """测试插件支持级别值"""
        from core.plugin_ecosystem_manager import PluginSupportLevel

        assert PluginSupportLevel.COMMUNITY.value == "community"
        assert PluginSupportLevel.PREMIUM.value == "premium"
        assert PluginSupportLevel.ENTERPRISE.value == "enterprise"


class TestPluginActivity:
    """测试插件活动数据类"""

    def test_plugin_activity_creation(self):
        """测试插件活动创建"""
        from core.plugin_ecosystem_manager import (
            PluginActivity,
            PluginActivityType,
        )

        activity = PluginActivity(
            activity_id="activity_1",
            plugin_id="plugin_1",
            activity_type=PluginActivityType.INSTALL,
            user_id="user_1",
            timestamp=datetime.now(timezone.utc),
        )

        assert activity.activity_id == "activity_1"
        assert activity.plugin_id == "plugin_1"
        assert activity.activity_type == PluginActivityType.INSTALL


class TestPluginDeveloper:
    """测试插件开发者数据类"""

    def test_plugin_developer_creation(self):
        """测试插件开发者创建"""
        from core.plugin_ecosystem_manager import (
            PluginDeveloper,
            PluginSupportLevel,
        )

        developer = PluginDeveloper(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
            support_level=PluginSupportLevel.COMMUNITY,
        )

        assert developer.developer_id == "dev_1"
        assert developer.name == "Developer 1"
        assert developer.support_level == PluginSupportLevel.COMMUNITY


class TestPluginEcosystemManager:
    """测试插件生态系统管理器类"""

    def test_plugin_ecosystem_manager_initialization(self):
        """测试插件生态系统管理器初始化"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        assert manager.config == {}
        assert len(manager.activities) == 0
        assert len(manager.developers) == 0

    def test_plugin_ecosystem_manager_initialization_with_config(self):
        """测试插件生态系统管理器初始化（带配置）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        config = {"custom_key": "custom_value"}
        manager = PluginEcosystemManager(config)

        assert manager.config == config

    def test_record_activity(self):
        """测试记录活动"""
        from core.plugin_ecosystem_manager import (
            PluginActivityType,
            PluginEcosystemManager,
        )

        manager = PluginEcosystemManager()

        activity = manager.record_activity(
            plugin_id="plugin_1",
            activity_type=PluginActivityType.INSTALL,
            user_id="user_1",
        )

        assert activity.plugin_id == "plugin_1"
        assert manager.total_activities == 1

    def test_register_developer(self):
        """测试注册开发者"""
        from core.plugin_ecosystem_manager import (
            PluginEcosystemManager,
            PluginSupportLevel,
        )

        manager = PluginEcosystemManager()

        result = manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
            support_level=PluginSupportLevel.COMMUNITY,
        )

        assert result is True
        assert "dev_1" in manager.developers
        assert manager.total_developers == 1

    def test_register_developer_duplicate(self):
        """测试注册开发者（重复）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
        )

        result = manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
        )

        assert result is False

    def test_update_developer_reputation(self):
        """测试更新开发者声誉"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
        )

        result = manager.update_developer_reputation("dev_1", 0.5)

        assert result is True
        assert manager.developers["dev_1"].reputation_score == 0.5

    def test_update_developer_reputation_invalid(self):
        """测试更新开发者声誉（无效）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        result = manager.update_developer_reputation("invalid_dev", 0.5)

        assert result is False

    def test_update_developer_reputation_bounds(self):
        """测试更新开发者声誉（边界）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
        )

        # Test upper bound
        manager.update_developer_reputation("dev_1", 10.0)
        assert manager.developers["dev_1"].reputation_score == 5.0

        # Test lower bound
        manager.update_developer_reputation("dev_1", -10.0)
        assert manager.developers["dev_1"].reputation_score == 0.0

    def test_create_community_forum(self):
        """测试创建社区论坛"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        result = manager.create_community_forum(
            forum_id="forum_1",
            title="Test Forum",
            description="Test Description",
        )

        assert result is True
        assert "forum_1" in manager.community_forums

    def test_create_community_forum_duplicate(self):
        """测试创建社区论坛（重复）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        manager.create_community_forum(
            forum_id="forum_1",
            title="Test Forum",
            description="Test Description",
        )

        result = manager.create_community_forum(
            forum_id="forum_1",
            title="Test Forum",
            description="Test Description",
        )

        assert result is False

    def test_create_developer_event(self):
        """测试创建开发者事件"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        event_date = datetime.now(timezone.utc)
        result = manager.create_developer_event(
            event_id="event_1",
            title="Test Event",
            description="Test Description",
            event_date=event_date,
        )

        assert result is True
        assert "event_1" in manager.developer_events

    def test_create_developer_event_duplicate(self):
        """测试创建开发者事件（重复）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        event_date = datetime.now(timezone.utc)
        manager.create_developer_event(
            event_id="event_1",
            title="Test Event",
            description="Test Description",
            event_date=event_date,
        )

        result = manager.create_developer_event(
            event_id="event_1",
            title="Test Event",
            description="Test Description",
            event_date=event_date,
        )

        assert result is False

    def test_create_incentive_program(self):
        """测试创建激励计划"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        result = manager.create_incentive_program(
            program_id="program_1",
            title="Test Program",
            description="Test Description",
            reward_type="cash",
            reward_amount=1000.0,
        )

        assert result is True
        assert "program_1" in manager.incentive_programs

    def test_create_incentive_program_duplicate(self):
        """测试创建激励计划（重复）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        manager.create_incentive_program(
            program_id="program_1",
            title="Test Program",
            description="Test Description",
            reward_type="cash",
            reward_amount=1000.0,
        )

        result = manager.create_incentive_program(
            program_id="program_1",
            title="Test Program",
            description="Test Description",
            reward_type="cash",
            reward_amount=1000.0,
        )

        assert result is False

    def test_get_plugin_activities(self):
        """测试获取插件活动"""
        from core.plugin_ecosystem_manager import (
            PluginActivityType,
            PluginEcosystemManager,
        )

        manager = PluginEcosystemManager()

        manager.record_activity(
            plugin_id="plugin_1",
            activity_type=PluginActivityType.INSTALL,
            user_id="user_1",
        )

        activities = manager.get_plugin_activities("plugin_1")

        assert len(activities) == 1

    def test_get_plugin_activities_with_time_range(self):
        """测试获取插件活动（带时间范围）"""
        from core.plugin_ecosystem_manager import (
            PluginActivityType,
            PluginEcosystemManager,
        )

        manager = PluginEcosystemManager()

        manager.record_activity(
            plugin_id="plugin_1",
            activity_type=PluginActivityType.INSTALL,
            user_id="user_1",
        )

        # Use a time range that should include the activity
        time_range = timedelta(hours=1)
        activities = manager.get_plugin_activities("plugin_1", time_range)

        assert len(activities) == 1

    def test_get_developer_stats(self):
        """测试获取开发者统计"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
        )

        stats = manager.get_developer_stats("dev_1")

        assert stats is not None
        assert stats["developer_id"] == "dev_1"
        assert stats["name"] == "Developer 1"

    def test_get_developer_stats_invalid(self):
        """测试获取开发者统计（无效）"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        stats = manager.get_developer_stats("invalid_dev")

        assert stats is None

    def test_get_ecosystem_summary(self):
        """测试获取生态系统摘要"""
        from core.plugin_ecosystem_manager import PluginEcosystemManager

        manager = PluginEcosystemManager()

        summary = manager.get_ecosystem_summary()

        assert "total_activities" in summary
        assert "total_developers" in summary
        assert "total_forums" in summary
        assert "total_events" in summary
        assert "total_programs" in summary
        assert "developers_by_support_level" in summary


class TestGetEcosystemManager:
    """测试获取生态系统管理器"""

    def test_get_ecosystem_manager(self):
        """测试获取生态系统管理器"""
        from core.plugin_ecosystem_manager import get_ecosystem_manager

        manager = get_ecosystem_manager()

        assert manager is not None
        assert hasattr(manager, "activities")

    def test_get_ecosystem_manager_singleton(self):
        """测试获取生态系统管理器（单例）"""
        from core.plugin_ecosystem_manager import get_ecosystem_manager

        manager1 = get_ecosystem_manager()
        manager2 = get_ecosystem_manager()

        assert manager1 is manager2


class TestPluginEcosystemManagerIntegration:
    """测试插件生态系统管理器集成"""

    def test_complete_ecosystem_workflow(self):
        """测试完整生态系统工作流"""
        from core.plugin_ecosystem_manager import (
            PluginActivityType,
            PluginEcosystemManager,
            PluginSupportLevel,
        )

        manager = PluginEcosystemManager()

        # Register developer
        manager.register_developer(
            developer_id="dev_1",
            name="Developer 1",
            email="dev@example.com",
            support_level=PluginSupportLevel.PREMIUM,
        )
        assert "dev_1" in manager.developers

        # Record activity
        activity = manager.record_activity(
            plugin_id="plugin_1",
            activity_type=PluginActivityType.INSTALL,
            user_id="user_1",
            metadata={"developer_id": "dev_1"},
        )
        assert activity.plugin_id == "plugin_1"

        # Update reputation
        manager.update_developer_reputation("dev_1", 0.5)
        assert manager.developers["dev_1"].reputation_score == 0.5

        # Create forum
        manager.create_community_forum(
            forum_id="forum_1",
            title="Test Forum",
            description="Test Description",
            plugin_id="plugin_1",
        )
        assert "forum_1" in manager.community_forums

        # Create event
        event_date = datetime.now(timezone.utc)
        manager.create_developer_event(
            event_id="event_1",
            title="Test Event",
            description="Test Description",
            event_date=event_date,
        )
        assert "event_1" in manager.developer_events

        # Create incentive program
        manager.create_incentive_program(
            program_id="program_1",
            title="Test Program",
            description="Test Description",
            reward_type="cash",
            reward_amount=1000.0,
        )
        assert "program_1" in manager.incentive_programs

        # Get summary
        summary = manager.get_ecosystem_summary()
        assert summary["total_developers"] == 1
        assert summary["total_forums"] == 1
        assert summary["total_events"] == 1
        assert summary["total_programs"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
