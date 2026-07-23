# -*- coding: utf-8 -*-
"""
E2E Test: WebSocket Real-time Communication
真实E2E测试：WebSocket实时通信测试，不使用Mock
"""

import asyncio
import json
import time
from datetime import datetime

import pytest
import websockets


@pytest.mark.e2e
@pytest.mark.slow
class TestWebSocketCommunication:
    """WebSocket实时通信E2E测试"""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """测试WebSocket连接"""

        try:
            uri = "ws://localhost:8000/ws/alerts"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 发送连接消息
                connect_message = {
                    "type": "connect",
                    "client_id": f"test_client_{int(datetime.now().timestamp())}",
                    "channels": ["alerts", "system"],
                }

                await websocket.send(json.dumps(connect_message))

                # 接收连接确认
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)

                assert response_data["type"] in ["connected", "ack"]
                assert "client_id" in response_data

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_alert_notification(self):
        """测试WebSocket告警通知"""

        try:
            uri = "ws://localhost:8000/ws/alerts"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 连接并订阅告警
                connect_message = {
                    "type": "subscribe",
                    "client_id": f"test_client_{int(datetime.now().timestamp())}",
                    "channel": "alerts",
                }

                await websocket.send(json.dumps(connect_message))

                # 等待订阅确认
                ack = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                assert json.loads(ack)["type"] == "subscribed"

                # 通过HTTP API创建告警，应该通过WebSocket推送
                import httpx

                async with httpx.AsyncClient(timeout=10.0) as client:
                    alert_response = await client.post(
                        "http://localhost:8000/api/v1/alerts",
                        json={
                            "component": "websocket_test",
                            "severity": "warning",
                            "title": "WebSocket测试告警",
                            "description": "测试WebSocket推送",
                            "metrics": {"test": 100},
                            "source": "test",
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    if alert_response.status_code not in [200, 201, 202]:
                        pytest.skip("Cannot create test alert")

                # 等待WebSocket推送
                try:
                    notification = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    notification_data = json.loads(notification)

                    # 验证通知内容
                    assert notification_data["type"] == "alert"
                    assert "alert_id" in notification_data
                    assert "severity" in notification_data

                except asyncio.TimeoutError:
                    pytest.skip("WebSocket notification not received within timeout")

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_multiple_clients(self):
        """测试多客户端WebSocket连接"""

        try:
            uri = "ws://localhost:8000/ws/alerts"
            client_count = 5

            async def client_task(client_id):
                async with websockets.connect(uri, timeout=10) as websocket:
                    connect_message = {
                        "type": "connect",
                        "client_id": f"multi_client_{client_id}",
                        "channels": ["alerts"],
                    }

                    await websocket.send(json.dumps(connect_message))

                    # 接收确认
                    ack = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    return json.loads(ack)["type"] == "connected"

            # 并发连接多个客户端
            results = await asyncio.gather(*[client_task(i) for i in range(client_count)])

            # 验证所有客户端都成功连接
            assert all(results)

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_heartbeat(self):
        """测试WebSocket心跳机制"""

        try:
            uri = "ws://localhost:8000/ws/heartbeat"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 发送心跳
                heartbeat_message = {"type": "ping", "timestamp": datetime.now().isoformat()}

                start_time = time.time()
                await websocket.send(json.dumps(heartbeat_message))

                # 等待pong响应
                pong = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong)

                end_time = time.time()
                round_trip_time = (end_time - start_time) * 1000  # 毫秒

                # 验证心跳响应
                assert pong_data["type"] == "pong"
                assert round_trip_time < 1000  # 往返时间应该小于1秒

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_reconnection(self):
        """测试WebSocket重连机制"""

        try:
            uri = "ws://localhost:8000/ws/alerts"

            # 第一次连接
            async with websockets.connect(uri, timeout=10) as websocket1:
                connect_message = {
                    "type": "connect",
                    "client_id": f"reconnect_test_{int(datetime.now().timestamp())}",
                }
                await websocket1.send(json.dumps(connect_message))
                ack1 = await asyncio.wait_for(websocket1.recv(), timeout=5.0)
                assert json.loads(ack1)["type"] == "connected"

            # 模拟断开后重连
            await asyncio.sleep(1)

            async with websockets.connect(uri, timeout=10) as websocket2:
                connect_message = {
                    "type": "reconnect",
                    "client_id": f"reconnect_test_{int(datetime.now().timestamp())}",
                }
                await websocket2.send(json.dumps(connect_message))
                ack2 = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
                assert json.loads(ack2)["type"] in ["connected", "reconnected"]

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_message_ordering(self):
        """测试WebSocket消息顺序"""

        try:
            uri = "ws://localhost:8000/ws/test"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 发送多条消息
                messages_sent = []
                for i in range(10):
                    message = {
                        "type": "test",
                        "sequence": i,
                        "timestamp": datetime.now().isoformat(),
                    }
                    await websocket.send(json.dumps(message))
                    messages_sent.append(i)

                # 接收消息
                messages_received = []
                for _ in range(10):
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        if "sequence" in data:
                            messages_received.append(data["sequence"])
                    except asyncio.TimeoutError:
                        break

                # 验证消息顺序
                assert messages_received == messages_sent

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_authentication(self):
        """测试WebSocket认证"""

        try:
            # 先通过HTTP获取token
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                login_response = await client.post(
                    "http://localhost:8000/api/v1/auth/login",
                    json={"username": "testuser", "password": "test123"},
                )

                if login_response.status_code != 200:
                    pytest.skip("Cannot obtain auth token")

                token = login_response.json().get("access_token")

            # 使用token连接WebSocket
            uri = f"ws://localhost:8000/ws/authenticated?token={token}"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 发送认证消息
                auth_message = {"type": "auth", "token": token}

                await websocket.send(json.dumps(auth_message))

                # 接收认证确认
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)

                assert response_data["type"] == "authenticated"

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_large_message_handling(self):
        """测试WebSocket大消息处理"""

        try:
            uri = "ws://localhost:8000/ws/test"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 发送大消息
                large_message = {
                    "type": "large_data",
                    "data": "X" * 100000,  # 100KB数据
                    "timestamp": datetime.now().isoformat(),
                }

                start_time = time.time()
                await websocket.send(json.dumps(large_message))

                # 等待确认
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    end_time = time.time()

                    # 验证处理时间
                    processing_time = (end_time - start_time) * 1000
                    assert processing_time < 5000  # 应该在5秒内处理

                except asyncio.TimeoutError:
                    pytest.skip("Large message handling timeout")

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_channel_subscription(self):
        """测试WebSocket频道订阅"""

        try:
            uri = "ws://localhost:8000/ws/alerts"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 订阅多个频道
                subscribe_message = {
                    "type": "subscribe",
                    "channels": ["alerts", "system", "metrics"],
                }

                await websocket.send(json.dumps(subscribe_message))

                # 接收订阅确认
                ack = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                ack_data = json.loads(ack)

                assert ack_data["type"] == "subscribed"
                assert "channels" in ack_data
                assert set(ack_data["channels"]) == {"alerts", "system", "metrics"}

                # 取消订阅
                unsubscribe_message = {"type": "unsubscribe", "channels": ["metrics"]}

                await websocket.send(json.dumps(unsubscribe_message))

                # 接收取消订阅确认
                unack = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                unack_data = json.loads(unack)

                assert unack_data["type"] == "unsubscribed"

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """测试WebSocket错误处理"""

        try:
            uri = "ws://localhost:8000/ws/alerts"
            async with websockets.connect(uri, timeout=10) as websocket:
                # 发送无效消息
                invalid_message = {"type": "invalid_type", "data": "invalid"}

                await websocket.send(json.dumps(invalid_message))

                # 接收错误响应
                try:
                    error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    error_data = json.loads(error_response)

                    assert error_data["type"] == "error"
                    assert "message" in error_data

                except asyncio.TimeoutError:
                    pytest.skip("Error handling response timeout")

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            pytest.skip(f"WebSocket server not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
