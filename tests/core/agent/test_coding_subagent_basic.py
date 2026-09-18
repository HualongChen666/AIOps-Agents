# -*- coding: utf-8 -*-
"""
基础优化测试
Basic Optimization Tests

测试超时机制、参数验证、并发控制、线程安全、进度显示等基础优化功能。
"""

import pytest
import time
import threading
from core.agent.stall_detector import StallDetector, TimeoutError, TimeoutContext
from core.agent.parameter_validator import ParameterValidator
from core.agent.tool_call_runtime import ToolCallRuntime
from core.agent.thread_safety import SubAgentBuilder, SubAgentRunner, SessionDB
from core.agent.progress_tracker import ProgressTracker


class TestStallDetector:
    """停滞检测器测试"""
    
    def test_stall_detection(self):
        """测试停滞检测"""
        detector = StallDetector(stall_timeout=1)
        
        # 初始状态应该没有停滞
        assert not detector.check_stall()
        
        # 等待超过超时时间
        time.sleep(1.1)
        
        # 应该检测到停滞
        assert detector.check_stall()
    
    def test_update_activity(self):
        """测试活动更新"""
        detector = StallDetector(stall_timeout=1)
        
        # 更新活动
        detector.update_activity()
        
        # 等待一段时间但不超过超时
        time.sleep(0.5)
        
        # 不应该停滞
        assert not detector.check_stall()
    
    def test_idle_time(self):
        """测试空闲时间计算"""
        detector = StallDetector(stall_timeout=10)
        
        detector.update_activity()
        time.sleep(0.1)
        
        idle_time = detector.get_idle_time()
        assert 0.1 <= idle_time <= 0.2
    
    def test_reset(self):
        """测试重置"""
        detector = StallDetector(stall_timeout=1)
        
        time.sleep(1.1)
        assert detector.check_stall()
        
        detector.reset()
        assert not detector.check_stall()


class TestTimeoutContext:
    """超时上下文测试"""
    
    def test_timeout_detection(self):
        """测试超时检测"""
        context = TimeoutContext(timeout=1, task_id="test_task")
        
        # 初始状态应该没有超时
        assert not context.check_timeout()
        
        # 等待超过超时时间
        time.sleep(1.1)
        
        # 应该检测到超时
        assert context.check_timeout()
    
    def test_timeout_info(self):
        """测试超时信息"""
        context = TimeoutContext(timeout=1, task_id="test_task")
        
        time.sleep(1.1)
        context.check_timeout()
        
        info = context.get_timeout_info()
        assert info["task_id"] == "test_task"
        assert info["timeout"] == 1
        assert info["timeout_triggered"] is True
        assert info["timeout_reason"] is not None


class TestParameterValidator:
    """参数验证器测试"""
    
    def test_valid_context(self):
        """测试有效context"""
        validator = ParameterValidator()
        context = {
            "tool": "bash",
            "params": {"command": "ls"}
        }
        available_tools = ["bash", "read_file"]
        
        result = validator.validate(context, available_tools)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_missing_required_field(self):
        """测试缺少必需字段"""
        validator = ParameterValidator()
        context = {"tool": "bash"}  # 缺少params
        available_tools = ["bash"]
        
        result = validator.validate(context, available_tools)
        assert result["valid"] is False
        assert any("params" in error for error in result["errors"])
    
    def test_invalid_tool_type(self):
        """测试无效工具类型"""
        validator = ParameterValidator()
        context = {"tool": 123, "params": {}}  # tool不是字符串
        available_tools = ["bash"]
        
        result = validator.validate(context, available_tools)
        assert result["valid"] is False
        assert any("字符串" in error for error in result["errors"])
    
    def test_tool_not_in_whitelist(self):
        """测试工具不在白名单中"""
        validator = ParameterValidator()
        context = {"tool": "dangerous_tool", "params": {}}
        available_tools = ["bash", "read_file"]
        
        result = validator.validate(context, available_tools)
        assert result["valid"] is False
        assert any("不在可用工具列表中" in error for error in result["errors"])
    
    def test_dangerous_tool(self):
        """测试危险工具"""
        validator = ParameterValidator()
        context = {"tool": "eval", "params": {}}
        available_tools = ["eval", "bash"]
        
        result = validator.validate(context, available_tools)
        assert result["valid"] is False
        assert any("危险工具" in error for error in result["errors"])
    
    def test_command_injection(self):
        """测试命令注入检测"""
        validator = ParameterValidator()
        context = {
            "tool": "bash",
            "params": {"command": "ls; rm -rf /"}
        }
        available_tools = ["bash"]
        
        result = validator.validate(context, available_tools)
        # bash命令注入验证
        assert result["valid"] is False


class TestToolCallRuntime:
    """工具调用运行时测试"""
    
    def test_acquire_execution_slot(self):
        """测试获取执行槽位"""
        runtime = ToolCallRuntime(max_concurrent=2)
        
        with runtime.acquire_execution_slot("bash"):
            # 在槽位内执行
            active_count = runtime.get_active_count("bash")
            assert active_count == 1
        
        # 释放后应该为0
        active_count = runtime.get_active_count("bash")
        assert active_count == 0
    
    def test_concurrent_limit(self):
        """测试并发限制"""
        runtime = ToolCallRuntime(max_concurrent=2)
        
        acquired = []
        def acquire_slot():
            try:
                with runtime.acquire_execution_slot("bash"):
                    acquired.append(True)
                    time.sleep(0.1)
            except:
                acquired.append(False)
        
        # 启动3个线程，但只有2个槽位
        threads = [threading.Thread(target=acquire_slot) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Semaphore不会阻塞，只是限制同时执行的槽位数
        # 所以所有3个线程都会成功，但不会同时超过2个
        assert sum(acquired) == 3
    
    def test_get_concurrency_stats(self):
        """测试获取并发统计"""
        runtime = ToolCallRuntime(max_concurrent=5)
        
        with runtime.acquire_execution_slot("bash"):
            stats = runtime.get_concurrency_stats()
            assert stats["max_concurrent"] == 5
            assert stats["total_active"] == 1
            assert stats["available_slots"] == 4


class TestSessionDB:
    """会话数据库测试"""
    
    def test_create_session(self):
        """测试创建会话"""
        db = SessionDB()
        
        session = db.create_session("session_1", user="test")
        assert session is not None
        assert session["id"] == "session_1"
        assert session["user"] == "test"
    
    def test_append_message(self):
        """测试追加消息"""
        db = SessionDB()
        db.create_session("session_1")
        
        success = db.append_message("session_1", {"content": "test"})
        assert success is True
        
        session = db.get_session("session_1")
        assert len(session["messages"]) == 1
    
    def test_concurrent_session_access(self):
        """测试并发会话访问"""
        db = SessionDB()
        db.create_session("session_1")
        
        errors = []
        def append_message():
            try:
                for i in range(10):
                    db.append_message("session_1", {"content": f"message_{i}"})
            except Exception as e:
                errors.append(e)
        
        # 启动多个线程并发访问
        threads = [threading.Thread(target=append_message) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该没有错误
        assert len(errors) == 0
        
        # 消息数量应该正确
        session = db.get_session("session_1")
        assert len(session["messages"]) == 50


class TestProgressTracker:
    """进度跟踪器测试"""
    
    def test_register_child(self):
        """测试注册子agent"""
        tracker = ProgressTracker()
        
        tracker.register_child("child_1", "test task")
        progress = tracker.get_progress()
        
        assert progress["total"] == 1
        assert progress["running"] == 1
    
    def test_update_child_status(self):
        """测试更新子agent状态"""
        tracker = ProgressTracker()
        
        tracker.register_child("child_1", "test task")
        tracker.update_child_status("child_1", "completed")
        
        progress = tracker.get_progress()
        assert progress["completed"] == 1
        assert progress["running"] == 0
    
    def test_format_progress(self):
        """测试格式化进度"""
        tracker = ProgressTracker()
        
        tracker.register_child("child_1", "task1")
        tracker.register_child("child_2", "task2")
        tracker.update_child_status("child_1", "completed")
        
        formatted = tracker.format_progress()
        assert "1/2" in formatted
        assert "完成" in formatted or "completed" in formatted.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])