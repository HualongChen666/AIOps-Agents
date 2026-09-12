# -*- coding: utf-8 -*-
"""
L6-L7 Frontend Integration (Phase 3)
Integration between L6 Execution Layer and L7 Integration Layer for frontend presentation
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class EventType(Enum):
    """Event type for frontend integration"""

    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGE = "status_change"
    DATA_UPDATE = "data_update"


class ComponentType(Enum):
    """Component type for frontend"""

    DASHBOARD = "dashboard"
    CHART = "chart"
    TABLE = "table"
    FORM = "form"
    NOTIFICATION = "notification"
    MODAL = "modal"


@dataclass
class FrontendEvent:
    """Frontend event configuration"""

    event_id: str
    event_type: EventType
    component_id: str
    component_type: ComponentType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentConfig:
    """Frontend component configuration"""

    component_id: str
    component_name: str
    component_type: ComponentType
    data_source: str
    update_frequency: int = 5
    auto_refresh: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataBinding:
    """Data binding configuration"""

    binding_id: str
    source_component: str
    target_component: str
    data_path: str
    transformation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class L6L7FrontendIntegrator:
    """Integration between L6 Execution Layer and L7 Integration Layer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize L6-L7 frontend integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Components
        self.components: Dict[str, ComponentConfig] = {}

        # Event handlers
        self.event_handlers: Dict[EventType, List[Callable]] = {}

        # Data bindings
        self.data_bindings: Dict[str, DataBinding] = {}

        # Event queue
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

        # Component data cache
        self.component_data: Dict[str, Any] = {}

        # Configuration
        self.auto_refresh_enabled = self.config.get("auto_refresh_enabled", True)
        self.event_buffer_size = self.config.get("event_buffer_size", 100)

        # Statistics
        self.total_events = 0
        self.total_updates = 0

        logger.info("L6-L7 frontend integrator initialized")

    def register_component(self, component: ComponentConfig) -> None:
        """
        Register frontend component

        Args:
            component: Component configuration
        """
        self.components[component.component_id] = component
        logger.info(f"Registered component: {component.component_id}")

    def register_event_handler(self, event_type: EventType, handler: Callable) -> None:
        """
        Register event handler

        Args:
            event_type: Event type
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered event handler for: {event_type.value}")

    def register_data_binding(self, binding: DataBinding) -> None:
        """
        Register data binding

        Args:
            binding: Data binding configuration
        """
        self.data_bindings[binding.binding_id] = binding
        logger.info(f"Registered data binding: {binding.binding_id}")

    async def emit_event(self, event: FrontendEvent) -> None:
        """
        Emit frontend event

        Args:
            event: Frontend event
        """
        await self.event_queue.put(event)
        self.total_events += 1
        logger.debug(f"Emitted event: {event.event_id}, type: {event.event_type.value}")

    async def start_event_processor(self) -> None:
        """Start event processor"""

        async def process_events():
            while True:
                try:
                    event = await self.event_queue.get()
                    await self._process_event(event)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Event processor error: {e}")
                    await asyncio.sleep(1)

        asyncio.create_task(process_events())
        logger.info("Event processor started")

    async def _process_event(self, event: FrontendEvent) -> None:
        """
        Process frontend event

        Args:
            event: Frontend event
        """
        try:
            # Call registered handlers
            for handler in self.event_handlers.get(event.event_type, []):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed for {event.event_type.value}: {e}")

            # Update component data
            await self._update_component_data(event)

            # Trigger data bindings
            await self._trigger_data_bindings(event)

        except Exception as e:
            logger.error(f"Failed to process event: {e}")

    async def _update_component_data(self, event: FrontendEvent) -> None:
        """
        Update component data based on event

        Args:
            event: Frontend event
        """
        if event.component_id in self.components:
            self.component_data[event.component_id] = event.data
            self.total_updates += 1
            logger.debug(f"Updated component data: {event.component_id}")

    async def _trigger_data_bindings(self, event: FrontendEvent) -> None:
        """
        Trigger data bindings based on event

        Args:
            event: Frontend event
        """
        for binding in self.data_bindings.values():
            if binding.source_component == event.component_id:
                await self._execute_data_binding(binding, event.data)

    async def _execute_data_binding(self, binding: DataBinding, data: Any) -> None:
        """
        Execute data binding

        Args:
            binding: Data binding configuration
            data: Source data
        """
        if binding.target_component in self.components:
            # Apply transformation if configured
            if binding.transformation:
                data = await self._apply_transformation(binding.transformation, data)

            # Update target component data
            self.component_data[binding.target_component] = data

            logger.debug(f"Executed data binding: {binding.binding_id}")

    async def _apply_transformation(self, transformation: str, data: Any) -> Any:
        """Apply a real data transformation.

        历史问题（已修复）：原实现仅 ``asyncio.sleep(0.1)`` 后原样返回数据（"Simulate
        transformation"）。现支持 ``json_path``（``path.to.field``）、``extract``、
        ``pick``、``count``、``sum``、``upper``、``lower`` 等真实算子。
        """
        spec = (transformation or "").strip()
        if not spec:
            return data

        name, _, arg = spec.partition(":")
        name = name.strip().lower()
        arg = arg.strip()

        if name in ("", "identity", "none"):
            return data

        if name in ("json_path", "path", "get"):
            if not arg:
                raise ValueError("json_path transformation requires a dotted path")
            cur = data
            for part in arg.split("."):
                if isinstance(cur, dict):
                    cur = cur.get(part)
                elif isinstance(cur, list):
                    cur = cur[int(part)]
                else:
                    return None
            return cur

        if name == "extract":
            field = arg or "value"
            if isinstance(data, dict):
                return data.get(field)
            return data

        if name == "pick":
            fields = [f.strip() for f in arg.split(",") if f.strip()]
            if isinstance(data, dict):
                return {f: data.get(f) for f in fields}
            return data

        if name == "count":
            return len(data) if isinstance(data, (list, dict, str)) else 1

        if name == "sum":
            if isinstance(data, list):
                return sum(float(x) for x in data)
            raise ValueError("sum transformation requires a list")

        if name == "upper":
            return data.upper() if isinstance(data, str) else data

        if name == "lower":
            return data.lower() if isinstance(data, str) else data

        raise ValueError(f"unknown transformation: {transformation}")

    async def _refresh_component(self, component_id: str) -> None:
        """Fetch fresh component data from its real data source.

        历史问题（已修复）：原实现仅 ``asyncio.sleep(0.2)``（"would fetch fresh data from
        data source"），从不拉取数据。现按 ``component.data_source`` 真实发起 HTTP 拉取并
        写入 component_data；拉取失败如实记录并保留旧值。
        """
        if component_id not in self.components:
            return

        component = self.components[component_id]
        source = component.data_source
        if not source:
            logger.warning(f"Component {component_id} has no data_source; nothing to refresh")
            return

        base_url = self.config.get("data_source_base_url", "")
        url = source if source.startswith(("http://", "https://")) else f"{base_url}{source}"
        if not url.startswith(("http://", "https://")):
            raise ValueError(
                f"component {component_id} data_source '{source}' is not fetchable "
                f"(set config['data_source_base_url'])"
            )

        import httpx

        timeout = self.config.get("data_source_timeout", 10)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            self.component_data[component_id] = response.json()
        self.total_updates += 1
        logger.debug(f"Refreshed component: {component_id} from {url}")

    async def start_auto_refresh(self) -> None:
        """Start auto-refresh for components"""
        if not self.auto_refresh_enabled:
            return

        async def refresh_loop():
            while True:
                try:
                    refresh_interval = 1.0
                    for component_id, component in list(self.components.items()):
                        if component.auto_refresh:
                            await self._refresh_component(component_id)
                        refresh_interval = getattr(component, "update_frequency", 1.0)

                    await asyncio.sleep(refresh_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto-refresh error: {e}")
                    await asyncio.sleep(1)

        asyncio.create_task(refresh_loop())
        logger.info("Auto-refresh started")

    def get_component_data(self, component_id: str) -> Optional[Any]:
        """
        Get component data

        Args:
            component_id: Component ID

        Returns:
            Component data
        """
        return self.component_data.get(component_id)

    def get_component_config(self, component_id: str) -> Optional[Dict[str, Any]]:
        """
        Get component configuration

        Args:
            component_id: Component ID

        Returns:
            Component configuration dictionary
        """
        if component_id not in self.components:
            return None

        component = self.components[component_id]

        return {
            "component_id": component.component_id,
            "component_name": component.component_name,
            "component_type": component.component_type.value,
            "data_source": component.data_source,
            "update_frequency": component.update_frequency,
            "auto_refresh": component.auto_refresh,
            "config": component.config,
        }

    async def update_component(self, component_id: str, data: Dict[str, Any]) -> bool:
        """
        Update component data manually

        Args:
            component_id: Component ID
            data: New data

        Returns:
            Success status
        """
        if component_id not in self.components:
            return False

        self.component_data[component_id] = data
        self.total_updates += 1

        # Emit data update event
        event = FrontendEvent(
            event_id=f"update_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            event_type=EventType.DATA_UPDATE,
            component_id=component_id,
            component_type=self.components[component_id].component_type,
            data=data,
        )

        await self.emit_event(event)

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            "total_events": self.total_events,
            "total_updates": self.total_updates,
            "registered_components": len(self.components),
            "registered_bindings": len(self.data_bindings),
            "active_handlers": sum(len(handlers) for handlers in self.event_handlers.values()),
        }


def get_l6l7_frontend_integrator(config: Optional[Dict[str, Any]] = None) -> L6L7FrontendIntegrator:
    """
    Factory function to get L6-L7 frontend integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        L6L7FrontendIntegrator: Integrator instance
    """
    return L6L7FrontendIntegrator(config)
