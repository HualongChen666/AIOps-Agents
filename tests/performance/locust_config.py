# -*- coding: utf-8 -*-
"""
Locust性能测试配置
支持不同并发级别和测试场景
"""

from locust import LoadTestShape


class CustomLoadShape(LoadTestShape):
    """
    自定义负载测试形状
    支持多种测试场景：阶梯式、尖峰式、波动式
    """

    def __init__(self):
        super().__init__()
        self.test_duration = 600  # 10分钟
        self.stages = [
            # 阶梯式负载测试
            {"duration": 60, "users": 10, "spawn_rate": 5},
            {"duration": 60, "users": 50, "spawn_rate": 10},
            {"duration": 60, "users": 100, "spawn_rate": 20},
            {"duration": 60, "users": 500, "spawn_rate": 50},
            {"duration": 60, "users": 1000, "spawn_rate": 100},
            {"duration": 60, "users": 5000, "spawn_rate": 500},
            {"duration": 60, "users": 10000, "spawn_rate": 1000},
            {"duration": 60, "users": 50000, "spawn_rate": 5000},
            {"duration": 60, "users": 10000, "spawn_rate": 1000},
            {"duration": 60, "users": 5000, "spawn_rate": 500},
            {"duration": 60, "users": 1000, "spawn_rate": 100},
            {"duration": 60, "users": 100, "spawn_rate": 20},
        ]

    def tick(self):
        """
        返回当前时间点的用户数和生成速率
        """
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
            run_time -= stage["duration"]

        return None


class StaircaseLoadShape(LoadTestShape):
    """
    阶梯式负载测试
    逐步增加用户数，测试系统在不同负载下的性能
    """

    def __init__(self):
        super().__init__()
        self.max_users = 10000
        self.step_duration = 60  # 每个阶梯60秒
        self.step_users = 100  # 每个阶梯增加100用户

    def tick(self):
        run_time = self.get_run_time()

        if run_time < self.step_duration:
            return (self.step_users, self.step_users)

        current_step = int(run_time / self.step_duration)
        users = min(self.step_users * (current_step + 1), self.max_users)

        if users >= self.max_users:
            return None

        return (users, self.step_users)


class SpikeLoadShape(LoadTestShape):
    """
    尖峰式负载测试
    模拟突发流量，测试系统的抗压能力
    """

    def __init__(self):
        super().__init__()
        self.baseline_users = 100
        self.spike_users = 10000
        self.spike_duration = 60  # 尖峰持续60秒
        self.cycle_duration = 300  # 每个周期5分钟

    def tick(self):
        run_time = self.get_run_time()
        cycle_time = run_time % self.cycle_duration

        if cycle_time < self.spike_duration:
            return (self.spike_users, self.spike_users)
        else:
            return (self.baseline_users, self.baseline_users)


class WaveLoadShape(LoadTestShape):
    """
    波动式负载测试
    模拟真实场景中的流量波动
    """

    def __init__(self):
        super().__init__()
        self.min_users = 100
        self.max_users = 5000
        self.wave_period = 120  # 波动周期2分钟

    def tick(self):
        run_time = self.get_run_time()

        # 使用正弦函数模拟波动
        import math

        wave = (math.sin(run_time * 2 * math.pi / self.wave_period) + 1) / 2
        users = int(self.min_users + wave * (self.max_users - self.min_users))

        return (users, 100)


class ConstantLoadShape(LoadTestShape):
    """
    恒定负载测试
    保持恒定的用户数，测试系统稳定性
    """

    def __init__(self):
        super().__init__()
        self.users = 1000
        self.spawn_rate = 100

    def tick(self):
        return (self.users, self.spawn_rate)


# 测试场景配置
TEST_SCENARIOS = {
    "staircase": {
        "name": "阶梯式负载测试",
        "shape": StaircaseLoadShape,
        "description": "逐步增加用户数，测试系统在不同负载下的性能",
    },
    "spike": {
        "name": "尖峰式负载测试",
        "shape": SpikeLoadShape,
        "description": "模拟突发流量，测试系统的抗压能力",
    },
    "wave": {
        "name": "波动式负载测试",
        "shape": WaveLoadShape,
        "description": "模拟真实场景中的流量波动",
    },
    "constant": {
        "name": "恒定负载测试",
        "shape": ConstantLoadShape,
        "description": "保持恒定的用户数，测试系统稳定性",
    },
    "custom": {
        "name": "自定义负载测试",
        "shape": CustomLoadShape,
        "description": "自定义的负载测试场景",
    },
}

# 并发级别配置
CONCURRENCY_LEVELS = {
    "low": {"name": "低并发", "users": 10, "spawn_rate": 5, "description": "模拟少量用户访问"},
    "medium": {"name": "中并发", "users": 100, "spawn_rate": 20, "description": "模拟中等用户访问"},
    "high": {"name": "高并发", "users": 1000, "spawn_rate": 100, "description": "模拟高用户访问"},
    "very_high": {
        "name": "超高并发",
        "users": 10000,
        "spawn_rate": 1000,
        "description": "模拟超高用户访问",
    },
    "extreme": {
        "name": "极限并发",
        "users": 50000,
        "spawn_rate": 5000,
        "description": "模拟极限用户访问",
    },
}
