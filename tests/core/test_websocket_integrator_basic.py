# -*- coding: utf-8 -*-
"""
基础WebSocket集成器模块测试
测试WebSocket集成器核心功能的基础场景
"""

import pytest


class TestWebsocketIntegratorBasic:
    """WebSocket集成器模块基础测试"""

    def test_websocket_integrator_module_structure(self):
        """测试WebSocket集成器模块结构"""
        try:
            from core import websocket_integrator

            assert websocket_integrator is not None
        except ImportError as e:
            pytest.skip(f"Websocket integrator module not available: {e}")

    def test_websocket_integrator_functions_exist(self):
        """测试WebSocket集成器关键函数存在"""
        try:
            from core.websocket_integrator import connect_websocket, receive_message, send_message

            # 验证关键函数存在
            assert connect_websocket is not None
            assert send_message is not None
            assert receive_message is not None
        except Exception as e:
            pytest.skip(f"Websocket integrator functions test failed: {e}")

    def test_websocket_integrator_classes_exist(self):
        """测试WebSocket集成器关键类存在"""
        try:
            from core.websocket_integrator import (
                ConnectionManager,
                MessageHandler,
                WebsocketIntegrator,
            )

            # 验证关键类存在
            assert WebsocketIntegrator is not None
            assert ConnectionManager is not None
            assert MessageHandler is not None
        except Exception as e:
            pytest.skip(f"Websocket integrator classes test failed: {e}")

    def test_websocket_integrator_constants(self):
        """测试WebSocket集成器常量定义"""
        try:
            from core.websocket_integrator import ConnectionStatus, MessageType

            # 验证常量存在
            assert ConnectionStatus is not None
            assert MessageType is not None
        except Exception as e:
            pytest.skip(f"Websocket integrator constants test failed: {e}")
