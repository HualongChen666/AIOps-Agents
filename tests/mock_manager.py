# -*- coding: utf-8 -*-
# tests/mock_manager.py
# 统一的Mock配置管理模块
# 提供稳定、可复用的mock配置，提升测试稳定性
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

logger = logging.getLogger(__name__)


class MockManager:
    """统一的Mock管理器，提供稳定的mock配置"""

    def __init__(self):
        """初始化Mock管理器"""
        self._active_mocks: Dict[str, Any] = {}
        self._mock_patches: List[Any] = []
        self._original_modules: Dict[str, Any] = {}

    def create_mock_config(
        self,
        return_value: Any = None,
        side_effect: Optional[Callable] = None,
        is_async: bool = False,
        spec: Optional[Any] = None,
        **kwargs,
    ) -> Any:
        """
        创建标准化的mock配置

        Args:
            return_value: mock的返回值
            side_effect: mock的副作用函数
            is_async: 是否为异步mock
            spec: mock的规格对象
            **kwargs: 其他mock参数

        Returns:
            配置好的mock对象
        """
        mock_class = AsyncMock if is_async else Mock
        mock = mock_class(spec=spec, **kwargs)

        if side_effect is not None:
            mock.side_effect = side_effect
        elif return_value is not None:
            mock.return_value = return_value

        return mock

    def create_service_mock(
        self, service_name: str, methods: Dict[str, Any], is_async: bool = False
    ) -> Mock:
        """
        创建服务mock对象

        Args:
            service_name: 服务名称
            methods: 方法名到返回值的映射
            is_async: 是否为异步服务

        Returns:
            配置好的服务mock
        """
        service_mock = Mock()
        service_mock.__name__ = service_name

        for method_name, return_value in methods.items():
            if is_async:
                setattr(service_mock, method_name, AsyncMock(return_value=return_value))
            else:
                setattr(service_mock, method_name, Mock(return_value=return_value))

        self._active_mocks[service_name] = service_mock
        return service_mock

    @contextmanager
    def patch_module(self, module_path: str, mock_object: Any):
        """
        上下文管理器，用于临时patch模块

        Args:
            module_path: 要patch的模块路径
            mock_object: mock对象
        """
        patcher = patch(module_path, mock_object)
        self._mock_patches.append(patcher)
        mock = patcher.start()
        try:
            yield mock
        finally:
            patcher.stop()
            self._mock_patches.remove(patcher)

    @contextmanager
    def patch_multiple(self, **patches):
        """
        上下文管理器，用于同时patch多个对象

        Args:
            **patches: 路径到mock对象的映射
        """
        active_patches = []
        try:
            for path, mock_obj in patches.items():
                patcher = patch(path, mock_obj)
                patcher.start()
                active_patches.append(patcher)
            yield
        finally:
            for patcher in reversed(active_patches):
                patcher.stop()

    def safe_module_mock(
        self, module_names: List[str], mock_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        安全地mock多个模块，避免破坏原有模块结构

        Args:
            module_names: 要mock的模块名列表
            mock_config: mock配置字典

        Returns:
            mock对象的字典
        """
        mocked_modules = {}
        mock_config = mock_config or {}

        for module_name in module_names:
            if module_name not in sys.modules:
                # 如果模块不存在，创建一个MagicMock
                mock = MagicMock()
                sys.modules[module_name] = mock
                self._original_modules[module_name] = None
            else:
                # 如果模块存在，保存原始引用
                original = sys.modules[module_name]
                self._original_modules[module_name] = original
                # 创建mock并替换
                mock = MagicMock()
                sys.modules[module_name] = mock

            # 应用配置
            if module_name in mock_config:
                config = mock_config[module_name]
                for attr_name, attr_value in config.items():
                    setattr(mock, attr_name, attr_value)

            mocked_modules[module_name] = mock
            self._active_mocks[module_name] = mock

        return mocked_modules

    def restore_modules(self):
        """恢复所有被mock的模块"""
        for module_name, original in self._original_modules.items():
            if original is None:
                # 如果原始不存在，删除mock
                if module_name in sys.modules:
                    del sys.modules[module_name]
            else:
                # 恢复原始模块
                sys.modules[module_name] = original

        self._original_modules.clear()
        logger.info("All modules restored to original state")

    def reset_all_mocks(self):
        """重置所有活跃的mock"""
        reset_count = 0
        for mock_name, mock in self._active_mocks.items():
            if hasattr(mock, "reset_mock"):
                mock.reset_mock()
                reset_count += 1
        logger.info(f"Reset {reset_count} mocks")  # noqa: F541

    def cleanup(self):
        """清理所有mock资源"""
        self.reset_all_mocks()
        self.restore_modules()
        self._active_mocks.clear()
        logger.info("Mock manager cleanup completed")


# 预定义的mock配置
class MockConfigs:
    """预定义的mock配置集合"""

    @staticmethod
    def get_ai_analyze_config() -> Dict[str, Any]:
        """AI分析服务的mock配置"""
        return {
            "return_value": {
                "analysis": "分析结果",
                "root_cause": "根因分析",
                "suggestions": ["建议1", "建议2"],
                "confidence": 0.95,
                "metadata": {"model": "gpt-4", "timestamp": "2024-01-01T00:00:00Z"},
            }
        }

    @staticmethod
    def get_alert_service_config() -> Dict[str, Any]:
        """告警服务的mock配置"""
        return {
            "get_alerts": {"alerts": [], "total": 0},
            "clear_alerts": {"success": True, "cleared_count": 0},
            "create_alert": {"success": True, "alert_id": 1},
            "update_alert": {"success": True},
            "delete_alert": {"success": True},
            "get_alert_by_id": {"id": 1, "title": "测试告警", "severity": "critical"},
            "escalate_alert": {"success": True, "escalated_to": "level2"},
        }

    @staticmethod
    def get_health_check_config() -> Dict[str, Any]:
        """健康检查的mock配置"""
        return {
            "get_liveness_status": {"status": "healthy"},
            "get_readiness_status": {"status": "ready"},
            "get_detailed_health": {
                "status": "healthy",
                "components": {
                    "database": {"status": "healthy"},
                    "redis": {"status": "healthy"},
                    "ai_engine": {"status": "healthy"},
                },
            },
            "perform_health_checks": {
                "status": "healthy",
                "components": {"database": {"status": "healthy"}, "redis": {"status": "healthy"}},
            },
        }

    @staticmethod
    def get_database_config() -> Dict[str, Any]:
        """数据库的mock配置"""
        return {
            "connect": Mock(return_value=Mock()),
            "execute": Mock(return_value=Mock(rowcount=1)),
            "fetchall": Mock(return_value=[]),
            "fetchone": Mock(return_value=None),
            "commit": Mock(),
            "rollback": Mock(),
            "close": Mock(),
            "begin_transaction": Mock(return_value="txn_12345"),
            "execute_batch": Mock(return_value={"success": True, "affected_rows": 1}),
        }

    @staticmethod
    def get_cache_config() -> Dict[str, Any]:
        """缓存的mock配置"""
        return {
            "get": Mock(return_value=None),
            "set": Mock(return_value=True),
            "delete": Mock(return_value=True),
            "exists": Mock(return_value=False),
            "clear": Mock(return_value=True),
            "get_stats": Mock(return_value={"hits": 100, "misses": 10, "hit_rate": 0.9}),
            "get_keys": Mock(return_value=["key1", "key2"]),
        }

    @staticmethod
    def get_auth_config() -> Dict[str, Any]:
        """认证服务的mock配置"""
        return {
            "verify_token": Mock(return_value={"user_id": 1, "valid": True}),
            "create_token": Mock(return_value="mock_token_12345"),
            "refresh_token": Mock(return_value="new_mock_token_67890"),
            "revoke_token": Mock(return_value=True),
            "validate_user": Mock(return_value={"valid": True, "user_id": 1}),
            "check_permission": Mock(return_value=True),
        }

    @staticmethod
    def get_workflow_service_config() -> Dict[str, Any]:
        """工作流服务的mock配置"""
        return {
            "create_workflow": Mock(return_value={"workflow_id": "wf_123", "status": "created"}),
            "execute_workflow": Mock(return_value={"workflow_id": "wf_123", "status": "running"}),
            "get_workflow_status": Mock(return_value={"status": "completed", "progress": 100}),
            "pause_workflow": Mock(return_value={"status": "paused"}),
            "resume_workflow": Mock(return_value={"status": "running"}),
            "cancel_workflow": Mock(return_value={"status": "cancelled"}),
            "list_workflows": Mock(return_value={"workflows": [], "total": 0}),
        }

    @staticmethod
    def get_topology_service_config() -> Dict[str, Any]:
        """拓扑服务的mock配置"""
        return {
            "get_topology": Mock(return_value={"nodes": [], "edges": [], "metadata": {}}),
            "discover_topology": Mock(return_value={"discovered_nodes": 5, "discovered_edges": 8}),
            "update_topology": Mock(return_value={"success": True}),
            "analyze_impact": Mock(return_value={"affected_services": [], "impact_score": 0.5}),
            "get_dependency_graph": Mock(return_value={"dependencies": []}),
        }

    @staticmethod
    def get_audit_service_config() -> Dict[str, Any]:
        """审计服务的mock配置"""
        return {
            "log_event": Mock(
                return_value={"event_id": "evt_123", "timestamp": "2024-01-01T00:00:00Z"}
            ),
            "get_audit_trail": Mock(return_value={"events": [], "total": 0}),
            "search_events": Mock(return_value={"events": [], "total": 0}),
            "generate_report": Mock(return_value={"report_id": "rpt_456", "status": "generated"}),
            "get_compliance_status": Mock(return_value={"compliant": True, "score": 0.95}),
        }

    @staticmethod
    def get_user_service_config() -> Dict[str, Any]:
        """用户服务的mock配置"""
        return {
            "get_user": Mock(return_value={"user_id": 1, "username": "test_user", "role": "admin"}),
            "create_user": Mock(
                return_value={"user_id": 2, "username": "new_user", "created": True}
            ),
            "update_user": Mock(return_value={"success": True}),
            "delete_user": Mock(return_value={"success": True}),
            "list_users": Mock(return_value={"users": [], "total": 0}),
            "assign_role": Mock(return_value={"success": True}),
        }

    @staticmethod
    def get_config_service_config() -> Dict[str, Any]:
        """配置服务的mock配置"""
        return {
            "get_config": Mock(return_value={"key": "value"}),
            "set_config": Mock(return_value=True),
            "delete_config": Mock(return_value=True),
            "get_all_configs": Mock(return_value={"configs": {}}),
            "validate_config": Mock(return_value={"valid": True}),
            "watch_config": Mock(return_value=True),
        }

    @staticmethod
    def get_notification_service_config() -> Dict[str, Any]:
        """通知服务的mock配置"""
        return {
            "send_email": Mock(return_value={"success": True, "message_id": "msg_123"}),
            "send_sms": Mock(return_value={"success": True, "message_id": "msg_124"}),
            "send_webhook": Mock(return_value={"success": True, "status_code": 200}),
            "send_slack": Mock(return_value={"success": True, "timestamp": "2024-01-01T00:00:00Z"}),
            "get_notification_status": Mock(return_value={"status": "delivered"}),
        }

    @staticmethod
    def get_storage_service_config() -> Dict[str, Any]:
        """存储服务的mock配置"""
        return {
            "store_file": Mock(return_value={"file_id": "file_123", "size": 1024}),
            "retrieve_file": Mock(return_value={"content": b"file_content", "metadata": {}}),
            "delete_file": Mock(return_value={"success": True}),
            "list_files": Mock(return_value={"files": [], "total": 0}),
            "get_file_info": Mock(
                return_value={"file_id": "file_123", "size": 1024, "created": "2024-01-01"}
            ),
        }

    @staticmethod
    def get_monitoring_service_config() -> Dict[str, Any]:
        """监控服务的mock配置"""
        return {
            "get_metrics": Mock(return_value={"metrics": [], "timestamp": "2024-01-01T00:00:00Z"}),
            "collect_metrics": Mock(return_value={"collected": 10, "failed": 0}),
            "get_alert_rules": Mock(return_value={"rules": [], "total": 0}),
            "create_alert_rule": Mock(return_value={"rule_id": "rule_123", "created": True}),
            "get_system_health": Mock(return_value={"status": "healthy", "score": 0.95}),
        }

    @staticmethod
    def get_security_service_config() -> Dict[str, Any]:
        """安全服务的mock配置"""
        return {
            "validate_input": Mock(return_value={"valid": True, "sanitized": "input"}),
            "check_permission": Mock(return_value={"allowed": True}),
            "encrypt_data": Mock(
                return_value={"encrypted": "encrypted_data", "algorithm": "AES-256"}
            ),
            "decrypt_data": Mock(return_value={"decrypted": "original_data", "success": True}),
            "audit_security_event": Mock(return_value={"event_id": "sec_123", "logged": True}),
        }

    @staticmethod
    def get_plugin_service_config() -> Dict[str, Any]:
        """插件服务的mock配置"""
        return {
            "load_plugin": Mock(return_value={"plugin_id": "plugin_123", "loaded": True}),
            "unload_plugin": Mock(return_value={"success": True}),
            "list_plugins": Mock(return_value={"plugins": [], "total": 0}),
            "get_plugin_info": Mock(return_value={"plugin_id": "plugin_123", "version": "1.0.0"}),
            "execute_plugin": Mock(return_value={"result": "success", "output": {}}),
        }


class MockMonitor:
    """Mock使用监控和统计"""

    def __init__(self):
        """初始化监控器"""
        self._mock_usage: Dict[str, Dict[str, Any]] = {}
        self._test_history: List[Dict[str, Any]] = []
        self._session_start_time = time.time()
        self._current_test: Optional[str] = None

    def start_test(self, test_name: str):
        """开始测试监控"""
        self._current_test = test_name
        logger.info(f"Starting mock monitoring for test: {test_name}")  # noqa: F541

    def end_test(self):
        """结束测试监控"""
        if self._current_test:
            test_summary = {
                "test_name": self._current_test,
                "mocks_used": len(self._mock_usage),
                "timestamp": time.time(),
                "mock_details": dict(self._mock_usage),
            }
            self._test_history.append(test_summary)
            logger.info(
                f"Test completed: {self._current_test}, mocks used: {len(self._mock_usage)}"  # noqa: E501
            )
            self._current_test = None
            self._mock_usage.clear()

    def record_mock_usage(self, mock_name: str, method_name: str, call_count: int = 1):
        """记录mock使用情况"""
        if mock_name not in self._mock_usage:
            self._mock_usage[mock_name] = {
                "methods": {},
                "total_calls": 0,
                "first_used": time.time(),
            }

        if method_name not in self._mock_usage[mock_name]["methods"]:
            self._mock_usage[mock_name]["methods"][method_name] = {
                "call_count": 0,
                "last_called": None,
            }

        self._mock_usage[mock_name]["methods"][method_name]["call_count"] += call_count
        self._mock_usage[mock_name]["methods"][method_name]["last_called"] = time.time()
        self._mock_usage[mock_name]["total_calls"] += call_count

    def get_mock_stats(self) -> Dict[str, Any]:
        """获取mock使用统计"""
        total_calls = sum(mock_data["total_calls"] for mock_data in self._mock_usage.values())
        most_used_mock = max(
            self._mock_usage.items(),
            key=lambda x: x[1]["total_calls"],
            default=(None, {"total_calls": 0}),
        )

        return {
            "total_mocks_used": len(self._mock_usage),
            "total_calls": total_calls,
            "most_used_mock": most_used_mock[0] if most_used_mock[0] else None,
            "most_used_mock_calls": most_used_mock[1]["total_calls"],
            "session_duration": time.time() - self._session_start_time,
            "current_test": self._current_test,
            "mock_details": dict(self._mock_usage),
        }

    def get_test_history(self) -> List[Dict[str, Any]]:
        """获取测试历史"""
        return self._test_history.copy()

    def generate_usage_report(self) -> str:
        """生成使用报告"""
        stats = self.get_mock_stats()
        report_lines = [
            "=" * 60,
            "MOCK USAGE REPORT",
            "=" * 60,
            f"Session Duration: {  # noqa: F541
                stats['session_duration']:.2f}s",
            f"Total Mocks Used: {stats['total_mocks_used']}",  # noqa: F541, E501
            f"Total Mock Calls: {stats['total_calls']}",  # noqa: F541
            f"Most Used Mock: {stats['most_used_mock'] or 'None'} ({  # noqa: F541
                        stats['most_used_mock_calls']} calls)",
            "",
            "Mock Details:",
        ]

        for mock_name, mock_data in stats["mock_details"].items():
            report_lines.append(f"  {mock_name}:")  # noqa: F541
            report_lines.append(f"    Total Calls: {mock_data['total_calls']}")  # noqa: F541
            for method_name, method_data in mock_data["methods"].items():
                report_lines.append(
                    f"    {method_name}: {method_data['call_count']} calls"
                )  # noqa: F541

        if self._test_history:
            report_lines.append("")
            report_lines.append("Test History:")
            for i, test in enumerate(self._test_history, 1):
                report_lines.append(
                    f"  {i}. {test['test_name']}: {test['mocks_used']} mocks"
                )  # noqa: F541

        report_lines.append("=" * 60)
        return "\n".join(report_lines)

    def identify_over_mocks(self, threshold: int = 10) -> List[str]:
        """识别过度使用的mock"""
        over_used = []
        for mock_name, mock_data in self._mock_usage.items():
            if mock_data["total_calls"] > threshold:
                over_used.append(mock_name)
        return over_used

    def identify_unused_mocks(self, registered_mocks: List[str]) -> List[str]:
        """识别未使用的mock"""
        return [mock for mock in registered_mocks if mock not in self._mock_usage]


# 全局mock管理器实例
_global_mock_manager: Optional[MockManager] = None
_global_mock_monitor: Optional[MockMonitor] = None


def get_mock_manager() -> MockManager:
    """获取全局mock管理器实例"""
    global _global_mock_manager
    if _global_mock_manager is None:
        _global_mock_manager = MockManager()
    return _global_mock_manager


def get_mock_monitor() -> MockMonitor:
    """获取全局mock监控器实例"""
    global _global_mock_monitor
    if _global_mock_monitor is None:
        _global_mock_monitor = MockMonitor()
    return _global_mock_monitor


def reset_global_mock_manager():
    """重置全局mock管理器"""
    global _global_mock_manager
    if _global_mock_manager is not None:
        _global_mock_manager.cleanup()
        _global_mock_manager = None


def reset_global_mock_monitor():
    """重置全局mock监控器"""
    global _global_mock_monitor
    if _global_mock_monitor is not None:
        _global_mock_monitor = None


# 便捷函数
def create_stable_mock(
    return_value: Any = None, side_effect: Optional[Callable] = None, is_async: bool = False
) -> Any:
    """
    创建稳定的mock对象

    Args:
        return_value: 返回值
        side_effect: 副作用函数
        is_async: 是否异步

    Returns:
        配置好的mock对象
    """
    manager = get_mock_manager()
    return manager.create_mock_config(
        return_value=return_value, side_effect=side_effect, is_async=is_async
    )


def create_service_mock(service_name: str, methods: Dict[str, Any], is_async: bool = False) -> Mock:
    """
    创建服务mock对象

    Args:
        service_name: 服务名称
        methods: 方法配置
        is_async: 是否异步

    Returns:
        服务mock对象
    """
    manager = get_mock_manager()
    return manager.create_service_mock(service_name, methods, is_async)


class MockCoverageReporter:
    """Mock覆盖率报告生成器"""

    def __init__(self, monitor: MockMonitor):
        """
        初始化覆盖率报告生成器

        Args:
            monitor: Mock监控器实例
        """
        self.monitor = monitor

    def generate_coverage_report(
        self, registered_mocks: Dict[str, Dict[str, Any]], output_format: str = "text"
    ) -> str:
        """
        生成mock覆盖率报告

         Args:
             registered_mocks: 注册的mock配置 {service_name: {methods: [...]}}
             output_format: 输出格式 ('text', 'json', 'html')

         Returns:
             格式化的覆盖率报告
        """
        mock_stats = self.monitor.get_mock_stats()
        used_mocks = set(mock_stats["mock_details"].keys())
        registered_mock_names = set(registered_mocks.keys())

        # 计算覆盖率
        total_registered = len(registered_mock_names)
        total_used = len(used_mocks)
        coverage_percentage = (total_used / total_registered * 100) if total_registered > 0 else 0

        # 计算方法覆盖率
        method_coverage = self._calculate_method_coverage(
            registered_mocks, mock_stats["mock_details"]
        )

        if output_format == "json":
            return self._generate_json_report(
                coverage_percentage, total_registered, total_used, method_coverage, mock_stats
            )
        elif output_format == "html":
            return self._generate_html_report(
                coverage_percentage,
                total_registered,
                total_used,
                method_coverage,
                mock_stats,
                registered_mocks,
            )
        else:
            return self._generate_text_report(
                coverage_percentage,
                total_registered,
                total_used,
                method_coverage,
                mock_stats,
                registered_mocks,
            )

    def _calculate_method_coverage(
        self, registered_mocks: Dict[str, Dict[str, Any]], used_mocks: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算方法覆盖率"""
        method_stats: Dict[str, Any] = {
            "total_registered_methods": 0,
            "total_used_methods": 0,
            "method_details": {},
        }

        for service_name, service_config in registered_mocks.items():
            registered_methods = set(service_config.keys())
            used_methods = set()

            if service_name in used_mocks:
                used_methods = set(used_mocks[service_name]["methods"].keys())

            method_stats["total_registered_methods"] += len(registered_methods)
            method_stats["total_used_methods"] += len(used_methods)

            method_stats["method_details"][service_name] = {
                "registered": len(registered_methods),
                "used": len(used_methods),
                "coverage": (
                    len(used_methods) / len(registered_methods) * 100 if registered_methods else 0
                ),
                "missing_methods": list(registered_methods - used_methods),
            }

        method_stats["overall_coverage"] = (
            method_stats["total_used_methods"] / method_stats["total_registered_methods"] * 100
            if method_stats["total_registered_methods"] > 0
            else 0
        )

        return method_stats

    def _generate_text_report(
        self,
        coverage_percentage: float,
        total_registered: int,
        total_used: int,
        method_coverage: Dict[str, Any],
        mock_stats: Dict[str, Any],
        registered_mocks: Dict[str, Dict[str, Any]],
    ) -> str:
        """生成文本格式报告"""  # noqa: E501
        report_lines = [
            "=" * 70,
            "MOCK COVERAGE REPORT",
            "=" * 70,
            (  # noqa: E501
                f"Service Coverage: {coverage_percentage:.1f}% ({total_used}/{total_registered}"
                " services)"
            ),
            f"Method Coverage: {method_coverage['overall_coverage']:.1f}% "  # noqa: F541
            f"({method_coverage['total_used_methods']}/"  # noqa: F541
            f"{method_coverage['total_registered_methods']} methods)",  # noqa: F541
            "",
            "Service Coverage Details:",
        ]

        # 按覆盖率排序
        sorted_services = sorted(
            method_coverage["method_details"].items(), key=lambda x: x[1]["coverage"], reverse=True
        )

        for service_name, coverage_data in sorted_services:
            status = "PASS" if coverage_data["coverage"] == 100 else "FAIL"
            report_lines.append(
                f"  {status} {service_name}: {coverage_data['coverage']:.1f}% "  # noqa: F541
                f"({coverage_data['used']}/{coverage_data['registered']} methods)"  # noqa: F541
            )

            if coverage_data["missing_methods"]:
                report_lines.append(
                    f"      Missing: {', '.join(coverage_data['missing_methods'])}"
                )  # noqa: F541

        # 未使用的服务
        unused_services = set(registered_mocks.keys()) - set(mock_stats["mock_details"].keys())
        if unused_services:
            report_lines.append("")
            report_lines.append("Unused Services:")
            for service in sorted(unused_services):
                report_lines.append(f"  - {service}")  # noqa: F541

        # 过度使用的mock
        over_used = self.monitor.identify_over_mocks(threshold=20)
        if over_used:
            report_lines.append("")
            report_lines.append("Over-used Mocks (>20 calls):")
            for mock_name in over_used:
                calls = mock_stats["mock_details"][mock_name]["total_calls"]
                report_lines.append(f"  - {mock_name}: {calls} calls")  # noqa: F541

        report_lines.append("")
        report_lines.append("=" * 70)
        return "\n".join(report_lines)

    def _generate_json_report(
        self,
        coverage_percentage: float,
        total_registered: int,
        total_used: int,
        method_coverage: Dict[str, Any],
        mock_stats: Dict[str, Any],
    ) -> str:
        """生成JSON格式报告"""
        import json

        report = {
            "summary": {
                "service_coverage_percentage": coverage_percentage,
                "services_used": total_used,
                "services_registered": total_registered,
                "method_coverage_percentage": method_coverage["overall_coverage"],
                "methods_used": method_coverage["total_used_methods"],
                "methods_registered": method_coverage["total_registered_methods"],
            },
            "service_details": method_coverage["method_details"],
            "mock_usage_stats": mock_stats,
            "test_history": self.monitor.get_test_history(),
        }
        return json.dumps(report, indent=2)

    def _generate_html_report(
        self,
        coverage_percentage: float,
        total_registered: int,
        total_used: int,
        method_coverage: Dict[str, Any],
        mock_stats: Dict[str, Any],
        registered_mocks: Dict[str, Dict[str, Any]],
    ) -> str:
        """生成HTML格式报告"""
        html_lines = [
            "<html>",  # noqa: E501
            "<head>",
            "<title>Mock Coverage Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            (  # noqa: E501
                ".summary { background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom:"
                " 20px; }"
            ),
            ".coverage-high { color: green; }",
            ".coverage-medium { color: orange; }",
            ".coverage-low { color: red; }",
            "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            ".unused { background-color: #ffcccc; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Mock Coverage Report</h1>",
            "<div class='summary'>",
            f"<h2>Summary</h2>",  # noqa: F541
            f"<p>Service Coverage: <strong class='coverage-"  # noqa: F541
            f"{self._get_coverage_class(coverage_percentage)}'>"  # noqa: F541
            f"{coverage_percentage:.1f}%</strong> "  # noqa: F541
            f"({total_used}/{total_registered} services)</p>",  # noqa: F541
            f"<p>Method Coverage: <strong class='coverage-"  # noqa: F541
            f"{self._get_coverage_class(method_coverage['overall_coverage'])}'>"  # noqa: F541
            f"{method_coverage['overall_coverage']:.1f}%</strong> "  # noqa: F541
            f"({method_coverage['total_used_methods']}/"  # noqa: E501
            f"{method_coverage['total_registered_methods']} methods)</p>",  # noqa: F541
            "</div>",
            "<h2>Service Coverage Details</h2>",
            "<table>",
            (  # noqa: E501
                "<tr><th>Service</th><th>Coverage</th><th>Methods Used</th><th>Total"
                " Methods</th><th>Status</th></tr>"
            ),
        ]

        # 按覆盖率排序
        sorted_services = sorted(
            method_coverage["method_details"].items(), key=lambda x: x[1]["coverage"], reverse=True
        )

        for service_name, coverage_data in sorted_services:
            coverage_class = self._get_coverage_class(coverage_data["coverage"])
            status = "PASS" if coverage_data["coverage"] == 100 else "FAIL"
            row_class = "unused" if coverage_data["used"] == 0 else ""

            html_lines.append(
                f"<tr class='{row_class}'>"  # noqa: F541
                f"<td>{service_name}</td>"  # noqa: F541
                f"<td class='coverage-{coverage_class}'>"  # noqa: E501
                f"{coverage_data['coverage']:.1f}%</td>"
                f"<td>{coverage_data['used']}</td>"  # noqa: F541
                f"<td>{coverage_data['registered']}</td>"  # noqa: F541
                f"<td>{status}</td>"  # noqa: F541
                f"</tr>"  # noqa: F541
            )

        html_lines.extend(["</table>", "</body>", "</html>"])

        return "\n".join(html_lines)

    def _get_coverage_class(self, coverage: float) -> str:
        """获取覆盖率CSS类"""
        if coverage >= 80:
            return "high"
        elif coverage >= 50:
            return "medium"
        else:
            return "low"


class SmartMockManager:
    """智能Mock管理器 - 提供自动化优化和智能分析"""

    def __init__(self, monitor: MockMonitor):
        """
        初始化智能管理器

        Args:
            monitor: Mock监控器实例
        """
        self.monitor = monitor
        self.usage_patterns: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, List[float]] = {}
        self.optimization_suggestions: List[str] = []
        self.anomaly_detection_enabled = True
        self.auto_optimization_enabled = True

    def analyze_usage_patterns(self) -> Dict[str, Any]:
        """分析mock使用模式"""
        stats = self.monitor.get_mock_stats()
        patterns: Dict[str, Any] = {
            "high_frequency_mocks": [],
            "low_frequency_mocks": [],
            "burst_usage": [],
            "steady_usage": [],
            "correlated_usage": [],
        }

        for mock_name, mock_data in stats["mock_details"].items():
            total_calls = mock_data["total_calls"]
            method_count = len(mock_data["methods"])

            # 高频使用mock
            if total_calls > 50:
                patterns["high_frequency_mocks"].append(
                    {"name": mock_name, "calls": total_calls, "methods": method_count}
                )
            elif total_calls < 5:
                patterns["low_frequency_mocks"].append({"name": mock_name, "calls": total_calls})

            # 使用模式分析
            if method_count == 1 and total_calls > 20:
                patterns["burst_usage"].append(mock_name)
            elif method_count > 3 and total_calls > 10:
                patterns["steady_usage"].append(mock_name)

        self.usage_patterns = patterns
        return patterns

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测使用异常"""
        anomalies = []
        stats = self.monitor.get_mock_stats()

        for mock_name, mock_data in stats["mock_details"].items():
            # 检测异常高频使用
            if mock_data["total_calls"] > 100:
                anomalies.append(
                    {
                        "type": "excessive_usage",
                        "mock": mock_name,
                        "calls": mock_data["total_calls"],
                        "severity": "high",
                        "suggestion": (  # noqa: E501
                            f"Consider reducing {mock_name} usage or caching results"
                        ),
                    }
                )

            # 检测异常方法分布
            method_calls = [m["call_count"] for m in mock_data["methods"].values()]
            if method_calls:
                avg_calls = sum(method_calls) / len(method_calls)
                max_calls = max(method_calls)
                if max_calls > avg_calls * 10:
                    anomalies.append(
                        {
                            "type": "unbalanced_usage",
                            "mock": mock_name,
                            "max_calls": max_calls,
                            "avg_calls": avg_calls,
                            "severity": "medium",
                            "suggestion": f"Unbalanced method usage in {mock_name}",  # noqa: F541
                        }
                    )

        self.optimization_suggestions = [a["suggestion"] for a in anomalies]
        return anomalies

    def generate_optimization_suggestions(self) -> List[str]:
        """生成优化建议"""
        suggestions = []
        patterns = self.analyze_usage_patterns()
        anomalies = self.detect_anomalies()

        # 基于模式的建议
        if patterns["high_frequency_mocks"]:
            top_mock = patterns["high_frequency_mocks"][0]
            suggestions.append(
                f"Consider caching results for {top_mock['name']} "  # noqa: F541
                f"({top_mock['calls']} calls across {top_mock['methods']} methods)"  # noqa: F541
            )

        if patterns["low_frequency_mocks"]:
            suggestions.append(
                f"Review {len(patterns['low_frequency_mocks'])} low-frequency mocks "  # noqa: F541
                "for potential removal or consolidation"
            )

        if patterns["burst_usage"]:
            suggestions.append(
                f"Burst usage detected in {len(patterns['burst_usage'])} mocks. "  # noqa: F541
                "Consider implementing request batching"
            )

        # 基于异常的建议
        for anomaly in anomalies:
            if anomaly["severity"] == "high":
                suggestions.append(f"HIGH PRIORITY: {anomaly['suggestion']}")  # noqa: F541

        self.optimization_suggestions = suggestions
        return suggestions

    def auto_optimize_config(self) -> Dict[str, Any]:
        """自动优化配置"""
        if not self.auto_optimization_enabled:
            return {"enabled": False, "reason": "Auto-optimization disabled"}

        optimizations: Dict[str, Any] = {
            "enabled": True,
            "changes": [],
            "performance_improvements": {},
        }

        patterns = self.analyze_usage_patterns()

        # 高频mock优化建议
        for mock_info in patterns["high_frequency_mocks"]:
            mock_name = mock_info["name"]
            optimizations["changes"].append(
                {
                    "mock": mock_name,
                    "action": "add_caching",
                    "reason": f"High frequency usage ({mock_info['calls']} calls)",  # noqa: F541
                    "expected_improvement": "30-50% reduction in mock calls",
                }
            )

        # 低频mock清理建议
        for mock_info in patterns["low_frequency_mocks"]:
            mock_name = mock_info["name"]
            optimizations["changes"].append(
                {
                    "mock": mock_name,
                    "action": "review_necessity",
                    "reason": f"Low frequency usage ({mock_info['calls']} calls)",  # noqa: F541
                    "expected_improvement": "Reduced test complexity",
                }
            )

        return optimizations

    def smart_reset_strategy(self, mock_name: str) -> bool:
        """智能重置策略"""
        if not self.anomaly_detection_enabled:
            return True

        # 检查是否需要特殊处理
        stats = self.monitor.get_mock_stats()
        if mock_name in stats["mock_details"]:
            mock_data = stats["mock_details"][mock_name]

            # 高频使用的mock，延迟重置
            if mock_data["total_calls"] > 50:
                logger.info(
                    f"Smart reset: Delaying reset for high-frequency mock {mock_name}"
                )  # noqa: F541
                return False

            # 正常重置
            return True

        return True

    def performance_monitoring(self) -> Dict[str, Any]:
        """性能监控"""
        stats = self.monitor.get_mock_stats()
        performance_data = {
            "session_duration": stats["session_duration"],
            "calls_per_second": 0,
            "avg_response_time": 0,
            "performance_rating": "good",
        }

        if stats["session_duration"] > 0:
            performance_data["calls_per_second"] = stats["total_calls"] / stats["session_duration"]

        # 性能评级
        if performance_data["calls_per_second"] > 100:
            performance_data["performance_rating"] = "excellent"
        elif performance_data["calls_per_second"] > 50:
            performance_data["performance_rating"] = "good"
        elif performance_data["calls_per_second"] > 10:
            performance_data["performance_rating"] = "fair"
        else:
            performance_data["performance_rating"] = "poor"

        return performance_data

    def generate_smart_report(self) -> str:
        """生成智能分析报告"""
        report_lines = [
            "=" * 70,
            "SMART MOCK ANALYSIS REPORT",
            "=" * 70,
            "",
            "USAGE PATTERNS:",
            "-" * 50,
        ]

        patterns = self.analyze_usage_patterns()

        report_lines.append(
            f"High-frequency mocks: {len(patterns['high_frequency_mocks'])}"
        )  # noqa: F541
        for mock in patterns["high_frequency_mocks"][:3]:  # 显示前3个
            report_lines.append(f"  - {mock['name']}: {mock['calls']} calls")  # noqa: F541

        report_lines.append(
            f"Low-frequency mocks: {len(patterns['low_frequency_mocks'])}"
        )  # noqa: F541

        report_lines.append("")
        report_lines.append("ANOMALIES DETECTED:")
        report_lines.append("-" * 50)

        anomalies = self.detect_anomalies()
        if anomalies:
            for anomaly in anomalies[:5]:  # 显示前5个
                report_lines.append(
                    f"  [{anomaly['severity'].upper()}] "  # noqa: E501
                    f"{anomaly['type']}: {anomaly['mock']}"
                )
        else:
            report_lines.append("  No anomalies detected")

        report_lines.append("")
        report_lines.append("OPTIMIZATION SUGGESTIONS:")
        report_lines.append("-" * 50)

        suggestions = self.generate_optimization_suggestions()
        for i, suggestion in enumerate(suggestions[:5], 1):  # 显示前5个
            report_lines.append(f"  {i}. {suggestion}")  # noqa: F541

        report_lines.append("")
        report_lines.append("PERFORMANCE METRICS:")
        report_lines.append("-" * 50)

        perf = self.performance_monitoring()
        report_lines.append(f"Session duration: {perf['session_duration']:.2f}s")  # noqa: F541
        report_lines.append(f"Calls per second: {perf['calls_per_second']:.2f}")  # noqa: F541
        report_lines.append(
            f"Performance rating: {perf['performance_rating'].upper()}"
        )  # noqa: F541

        report_lines.append("")
        report_lines.append("AUTO-OPTIMIZATION STATUS:")
        report_lines.append("-" * 50)

        auto_opt = self.auto_optimize_config()
        if auto_opt["enabled"]:
            report_lines.append(f"Auto-optimization: ENABLED")  # noqa: F541
            report_lines.append(f"Recommended changes: {len(auto_opt['changes'])}")  # noqa: F541
        else:
            report_lines.append(
                f"Auto-optimization: DISABLED ({auto_opt.get('reason', 'Unknown')})"  # noqa: F541
            )

        report_lines.append("=" * 70)
        return "\n".join(report_lines)


class MockConfigValidator:
    """Mock配置验证器"""

    def __init__(self):
        """初始化配置验证器"""
        self.validation_rules = {
            "required_fields": ["return_value", "side_effect"],
            "async_compatibility": ["is_async"],
            "naming_convention": r"^[a-z_][a-z0-9_]*$",
        }
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

    def validate_config(self, config_name: str, config: Dict[str, Any]) -> bool:
        """
        验证单个mock配置

        Args:
            config_name: 配置名称
            config: 配置字典

        Returns:
            验证是否通过
        """
        self.validation_errors.clear()
        self.validation_warnings.clear()

        # 验证配置结构
        if not isinstance(config, dict):
            self.validation_errors.append(
                f"{config_name}: Config must be a dictionary"
            )  # noqa: F541
            return False

        # 验证命名规范
        if not self._validate_naming_convention(config_name):
            self.validation_warnings.append(
                f"{config_name}: Does not follow naming convention"
            )  # noqa: F541

        # 验证必需字段
        if "return_value" not in config and "side_effect" not in config:
            self.validation_errors.append(
                f"{config_name}: Must have either 'return_value' or 'side_effect'"  # noqa: F541
            )

        # 验证return_value类型
        if "return_value" in config:
            self._validate_return_value(config_name, config["return_value"])

        # 验证side_effect类型
        if "side_effect" in config:
            self._validate_side_effect(config_name, config["side_effect"])

        # 验证异步兼容性
        if "is_async" in config:
            self._validate_async_config(config_name, config)

        return len(self.validation_errors) == 0

    def validate_service_config(self, service_name: str, methods: Dict[str, Any]) -> bool:
        """
        验证服务mock配置

        Args:
            service_name: 服务名称
            methods: 方法配置字典

        Returns:
            验证是否通过
        """
        self.validation_errors.clear()
        self.validation_warnings.clear()

        if not isinstance(methods, dict):
            self.validation_errors.append(
                f"{service_name}: Methods must be a dictionary"
            )  # noqa: F541
            return False

        if not methods:
            self.validation_warnings.append(f"{service_name}: No methods defined")  # noqa: F541

        for method_name, method_config in methods.items():
            if not self._validate_naming_convention(method_name):
                self.validation_warnings.append(
                    f"{service_name}.{method_name}: Does not follow naming convention"  # noqa: F541
                )

            if not isinstance(method_config, (dict, str, int, float, bool, type(None))):
                self.validation_errors.append(
                    f"{service_name}.{method_name}: Invalid method config type"  # noqa: F541
                )

        return len(self.validation_errors) == 0

    def validate_all_configs(self, configs: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        验证所有配置

        Args:
            configs: 配置字典

        Returns:
            验证结果字典 {config_name: is_valid}
        """
        results = {}
        for config_name, config in configs.items():
            results[config_name] = self.validate_config(config_name, config)
        return results

    def get_validation_report(self) -> str:
        """获取验证报告"""
        report_lines = ["Mock Configuration Validation Report", "=" * 50]

        if self.validation_errors:
            report_lines.append("\nERRORS:")
            for error in self.validation_errors:
                report_lines.append(f"  X {error}")  # noqa: F541

        if self.validation_warnings:
            report_lines.append("\nWARNINGS:")
            for warning in self.validation_warnings:
                report_lines.append(f"  ! {warning}")  # noqa: F541

        if not self.validation_errors and not self.validation_warnings:
            report_lines.append("\nPASS All validations passed")

        report_lines.append("=" * 50)
        return "\n".join(report_lines)

    def _validate_naming_convention(self, name: str) -> bool:
        """验证命名规范"""
        import re

        return bool(re.match(str(self.validation_rules["naming_convention"]), name))

    def _validate_return_value(self, config_name: str, return_value: Any) -> bool:
        """验证return_value"""
        # 检查是否为可JSON序列化的类型
        try:
            import json

            json.dumps(return_value)
            return True
        except (TypeError, ValueError):
            self.validation_errors.append(
                f"{config_name}: return_value is not JSON serializable"
            )  # noqa: F541
            return False

    def _validate_side_effect(self, config_name: str, side_effect: Any) -> bool:
        """验证side_effect"""
        if callable(side_effect):
            return True
        elif isinstance(side_effect, (list, tuple)):
            return True
        elif isinstance(side_effect, Exception):
            return True
        else:
            self.validation_errors.append(
                f"{config_name}: side_effect must be callable, "  # noqa: E501
                "list/tuple, or Exception"
            )
            return False

    def _validate_async_config(self, config_name: str, config: Dict[str, Any]) -> bool:
        """验证异步配置"""
        if config["is_async"] and "return_value" in config:
            # 异步mock的return_value应该是coroutine或简单值
            return_value = config["return_value"]
            if isinstance(return_value, dict) and "analysis" in return_value:
                # AI分析结果，适合异步
                return True
            elif isinstance(return_value, (str, int, float, bool, type(None), list, dict)):
                # 简单值，适合异步
                return True
            else:
                self.validation_warnings.append(
                    f"{config_name}: Async mock with complex return_value "  # noqa: E501
                    "may need special handling"
                )
        return True


# 全局智能管理器实例
_global_smart_manager: Optional[SmartMockManager] = None


def get_smart_manager() -> SmartMockManager:
    """获取全局智能管理器实例"""
    global _global_smart_manager
    if _global_smart_manager is None:
        monitor = get_mock_monitor()
        _global_smart_manager = SmartMockManager(monitor)
    return _global_smart_manager


def reset_global_smart_manager():
    """重置全局智能管理器"""
    global _global_smart_manager
    if _global_smart_manager is not None:
        _global_smart_manager = None
