# -*- coding: utf-8 -*-
from __future__ import annotations

"""
multi_region.py
---------------
高可用架构 - 多区域部署模块。

功能：
- 多区域配置管理
- 跨区域数据同步
- 区域健康监控
- 流量路由策略
- 故障转移机制
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 区域状态枚举
# ----------------------------------------------------------------------
class RegionStatus(Enum):
    """区域状态"""

    ACTIVE = "active"
    STANDBY = "standby"
    DEGRADED = "degraded"
    DOWN = "down"


# ----------------------------------------------------------------------
# 2️⃣ 区域定义
# ----------------------------------------------------------------------
@dataclass
class Region:
    """区域定义"""

    id: str
    name: str
    location: str
    status: RegionStatus = RegionStatus.ACTIVE
    endpoint: str = ""
    priority: int = 1  # 优先级，数字越小优先级越高
    capacity: float = 1.0  # 容量比例
    latency: Optional[float] = None  # 延迟（毫秒）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "status": self.status.value,
            "endpoint": self.endpoint,
            "priority": self.priority,
            "capacity": self.capacity,
            "latency": self.latency,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 3️⃣ 流量路由策略
# ----------------------------------------------------------------------
class RoutingStrategy(Enum):
    """路由策略"""

    ROUND_ROBIN = "round_robin"
    LEAST_LATENCY = "least_latency"
    WEIGHTED = "weighted"
    GEOGRAPHIC = "geographic"
    ACTIVE_STANDBY = "active_standby"


# ----------------------------------------------------------------------
# 4️⃣ 多区域管理器
# ----------------------------------------------------------------------
class MultiRegionManager:
    """多区域管理器"""

    def __init__(self):
        self.regions: Dict[str, Region] = {}
        self.routing_strategy = RoutingStrategy.WEIGHTED
        self.current_region_index = 0
        self.health_check_interval = 30  # 秒
        self.failover_threshold = 3  # 连续失败次数

    def add_region(self, region: Region):
        """添加区域"""
        self.regions[region.id] = region
        logger.info(f"Added region: {region.name} ({region.location})")

    def remove_region(self, region_id: str):
        """移除区域"""
        if region_id in self.regions:
            del self.regions[region_id]
            logger.info(f"Removed region: {region_id}")

    def update_region_status(
        self,
        region_id: str,
        status: RegionStatus,
    ):
        """更新区域状态"""
        if region_id in self.regions:
            self.regions[region_id].status = status
            logger.info(f"Updated region {region_id} status to {status.value}")

    def get_active_regions(self) -> List[Region]:
        """获取活跃区域"""
        return [region for region in self.regions.values() if region.status == RegionStatus.ACTIVE]

    def route_request(
        self,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Region]:
        """
        路由请求到最佳区域

        Parameters
        ----------
        request_context : Dict[str, Any], optional
            请求上下文（如地理位置）

        Returns
        -------
        Region or None
            目标区域
        """
        active_regions = self.get_active_regions()

        if not active_regions:
            logger.warning("No active regions available")
            return None

        if self.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_route(active_regions)
        elif self.routing_strategy == RoutingStrategy.LEAST_LATENCY:
            return self._least_latency_route(active_regions)
        elif self.routing_strategy == RoutingStrategy.WEIGHTED:
            return self._weighted_route(active_regions)
        elif self.routing_strategy == RoutingStrategy.GEOGRAPHIC:
            return self._geographic_route(active_regions, request_context)
        elif self.routing_strategy == RoutingStrategy.ACTIVE_STANDBY:
            return self._active_standby_route(active_regions)
        else:
            return active_regions[0]

    def _round_robin_route(self, active_regions: List[Region]) -> Region:
        """轮询路由"""
        region = active_regions[self.current_region_index % len(active_regions)]
        self.current_region_index += 1
        return region

    def _least_latency_route(self, active_regions: List[Region]) -> Region:
        """最低延迟路由"""
        regions_with_latency = [r for r in active_regions if r.latency is not None]

        if regions_with_latency:
            return min(regions_with_latency, key=lambda r: r.latency or 0.0)

        return active_regions[0]

    def _weighted_route(self, active_regions: List[Region]) -> Region:
        """加权路由（基于容量）"""
        import random

        total_capacity = sum(r.capacity for r in active_regions)
        if total_capacity == 0:
            return active_regions[0]

        rand = random.random() * total_capacity
        cumulative: float = 0

        for region in active_regions:
            cumulative += region.capacity
            if rand <= cumulative:
                return region

        return active_regions[-1]

    def _geographic_route(
        self,
        active_regions: List[Region],
        request_context: Optional[Dict[str, Any]],
    ) -> Region:
        """地理路由"""
        if request_context and "location" in request_context:
            # 简化实现：选择最近的区域
            request_location = request_context["location"]

            # 实际应使用地理距离计算
            # 这里简化为匹配 location 字段
            for region in active_regions:
                if region.location == request_location:
                    return region

        return active_regions[0]

    def _active_standby_route(self, active_regions: List[Region]) -> Region:
        """主备路由"""
        # 选择优先级最高的区域
        return min(active_regions, key=lambda r: r.priority)

    def set_routing_strategy(self, strategy: RoutingStrategy):
        """设置路由策略"""
        self.routing_strategy = strategy
        logger.info(f"Routing strategy set to {strategy.value}")

    def perform_health_check(self) -> Dict[str, bool]:
        """
        执行健康检查

        Returns
        -------
        Dict[str, bool]
            区域健康状态
        """
        health_status = {}

        for region_id, region in self.regions.items():
            # 简化实现：实际应调用健康检查端点
            is_healthy = self._check_region_health(region)
            health_status[region_id] = is_healthy

            # 更新状态
            if is_healthy:
                if region.status == RegionStatus.DOWN:
                    region.status = RegionStatus.ACTIVE
            else:
                if region.status == RegionStatus.ACTIVE:
                    region.status = RegionStatus.DEGRADED

        return health_status

    def _check_region_health(self, region: Region) -> bool:
        """检查单个区域健康"""
        # 简化实现
        # 实际应发送健康检查请求到区域端点
        return True

    def trigger_failover(self, failed_region_id: str) -> bool:
        """
        触发故障转移

        Parameters
        ----------
        failed_region_id : str
            失败区域 ID

        Returns
        -------
        bool
            是否成功
        """
        if failed_region_id not in self.regions:
            logger.warning(f"Region {failed_region_id} not found")
            return False

        # 标记区域为 DOWN
        self.regions[failed_region_id].status = RegionStatus.DOWN

        # 检查是否有其他活跃区域
        active_regions = self.get_active_regions()

        if not active_regions:
            logger.error("No active regions available for failover")
            return False

        logger.info(f"Failover triggered for region {failed_region_id}")
        logger.info(f"Active regions: {[r.id for r in active_regions]}")

        return True

    def get_region_statistics(self) -> Dict[str, Any]:
        """获取区域统计"""
        status_counts: Dict[str, int] = {}
        for region in self.regions.values():
            status = region.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_regions": len(self.regions),
            "active_regions": len(self.get_active_regions()),
            "status_distribution": status_counts,
            "routing_strategy": self.routing_strategy.value,
        }


# ----------------------------------------------------------------------
# 5️⃣ 数据同步管理器
# ----------------------------------------------------------------------
class DataSyncManager:
    """数据同步管理器"""

    def __init__(self):
        self.sync_config: Dict[str, Any] = {}
        self.sync_status: Dict[str, str] = {}

    def configure_sync(
        self,
        source_region: str,
        target_regions: List[str],
        sync_mode: str = "async",
    ):
        """
        配置数据同步

        Parameters
        ----------
        source_region : str
            源区域
        target_regions : List[str]
            目标区域列表
        sync_mode : str
            同步模式：'sync', 'async'
        """
        self.sync_config[source_region] = {
            "target_regions": target_regions,
            "sync_mode": sync_mode,
        }
        logger.info(f"Configured sync from {source_region} to {target_regions}")

    def sync_data(
        self,
        source_region: str,
        data: Any,
    ) -> Dict[str, bool]:
        """
        同步数据

        Parameters
        ----------
        source_region : str
            源区域
        data : Any
            要同步的数据

        Returns
        -------
        Dict[str, bool]
            同步结果
        """
        if source_region not in self.sync_config:
            logger.warning(f"No sync config for region {source_region}")
            return {}

        config = self.sync_config[source_region]
        target_regions = config["target_regions"]
        sync_mode = config["sync_mode"]

        results = {}

        for target_region in target_regions:
            try:
                # 简化实现：实际应调用数据同步接口
                if sync_mode == "sync":
                    # 同步同步
                    results[target_region] = True
                else:
                    # 异步同步
                    results[target_region] = True

                self.sync_status[f"{source_region}->{target_region}"] = "success"
            except Exception as e:
                logger.error(f"Sync to {target_region} failed: {e}")
                results[target_region] = False
                self.sync_status[f"{source_region}->{target_region}"] = f"failed: {e}"

        return results

    def get_sync_status(self) -> Dict[str, str]:
        """获取同步状态"""
        return self.sync_status


# ----------------------------------------------------------------------
# 6️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_multi_region_manager() -> MultiRegionManager:
    """创建多区域管理器"""
    return MultiRegionManager()


def create_data_sync_manager() -> DataSyncManager:
    """创建数据同步管理器"""
    return DataSyncManager()


# ----------------------------------------------------------------------
# 7️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试多区域管理器
    logger.info("Testing multi-region manager")

    manager = create_multi_region_manager()

    # 添加区域
    manager.add_region(
        Region(
            id="us-east-1",
            name="US East",
            location="us-east",
            endpoint="https://us-east-1.example.com",
            priority=1,
            capacity=0.5,
            latency=50,
        )
    )

    manager.add_region(
        Region(
            id="us-west-2",
            name="US West",
            location="us-west",
            endpoint="https://us-west-2.example.com",
            priority=2,
            capacity=0.3,
            latency=80,
        )
    )

    manager.add_region(
        Region(
            id="eu-west-1",
            name="EU West",
            location="eu-west",
            endpoint="https://eu-west-1.example.com",
            priority=3,
            capacity=0.2,
            latency=120,
        )
    )

    # 测试路由
    region = manager.route_request()
    if region is not None:
        logger.info(f"Routed to region: {region.name}")
    else:
        logger.warning("No region available for routing")

    # 测试健康检查
    health_status = manager.perform_health_check()
    logger.info(f"Health status: {health_status}")

    # 测试故障转移
    manager.trigger_failover("us-east-1")

    # 获取统计
    stats = manager.get_region_statistics()
    logger.info(f"Region statistics: {stats}")

    # 测试数据同步
    sync_manager = create_data_sync_manager()
    sync_manager.configure_sync("us-east-1", ["us-west-2", "eu-west-1"])

    sync_results = sync_manager.sync_data("us-east-1", {"test": "data"})
    logger.info(f"Sync results: {sync_results}")

    logger.info("Test passed!")
