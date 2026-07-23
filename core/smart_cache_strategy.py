# -*- coding: utf-8 -*-
"""
Smart Cache Strategy
智能缓存策略
"""


class SmartCacheStrategy:
    """智能缓存策略"""

    @staticmethod
    def get_ttl(key: str, access_count: int, data_size: int) -> int:
        """动态计算TTL"""
        if access_count > 100:
            return 60  # 热数据
        elif access_count > 10:
            return 300  # 温数据
        else:
            return 3600  # 冷数据

    @staticmethod
    def get_cache_tier(key: str) -> str:
        """获取缓存层级"""
        access_count = 0  # 需要从缓存获取
        if access_count > 100:
            return "hot"
        elif access_count > 10:
            return "warm"
        return "cold"
