# -*- coding: utf-8 -*-
"""
Frontend Enhancement Module
===========================

Enhances the frontend user experience with:
- Real-time monitoring dashboard (WebSocket-based)
- Interactive topology visualization
- Custom report generation functionality
- Mobile responsive design optimization
- Dark theme and customizable interface
- User preference settings and persistence
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# This module provides backend support for frontend enhancements


class ThemeType(Enum):
    """Theme types"""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


class ViewMode(Enum):
    """View modes"""

    GRID = "grid"
    LIST = "list"
    COMPACT = "compact"
    DETAILED = "detailed"


@dataclass
class UserPreference:
    """User preference settings"""

    user_id: str
    theme: ThemeType = ThemeType.AUTO
    language: str = "zh-CN"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm:ss"
    view_mode: ViewMode = ViewMode.GRID
    notifications_enabled: bool = True
    notification_sound: bool = False
    auto_refresh_interval: int = 30  # seconds
    dashboard_layout: Dict[str, Any] = field(default_factory=dict)
    custom_colors: Dict[str, str] = field(default_factory=dict)
    accessibility_settings: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""

    widget_id: str
    widget_type: str
    title: str
    position: Dict[str, int]  # {x, y, width, height}
    config: Dict[str, Any] = field(default_factory=dict)
    data_source: Optional[str] = None
    refresh_interval: int = 30
    enabled: bool = True


@dataclass
class ReportTemplate:
    """Report template configuration"""

    template_id: str
    name: str
    description: str
    data_sources: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    visualization_config: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # cron expression
    format: str = "pdf"  # pdf, html, csv
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class FrontendEnhancementManager:
    """
    Manager for frontend enhancements and user experience improvements
    """

    def __init__(self):
        """Initialize frontend enhancement manager"""
        # User preferences storage
        self.user_preferences: Dict[str, UserPreference] = {}

        # Dashboard configurations
        self.dashboard_configs: Dict[str, List[DashboardWidget]] = defaultdict(list)

        # Report templates
        self.report_templates: Dict[str, ReportTemplate] = {}

        # Theme configurations
        self.theme_configs: Dict[ThemeType, Dict[str, Any]] = {
            ThemeType.LIGHT: {
                "primary_color": "#3b82f6",
                "background_color": "#ffffff",
                "text_color": "#1f2937",
                "border_color": "#e5e7eb",
                "success_color": "#10b981",
                "warning_color": "#f59e0b",
                "error_color": "#ef4444",
            },
            ThemeType.DARK: {
                "primary_color": "#60a5fa",
                "background_color": "#1f2937",
                "text_color": "#f9fafb",
                "border_color": "#374151",
                "success_color": "#34d399",
                "warning_color": "#fbbf24",
                "error_color": "#f87171",
            },
        }

        # Custom themes
        self.custom_themes: Dict[str, Dict[str, Any]] = {}

        # Mobile responsive breakpoints
        self.responsive_breakpoints = {
            "xs": 0,
            "sm": 640,
            "md": 768,
            "lg": 1024,
            "xl": 1280,
            "2xl": 1536,
        }

    def get_user_preferences(self, user_id: str) -> UserPreference:
        """
        Get user preferences, create default if not exists

        Args:
            user_id: User identifier

        Returns:
            UserPreference
        """
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreference(user_id=user_id)

        return self.user_preferences[user_id]

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserPreference:
        """
        Update user preferences

        Args:
            user_id: User identifier
            preferences: Preference updates

        Returns:
            Updated UserPreference
        """
        user_pref = self.get_user_preferences(user_id)

        # Update preferences; coerce string enums back to their enum types
        if "theme" in preferences:
            preferences["theme"] = ThemeType(preferences["theme"])
        if "view_mode" in preferences:
            preferences["view_mode"] = ViewMode(preferences["view_mode"])
        for key, value in preferences.items():
            if hasattr(user_pref, key):
                setattr(user_pref, key, value)

        user_pref.last_updated = datetime.now()

        return user_pref

    def get_theme_config(self, theme: ThemeType) -> Dict[str, Any]:
        """
        Get theme configuration

        Args:
            theme: Theme type

        Returns:
            Theme configuration
        """
        if theme == ThemeType.CUSTOM:
            # Return default light theme as fallback
            return self.theme_configs[ThemeType.LIGHT]

        return self.theme_configs.get(theme, self.theme_configs[ThemeType.LIGHT])

    def create_custom_theme(
        self,
        theme_id: str,
        name: str,
        colors: Dict[str, str],
        base_theme: ThemeType = ThemeType.LIGHT,
    ) -> Dict[str, Any]:
        """
        Create custom theme

        Args:
            theme_id: Theme identifier
            name: Theme name
            colors: Color configuration
            base_theme: Base theme to inherit from

        Returns:
            Custom theme configuration
        """
        base_config = self.get_theme_config(base_theme)
        custom_config = {**base_config}
        custom_config.update(colors)

        self.custom_themes[theme_id] = {
            "theme_id": theme_id,
            "name": name,
            "base_theme": base_theme.value,
            "colors": custom_config,
            "created_at": datetime.now().isoformat(),
        }

        return self.custom_themes[theme_id]

    def get_dashboard_config(self, dashboard_id: str) -> List[DashboardWidget]:
        """
        Get dashboard widget configuration

        Args:
            dashboard_id: Dashboard identifier

        Returns:
            List of dashboard widgets
        """
        if dashboard_id not in self.dashboard_configs:
            # Create default dashboard
            self.dashboard_configs[dashboard_id] = self._create_default_dashboard()

        return self.dashboard_configs[dashboard_id]

    def _create_default_dashboard(self) -> List[DashboardWidget]:
        """Create default dashboard widgets"""
        return [
            DashboardWidget(
                widget_id="metrics_overview",
                widget_type="metrics",
                title="指标概览",
                position={"x": 0, "y": 0, "width": 12, "height": 6},
                config={"metrics": ["cpu", "memory", "disk", "network"], "chart_type": "line"},
                refresh_interval=30,
            ),
            DashboardWidget(
                widget_id="alert_stream",
                widget_type="alerts",
                title="告警流",
                position={"x": 0, "y": 6, "width": 6, "height": 4},
                config={"max_alerts": 10, "auto_refresh": True},
                refresh_interval=15,
            ),
            DashboardWidget(
                widget_id="system_health",
                widget_type="health",
                title="系统健康度",
                position={"x": 6, "y": 6, "width": 6, "height": 4},
                config={"show_details": True},
                refresh_interval=60,
            ),
            DashboardWidget(
                widget_id="topology_view",
                widget_type="topology",
                title="拓扑视图",
                position={"x": 0, "y": 10, "width": 12, "height": 8},
                config={"interactive": True, "show_labels": True},
                refresh_interval=120,
            ),
        ]

    def add_dashboard_widget(self, dashboard_id: str, widget: DashboardWidget) -> DashboardWidget:
        """
        Add widget to dashboard

        Args:
            dashboard_id: Dashboard identifier
            widget: Widget to add

        Returns:
            Added widget
        """
        if dashboard_id not in self.dashboard_configs:
            self.dashboard_configs[dashboard_id] = []

        self.dashboard_configs[dashboard_id].append(widget)
        return widget

    def remove_dashboard_widget(self, dashboard_id: str, widget_id: str) -> bool:
        """
        Remove widget from dashboard

        Args:
            dashboard_id: Dashboard identifier
            widget_id: Widget identifier

        Returns:
            True if removed
        """
        if dashboard_id not in self.dashboard_configs:
            return False

        widgets = self.dashboard_configs[dashboard_id]
        self.dashboard_configs[dashboard_id] = [w for w in widgets if w.widget_id != widget_id]

        return True

    def update_dashboard_widget(
        self, dashboard_id: str, widget_id: str, updates: Dict[str, Any]
    ) -> Optional[DashboardWidget]:
        """
        Update dashboard widget

        Args:
            dashboard_id: Dashboard identifier
            widget_id: Widget identifier
            updates: Widget updates

        Returns:
            Updated widget or None
        """
        if dashboard_id not in self.dashboard_configs:
            return None

        for widget in self.dashboard_configs[dashboard_id]:
            if widget.widget_id == widget_id:
                for key, value in updates.items():
                    if hasattr(widget, key):
                        setattr(widget, key, value)
                return widget

        return None

    def create_report_template(
        self,
        template_id: str,
        name: str,
        description: str,
        data_sources: List[str],
        visualization_config: Dict[str, Any],
        format: str = "pdf",
        schedule: Optional[str] = None,
        created_by: str = "system",
    ) -> ReportTemplate:
        """
        Create report template

        Args:
            template_id: Template identifier
            name: Report name
            description: Report description
            data_sources: Data sources for report
            visualization_config: Visualization configuration
            format: Output format
            schedule: Schedule (cron expression)
            created_by: Creator

        Returns:
            ReportTemplate
        """
        template = ReportTemplate(
            template_id=template_id,
            name=name,
            description=description,
            data_sources=data_sources,
            visualization_config=visualization_config,
            format=format,
            schedule=schedule,
            created_by=created_by,
        )

        self.report_templates[template_id] = template
        return template

    def generate_report(
        self, template_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate report from template

        Args:
            template_id: Template identifier
            filters: Optional filters for report generation

        Returns:
            Generated report
        """
        if template_id not in self.report_templates:
            return {"error": "Template not found"}

        template = self.report_templates[template_id]

        # Apply filters
        applied_filters = {**template.filters, **(filters or {})}

        # Generate report (simplified implementation)
        report = {
            "template_id": template_id,
            "name": template.name,
            "description": template.description,
            "generated_at": datetime.now().isoformat(),
            "format": template.format,
            "data_sources": template.data_sources,
            "filters": applied_filters,
            "visualization_config": template.visualization_config,
            "data": self._generate_sample_data(template.data_sources),
        }

        return report

    def _generate_sample_data(self, data_sources: List[str]) -> Dict[str, Any]:
        """Generate sample data for report"""
        sample_data: Dict[str, Any] = {}

        for source in data_sources:
            if source == "metrics":
                sample_data[source] = {
                    "cpu": [45, 52, 48, 61, 55],
                    "memory": [60, 62, 58, 65, 63],
                    "disk": [40, 41, 42, 43, 44],
                }
            elif source == "alerts":
                sample_data[source] = {"total": 15, "critical": 2, "warning": 8, "info": 5}
            elif source == "topology":
                sample_data[source] = {"nodes": 12, "edges": 18, "components": 5}

        return sample_data

    def get_responsive_config(self, viewport_width: int) -> Dict[str, Any]:
        """
        Get responsive configuration based on viewport width

        Args:
            viewport_width: Viewport width in pixels

        Returns:
            Responsive configuration
        """
        # Determine breakpoint
        breakpoint = "xs"
        for bp_name, bp_width in sorted(self.responsive_breakpoints.items(), key=lambda x: x[1]):
            if viewport_width >= bp_width:
                breakpoint = bp_name

        # Return responsive configuration
        configs = {
            "xs": {
                "grid_columns": 1,
                "font_size": "small",
                "show_sidebar": False,
                "compact_mode": True,
            },
            "sm": {
                "grid_columns": 2,
                "font_size": "small",
                "show_sidebar": False,
                "compact_mode": True,
            },
            "md": {
                "grid_columns": 2,
                "font_size": "medium",
                "show_sidebar": True,
                "compact_mode": False,
            },
            "lg": {
                "grid_columns": 3,
                "font_size": "medium",
                "show_sidebar": True,
                "compact_mode": False,
            },
            "xl": {
                "grid_columns": 4,
                "font_size": "large",
                "show_sidebar": True,
                "compact_mode": False,
            },
            "2xl": {
                "grid_columns": 4,
                "font_size": "large",
                "show_sidebar": True,
                "compact_mode": False,
            },
        }

        return configs.get(breakpoint, configs["lg"])

    def get_accessibility_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Get accessibility settings for user

        Args:
            user_id: User identifier

        Returns:
            Accessibility settings
        """
        user_pref = self.get_user_preferences(user_id)
        return user_pref.accessibility_settings

    def update_accessibility_settings(
        self, user_id: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update accessibility settings

        Args:
            user_id: User identifier
            settings: Accessibility settings

        Returns:
            Updated settings
        """
        user_pref = self.get_user_preferences(user_id)
        user_pref.accessibility_settings.update(settings)
        user_pref.last_updated = datetime.now()

        return user_pref.accessibility_settings

    def export_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Export user preferences as JSON

        Args:
            user_id: User identifier

        Returns:
            User preferences as dictionary
        """
        user_pref = self.get_user_preferences(user_id)

        return {
            "user_id": user_pref.user_id,
            "theme": user_pref.theme.value,
            "language": user_pref.language,
            "timezone": user_pref.timezone,
            "date_format": user_pref.date_format,
            "time_format": user_pref.time_format,
            "view_mode": user_pref.view_mode.value,
            "notifications_enabled": user_pref.notifications_enabled,
            "notification_sound": user_pref.notification_sound,
            "auto_refresh_interval": user_pref.auto_refresh_interval,
            "dashboard_layout": user_pref.dashboard_layout,
            "custom_colors": user_pref.custom_colors,
            "accessibility_settings": user_pref.accessibility_settings,
            "last_updated": user_pref.last_updated.isoformat(),
        }

    def import_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserPreference:
        """
        Import user preferences from JSON

        Args:
            user_id: User identifier
            preferences: Preferences dictionary

        Returns:
            Imported UserPreference
        """
        # Convert string enums back to enums
        if "theme" in preferences:
            preferences["theme"] = ThemeType(preferences["theme"])
        if "view_mode" in preferences:
            preferences["view_mode"] = ViewMode(preferences["view_mode"])

        return self.update_user_preferences(user_id, preferences)

    def get_frontend_summary(self) -> Dict[str, Any]:
        """Get summary of frontend enhancements"""
        return {
            "user_preferences_count": len(self.user_preferences),
            "dashboard_configs_count": len(self.dashboard_configs),
            "total_widgets": sum(len(widgets) for widgets in self.dashboard_configs.values()),
            "report_templates_count": len(self.report_templates),
            "custom_themes_count": len(self.custom_themes),
            "available_themes": [theme.value for theme in ThemeType],
            "supported_formats": ["pdf", "html", "csv"],
            "responsive_breakpoints": self.responsive_breakpoints,
        }


# Global instance
frontend_enhancement_manager = FrontendEnhancementManager()
