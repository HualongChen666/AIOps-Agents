# -*- coding: utf-8 -*-
"""
线程安全组件
Thread Safety Components

提供线程安全的资源管理，基于GitHub上Hermes Agent项目的经验。
包括主线程初始化、工作线程执行、线程安全的SessionDB。
"""

import threading
from typing import Dict, Any, Optional


class SubAgentBuilder:
    """
    子agent构建器（主线程初始化）
    
    在主线程中初始化子agent，避免在工作线程中初始化非线程安全的资源。
    基于GitHub上Hermes Agent项目的经验，httpx/SSL客户端不是线程安全的。
    """
    
    def __init__(self):
        """初始化构建器"""
        self._initialized_clients = {}
        self._lock = threading.Lock()
    
    def build_client(self, client_type: str, config: Dict[str, Any]) -> Any:
        """
        在主线程构建客户端
        
        Args:
            client_type: 客户端类型
            config: 客户端配置
        
        Returns:
            客户端实例
        """
        with self._lock:
            if client_type not in self._initialized_clients:
                # 在主线程初始化客户端
                self._initialized_clients[client_type] = self._create_client(client_type, config)
            return self._initialized_clients[client_type]
    
    def _create_client(self, client_type: str, config: Dict[str, Any]) -> Any:
        """
        创建客户端（实际实现）
        
        Args:
            client_type: 客户端类型
            config: 客户端配置
        
        Returns:
            客户端实例
        """
        # 这里应该是实际的客户端创建逻辑
        # 由于这是框架代码，返回一个占位符
        return {"type": client_type, "config": config}


class SubAgentRunner:
    """
    子agent运行器（工作线程执行）
    
    在工作线程中执行子agent，避免初始化竞争。
    """
    
    def __init__(self, builder: SubAgentBuilder):
        """
        初始化运行器
        
        Args:
            builder: 子agent构建器
        """
        self.builder = builder
    
    def run_child_agent(self, agent: Any, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        在工作线程运行子agent
        
        Args:
            agent: 子agent实例
            task: 任务字典
        
        Returns:
            执行结果
        """
        # 在工作线程中执行agent
        # 使用主线程初始化的客户端
        result = agent.execute(task)
        return result


class SessionDB:
    """
    会话数据库（线程安全）
    
    提供线程安全的会话管理，避免并发访问导致的数据竞争。
    基于GitHub上Hermes Agent项目的经验，子agent共享父agent的SessionDB。
    """
    
    def __init__(self):
        """初始化会话数据库"""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_session(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """
        创建会话（线程安全）
        
        Args:
            session_id: 会话ID
            **kwargs: 会话属性
        
        Returns:
            会话字典
        """
        with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "id": session_id,
                    "messages": [],
                    "created_at": None,
                    **kwargs
                }
            return self.sessions[session_id]
    
    def append_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        追加消息（线程安全）
        
        Args:
            session_id: 会话ID
            message: 消息字典
        
        Returns:
            是否成功
        """
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["messages"].append(message)
                return True
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话（线程安全）
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话字典或None
        """
        with self._lock:
            return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话（线程安全）
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否成功
        """
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有会话（线程安全）
        
        Returns:
            所有会话的副本
        """
        with self._lock:
            return self.sessions.copy()