# -*- coding: utf-8 -*-
"""
storage_optimizer.py
--------------------
成本优化 - 存储优化模块。

功能：
- 存储使用分析
- 数据生命周期管理
- 冷热数据分层
- 数据压缩
- 存储成本优化
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 存储类型枚举
# ----------------------------------------------------------------------
class StorageType(Enum):
    """存储类型"""

    HOT = "hot"  # 热存储（高频访问）
    WARM = "warm"  # 温存储（中频访问）
    COLD = "cold"  # 冷存储（低频访问）
    ARCHIVE = "archive"  # 归档存储（极少访问）


# ----------------------------------------------------------------------
# 2️⃣ 数据对象
# ----------------------------------------------------------------------
@dataclass
class DataObject:
    """数据对象"""

    id: str
    name: str
    size: int  # 字节
    storage_type: StorageType = StorageType.HOT
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_days(self) -> int:
        """数据年龄（天）"""
        return (datetime.now() - self.created_at).days

    @property
    def days_since_last_access(self) -> int:
        """距上次访问天数"""
        return (datetime.now() - self.last_accessed).days

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "storage_type": self.storage_type.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "path": self.path,
            "age_days": self.age_days,
            "days_since_last_access": self.days_since_last_access,
        }


# ----------------------------------------------------------------------
# 3️⃣ 存储统计
# ----------------------------------------------------------------------
@dataclass
class StorageStatistics:
    """存储统计"""

    total_objects: int = 0
    total_size: int = 0
    by_type: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    compression_ratio: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_objects": self.total_objects,
            "total_size": self.total_size,
            "total_size_gb": self.total_size / (1024**3),
            "by_type": self.by_type,
            "compression_ratio": self.compression_ratio,
        }


# ----------------------------------------------------------------------
# 4️⃣ 存储管理器
# ----------------------------------------------------------------------
class StorageManager:
    """存储管理器"""

    def __init__(self):
        self.objects: Dict[str, DataObject] = {}
        self.storage_costs: Dict[StorageType, float] = {
            StorageType.HOT: 0.23,  # $0.23/GB/月
            StorageType.WARM: 0.12,  # $0.12/GB/月
            StorageType.COLD: 0.04,  # $0.04/GB/月
            StorageType.ARCHIVE: 0.01,  # $0.01/GB/月
        }

    def add_object(self, obj: DataObject):
        """添加数据对象"""
        self.objects[obj.id] = obj
        logger.debug(f"Added data object: {obj.name} ({obj.size} bytes)")

    def remove_object(self, obj_id: str):
        """移除数据对象"""
        if obj_id in self.objects:
            del self.objects[obj_id]
            logger.debug(f"Removed data object: {obj_id}")

    def get_object(self, obj_id: str) -> Optional[DataObject]:
        """获取数据对象"""
        return self.objects.get(obj_id)

    def access_object(self, obj_id: str):
        """访问数据对象"""
        if obj_id in self.objects:
            obj = self.objects[obj_id]
            obj.last_accessed = datetime.now()
            obj.access_count += 1

    def get_statistics(self) -> StorageStatistics:
        """获取存储统计"""
        stats = StorageStatistics()

        by_type: Dict[str, Dict[str, Any]] = {
            storage_type.value: {"count": 0, "size": 0} for storage_type in StorageType
        }

        for obj in self.objects.values():
            stats.total_objects += 1
            stats.total_size += obj.size

            storage_type = obj.storage_type.value
            by_type[storage_type]["count"] += 1
            by_type[storage_type]["size"] += obj.size

        stats.by_type = by_type

        return stats

    def estimate_monthly_cost(self) -> float:
        """估算月度存储成本"""
        stats = self.get_statistics()
        total_cost = 0.0

        for storage_type_str, type_stats in stats.by_type.items():
            storage_type = StorageType(storage_type_str)
            size_gb = type_stats["size"] / (1024**3)
            cost_per_gb = self.storage_costs[storage_type]
            total_cost += size_gb * cost_per_gb

        return total_cost


# ----------------------------------------------------------------------
# 5️⃣ 存储优化器
# ----------------------------------------------------------------------
class StorageOptimizer:
    """存储优化器"""

    def __init__(self, storage_manager: StorageManager):
        """
        Parameters
        ----------
        storage_manager : StorageManager
            存储管理器
        """
        self.storage_manager = storage_manager
        self.tiering_rules = {
            StorageType.HOT: {"max_age_days": 7, "min_access_count": 10},
            StorageType.WARM: {"max_age_days": 30, "min_access_count": 5},
            StorageType.COLD: {"max_age_days": 90, "min_access_count": 1},
            StorageType.ARCHIVE: {"max_age_days": 365, "min_access_count": 0},
        }

    def analyze_storage_tiering(self) -> Dict[str, List[str]]:
        """
        分析存储分层

        Returns
        -------
        Dict[str, List[str]]
            分层建议 {storage_type: [object_ids]}
        """
        recommendations: Dict[str, List[str]] = {
            storage_type.value: [] for storage_type in StorageType
        }

        for obj_id, obj in self.storage_manager.objects.items():
            recommended_type = self._recommend_storage_type(obj)
            if recommended_type != obj.storage_type:
                recommendations[recommended_type.value].append(obj_id)

        return recommendations

    def _recommend_storage_type(self, obj: DataObject) -> StorageType:
        """推荐存储类型"""
        # 根据访问频率和年龄推荐
        access_frequency = obj.access_count / max(1, obj.age_days)
        days_since_access = obj.days_since_last_access

        if access_frequency > 1.0 and days_since_access < 7:
            return StorageType.HOT
        elif access_frequency > 0.1 and days_since_access < 30:
            return StorageType.WARM
        elif access_frequency > 0.01 and days_since_access < 90:
            return StorageType.COLD
        else:
            return StorageType.ARCHIVE

    def apply_tiering(self, recommendations: Dict[str, List[str]]) -> Dict[str, int]:
        """
        应用分层建议

        Parameters
        ----------
        recommendations : Dict[str, List[str]]
            分层建议

        Returns
        -------
        Dict[str, int]
            应用结果 {storage_type: count}
        """
        results = {}

        for storage_type_str, object_ids in recommendations.items():
            storage_type = StorageType(storage_type_str)
            count = 0

            for obj_id in object_ids:
                obj = self.storage_manager.get_object(obj_id)
                if obj:
                    obj.storage_type = storage_type
                    count += 1
                    logger.info(f"Moved {obj.name} to {storage_type.value}")

            results[storage_type_str] = count

        return results

    def identify_unused_data(
        self,
        days_threshold: int = 90,
    ) -> List[DataObject]:
        """
        识别未使用数据

        Parameters
        ----------
        days_threshold : int
            天数阈值

        Returns
        -------
        List[DataObject]
            未使用的数据对象列表
        """
        unused = []

        for obj in self.storage_manager.objects.values():
            if obj.days_since_last_access > days_threshold:
                unused.append(obj)

        # 按大小排序
        unused.sort(key=lambda o: o.size, reverse=True)

        return unused

    def suggest_deletion(
        self,
        size_threshold: int = 1024 * 1024 * 1024,  # 1GB
        days_threshold: int = 180,
    ) -> List[DataObject]:
        """
        建议删除的数据

        Parameters
        ----------
        size_threshold : int
            大小阈值（字节）
        days_threshold : int
            天数阈值

        Returns
        -------
        List[DataObject]
            建议删除的数据对象列表
        """
        candidates = []

        for obj in self.storage_manager.objects.items():
            obj_data = obj[1]
            if obj_data.size > size_threshold and obj_data.days_since_last_access > days_threshold:
                candidates.append(obj_data)

        candidates.sort(key=lambda o: o.size, reverse=True)

        return candidates

    def estimate_savings(
        self,
        recommendations: Dict[str, List[str]],
    ) -> Dict[str, float]:
        """
        估算节省

        Parameters
        ----------
        recommendations : Dict[str, List[str]]
            分层建议

        Returns
        -------
        Dict[str, float]
            节省估算（美元/月）
        """
        savings = {}

        for obj_id, obj in self.storage_manager.objects.items():
            # 查找推荐的新类型
            new_type = None
            for storage_type_str, object_ids in recommendations.items():
                if obj_id in object_ids:
                    new_type = StorageType(storage_type_str)
                    break

            if new_type and new_type != obj.storage_type:
                # 计算节省
                old_cost = self.storage_manager.storage_costs[obj.storage_type]
                new_cost = self.storage_manager.storage_costs[new_type]
                size_gb = obj.size / (1024**3)

                monthly_saving = (old_cost - new_cost) * size_gb

                if monthly_saving > 0:
                    savings[obj_id] = monthly_saving

        return savings


# ----------------------------------------------------------------------
# 6️⃣ 数据压缩器
# ----------------------------------------------------------------------
class DataCompressor:
    """数据压缩器"""

    def __init__(self):
        self.compression_stats: Dict[str, Dict[str, Any]] = {}

    def compress_data(
        self,
        data: bytes,
        algorithm: str = "gzip",
    ) -> tuple[bytes, float]:
        """
        压缩数据

        Parameters
        ----------
        data : bytes
            原始数据
        algorithm : str
            压缩算法

        Returns
        -------
        tuple[bytes, float]
            (压缩后数据, 压缩比)
        """
        import gzip
        import zlib

        original_size = len(data)

        if algorithm == "gzip":
            compressed = gzip.compress(data)
        elif algorithm == "zlib":
            compressed = zlib.compress(data)
        else:
            compressed = data

        compression_ratio = original_size / len(compressed) if len(compressed) > 0 else 1.0

        return compressed, compression_ratio

    def estimate_compression_savings(
        self,
        objects: List[DataObject],
        estimated_ratio: float = 2.0,
    ) -> Dict[str, Any]:
        """
        估算压缩节省

        Parameters
        ----------
        objects : List[DataObject]
            数据对象列表
        estimated_ratio : float
            估算压缩比

        Returns
        -------
        Dict[str, Any]
            节省估算
        """
        total_size = sum(obj.size for obj in objects)
        estimated_compressed_size = total_size / estimated_ratio
        savings = total_size - estimated_compressed_size

        return {
            "total_size": total_size,
            "estimated_compressed_size": estimated_compressed_size,
            "savings": savings,
            "savings_gb": savings / (1024**3),
            "compression_ratio": estimated_ratio,
        }


# ----------------------------------------------------------------------
# 7️⃣ 数据生命周期管理器
# ----------------------------------------------------------------------
class DataLifecycleManager:
    """数据生命周期管理器"""

    def __init__(self, storage_manager: StorageManager):
        """
        Parameters
        ----------
        storage_manager : StorageManager
            存储管理器
        """
        self.storage_manager = storage_manager
        self.lifecycle_policies: Dict[str, Dict[str, Any]] = {}

    def add_lifecycle_policy(
        self,
        policy_id: str,
        pattern: str,
        rules: Dict[str, Any],
    ):
        """
        添加生命周期策略

        Parameters
        ----------
        policy_id : str
            策略 ID
        pattern : str
            匹配模式（如文件名模式）
        rules : Dict[str, Any]
            规则（如 transition_after_days, delete_after_days）
        """
        self.lifecycle_policies[policy_id] = {
            "pattern": pattern,
            "rules": rules,
        }
        logger.info(f"Added lifecycle policy: {policy_id}")

    def apply_lifecycle_policies(self) -> List[Dict[str, Any]]:
        """
        应用生命周期策略

        Returns
        -------
        List[Dict[str, Any]]
            执行的操作列表
        """
        actions = []

        for policy_id, policy in self.lifecycle_policies.items():
            pattern = policy["pattern"]
            rules = policy["rules"]

            for obj in list(self.storage_manager.objects.values()):
                if pattern in obj.name:
                    # 检查是否需要转换存储类型
                    if "transition_after_days" in rules:
                        threshold = rules["transition_after_days"]
                        if obj.age_days > threshold:
                            new_type = StorageType(rules.get("transition_to", "cold"))
                            if obj.storage_type != new_type:
                                obj.storage_type = new_type
                                actions.append(
                                    {
                                        "policy_id": policy_id,
                                        "object_id": obj.id,
                                        "action": "transition",
                                        "to": new_type.value,
                                    }
                                )

                    # 检查是否需要删除
                    if "delete_after_days" in rules:
                        threshold = rules["delete_after_days"]
                        if obj.age_days > threshold:
                            self.storage_manager.remove_object(obj.id)
                            actions.append(
                                {
                                    "policy_id": policy_id,
                                    "object_id": obj.id,
                                    "action": "delete",
                                }
                            )

        return actions


# ----------------------------------------------------------------------
# 8️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_storage_manager() -> StorageManager:
    """创建存储管理器"""
    return StorageManager()


def create_storage_optimizer(storage_manager: StorageManager) -> StorageOptimizer:
    """创建存储优化器"""
    return StorageOptimizer(storage_manager)


def create_data_compressor() -> DataCompressor:
    """创建数据压缩器"""
    return DataCompressor()


def create_data_lifecycle_manager(storage_manager: StorageManager) -> DataLifecycleManager:
    """创建数据生命周期管理器"""
    return DataLifecycleManager(storage_manager)


# ----------------------------------------------------------------------
# 9️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试存储优化器
    logger.info("Testing storage optimizer")

    storage = create_storage_manager()
    optimizer = create_storage_optimizer(storage)

    # 添加测试数据
    for i in range(100):
        storage.add_object(
            DataObject(
                id=f"obj-{i}",
                name=f"data-{i}.log",
                size=1024 * 1024 * (i % 10 + 1),  # 1-10 MB
                storage_type=StorageType.HOT,
                created_at=datetime.now() - timedelta(days=i % 120),
                last_accessed=datetime.now() - timedelta(days=i % 60),
                access_count=i % 20,
            )
        )

    # 分析分层
    recommendations = optimizer.analyze_storage_tiering()

    logger.info("Tiering recommendations:")
    for storage_type, object_ids in recommendations.items():
        logger.info(f"  {storage_type}: {len(object_ids)} objects")

    # 应用分层
    results = optimizer.apply_tiering(recommendations)
    logger.info(f"Applied tiering: {results}")

    # 估算节省
    savings = optimizer.estimate_savings(recommendations)
    total_savings = sum(savings.values())
    logger.info(f"Estimated monthly savings: ${total_savings:.2f}")

    # 识别未使用数据
    unused = optimizer.identify_unused_data(days_threshold=90)
    logger.info(f"Unused data (>90 days): {len(unused)} objects")

    # 获取统计
    stats = storage.get_statistics()
    logger.info(f"Storage statistics: {stats.to_dict()}")

    # 估算成本
    cost = storage.estimate_monthly_cost()
    logger.info(f"Estimated monthly cost: ${cost:.2f}")

    # 测试数据压缩器
    logger.info("Testing data compressor")

    compressor = create_data_compressor()

    test_data = b"Hello, World! " * 1000
    compressed, ratio = compressor.compress_data(test_data)

    logger.info(f"Original size: {len(test_data)} bytes")
    logger.info(f"Compressed size: {len(compressed)} bytes")
    logger.info(f"Compression ratio: {ratio:.2f}x")

    logger.info("Test passed!")
