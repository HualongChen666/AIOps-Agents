# -*- coding: utf-8 -*-
"""
Smart Cache Strategy
智能缓存策略
"""


class SmartCacheStrategy:
    """智能缓存策略"""

    # 大对象占用内存高，命中率收益不足以抵消内存成本时缩短 TTL，促使其尽早释放
    _LARGE_OBJECT_BYTES = 1024 * 1024
    _HUGE_OBJECT_BYTES = 8 * 1024 * 1024

    @staticmethod
    def get_ttl(key: str, access_count: int, data_size: int = 0) -> int:
        """按访问频次与数据体积动态计算 TTL（秒）。

        热数据（高频访问）保留较短 TTL 以便尽快刷新；冷数据保留长 TTL。
        数据体积越大，内存占用越高，TTL 相应缩短以降低驻留成本。
        """
        if access_count > 100:
            ttl = 60  # 热数据
        elif access_count > 10:
            ttl = 300  # 温数据
        else:
            ttl = 3600  # 冷数据

        if data_size >= SmartCacheStrategy._HUGE_OBJECT_BYTES:
            ttl = max(30, ttl // 4)
        elif data_size >= SmartCacheStrategy._LARGE_OBJECT_BYTES:
            ttl = max(30, ttl // 2)
        return ttl

    @staticmethod
    def get_cache_tier(key: str, access_count: int = 0) -> str:
        """按传入的访问频次判定缓存层级。

        ``access_count`` 必须由调用方从真实缓存统计中提供；缺省为 0
        （尚未被访问，即 cold）。
        """
        if access_count > 100:
            return "hot"
        elif access_count > 10:
            return "warm"
        return "cold"
