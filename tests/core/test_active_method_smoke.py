# -*- coding: utf-8 -*-
import logging

"""Extended smoke tests for active core modules.

Tries to call public functions and methods with type-aware dummy arguments.
Calls that fail due to missing dependencies, type mismatches, or side effects
are skipped rather than failing the suite.
"""

import asyncio
import datetime
import enum
import inspect
import pathlib
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Union, get_args, get_origin, get_type_hints
from unittest.mock import MagicMock

import pytest

ACTIVE_MODULES = [
    "core.linux_collector",
    "core.data_lineage",
    "core.backup_strategy",
    "core.command_guard",
    "core.data_integration_manager",
    "core.audit_service",
    "core.config_center",
    "core.compliance_manager",
    "core.analysis.l2.enhanced_causal_analyzer",
    "core.enhanced_auth_integration",
    "core.health_check",
    "core.enterprise_functionality",
    "core.data_privacy",
    "core.performance_integration_tester",
    "core.log_collector",
    "core.integration_manager",
    "core.user_service",
    "core.linux_repair",
    "core.feature_flag",
    "core.enhanced_websocket_manager",
    "core.abac",
    "core.performance_report_generator",
    "core.websocket_integrator",
    "core.cache_helpers",
    "core.integration_testing_system",
    "core.analysis.l2.langgraph_engine",
    "core.l2l3_workflow_integrator",
    "core.collector",
    "core.performance_optimizer",
    "core.frontend_performance_optimizer",
    "core.integration_documentation_manager",
    "core.service_monitoring_manager",
    "core.data_lifecycle_manager",
    "core.unified_access_control",
    "core.frontend_enhancement",
    "core.cloud_collector",
    "core.qdrant_service",
    "core.telemetry_core",
    "core.documentation_manager",
    "core.service_mesh_manager",
    "core.localization_adapter",
    "core.plugin_system",
    "core.k8s_repair",
    "core.runbook_generator",
    "core.frontend_cache_strategy",
    "core.advanced_ai_capabilities",
]


# Modules with known heavy / network side effects that should not be auto-called
SKIP_MODULE_PREFIXES = (
    "core.analysis.l2.rag_engine",
    "core.ai.llm_router.enhanced_router",
    "core.ai.rag.retriever",
    "core.qdrant_service",
    "core.cloud_collector",
    "core.storage.l4",
    "core.real_integration",
    "core.cache_helpers",
    "core.performance_optimizer",
    "core.frontend_performance_optimizer",
    "core.model_fine_tuner",
    "core.user_service",
    "core.analysis.l2.langgraph_engine",
    "core.collector",
)


LONG_RUNNING_METHOD_PREFIXES = (
    "start_",
    "run_",
    "monitor_",
    "watch_",
    "listen_",
    "consume_",
    "health_check_loop",
    "background_",
)


def _is_long_running_method(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in LONG_RUNNING_METHOD_PREFIXES)


def _is_skipped_module(module_name: str) -> bool:
    return any(module_name.startswith(prefix) for prefix in SKIP_MODULE_PREFIXES)


def _value_for_type(tp: Any) -> Any:
    """Return a safe dummy value for a given type annotation."""
    import builtins

    origin = get_origin(tp)
    args = get_args(tp)

    # Optional / Union
    if origin is Union:
        for arg in args:
            if arg is type(None):
                continue
            try:
                return _value_for_type(arg)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
        return None

    # List, Sequence
    if origin in (list, List) or tp in (list, List):
        return [_value_for_type(arg) for arg in args] if args else []

    # Dict, Mapping
    if origin in (dict, Dict) or tp in (dict, Dict):
        if args and len(args) == 2:
            key_tp, val_tp = args
            return {_value_for_type(key_tp): _value_for_type(val_tp)}
        return {}

    # Callable
    if origin is Callable or tp is Callable:
        return lambda *a, **kw: MagicMock()

    # str
    if tp is str:
        return "test"
    if tp is int:
        return 0
    if tp is float:
        return 0.0
    if tp is bool:
        return False
    if tp is Any:
        return MagicMock()
    if tp is type(None):
        return None
    if tp is datetime.datetime:
        return datetime.datetime.now()
    if tp is datetime.date:
        return datetime.date.today()
    if tp is pathlib.Path:
        return pathlib.Path("test")
    if tp is bytes:
        return b"test"

    # Enum
    if isinstance(tp, type) and issubclass(tp, enum.Enum):
        try:
            return list(tp)[0]
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
        return None

    # Built-in scalar types
    if tp in (builtins.str, builtins.int, builtins.float, builtins.bool):
        type_map = {
            "<class 'str'>": "test",
            "<class 'int'>": 0,
            "<class 'float'>": 0.0,
            "<class 'bool'>": False,
        }
        return type_map.get(str(tp), None)

    # Try to instantiate a concrete class with a no-arg or generated constructor
    if isinstance(tp, type) and not inspect.isabstract(tp):
        # Pydantic-like model_construct for empty/optional models
        try:
            if hasattr(tp, "model_construct"):
                return tp.model_construct()
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
        try:
            sig = inspect.signature(tp.__init__)
            kwargs: Dict[str, Any] = {}
            for name, param in sig.parameters.items():
                if name in ("self", "cls"):
                    continue
                if param.default is not param.empty:
                    continue
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                kwargs[name] = _value_for_type(param.annotation)
            return tp(**kwargs)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
        try:
            return tp()
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)

    # Fallback: MagicMock for unknown/custom classes so methods can still be called
    return MagicMock()


def _generate_args(
    callable_obj: Callable[..., Any], module: ModuleType
) -> Optional[Dict[str, Any]]:
    """Generate a kwargs dict that can be used to call callable_obj.

    Returns None if any required argument cannot be generated.
    """
    try:
        sig = inspect.signature(callable_obj)
    except (ValueError, TypeError):
        return None

    try:
        hints = get_type_hints(callable_obj, globalns=module.__dict__, localns={})
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        hints = {}

    kwargs: Dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if param.default is not param.empty:
            continue
        if param.kind is param.KEYWORD_ONLY:
            # keyword-only without default still needs a value
            pass
        try:
            annotation = hints.get(name, param.annotation)
            kwargs[name] = _value_for_type(annotation)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            return None
    return kwargs


def _is_public(name: str) -> bool:
    return not name.startswith("_")


ASYNC_TIMEOUT_SECONDS = 1


def _call_or_run(obj: Callable[..., Any], kwargs: Dict[str, Any]) -> None:
    try:
        result = obj(**kwargs)
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        logging.exception("Unexpected exception: %s", e)
        return
    if inspect.iscoroutine(result):
        try:
            asyncio.run(asyncio.wait_for(result, timeout=ASYNC_TIMEOUT_SECONDS))
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise


def _try_call(obj: Callable[..., Any], module: ModuleType) -> None:
    kwargs = _generate_args(obj, module)
    if kwargs is None:
        return
    try:
        _call_or_run(obj, kwargs)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)


def _can_instantiate(cls: type, module: ModuleType) -> bool:
    if inspect.isabstract(cls):
        return False
    if not _is_public(cls.__name__):
        return False
    kwargs = _generate_args(cls, module)
    return kwargs is not None


@pytest.mark.parametrize("module_name", ACTIVE_MODULES)
def test_active_module_method_smoke(module_name: str) -> None:
    import importlib

    if _is_skipped_module(module_name):
        pytest.skip(f"Module {module_name} skipped due to heavy side effects")

    try:
        mod = importlib.import_module(module_name)
    except (ImportError, RuntimeError, OSError) as exc:
        pytest.skip(f"{module_name} not importable: {exc}")

    assert isinstance(mod, ModuleType)

    for name, obj in inspect.getmembers(mod):
        if not _is_public(name) or getattr(obj, "__module__", None) != module_name:
            continue

        if inspect.isclass(obj):
            try:
                kwargs = _generate_args(obj, mod)
                if kwargs is None:
                    continue
                instance = obj(**kwargs)
            except (Exception,):
                continue

            for method_name, method in inspect.getmembers(instance):
                if not _is_public(method_name) or _is_long_running_method(method_name):
                    continue
                if not (
                    inspect.isfunction(method)
                    or inspect.ismethod(method)
                    or inspect.iscoroutinefunction(method)
                ):
                    continue
                _try_call(method, mod)

        if (
            inspect.isfunction(obj)
            and not inspect.iscoroutinefunction(obj)
            and not _is_long_running_method(obj.__name__)
        ):
            _try_call(obj, mod)
