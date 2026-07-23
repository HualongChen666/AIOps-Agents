# -*- coding: utf-8 -*-
"""
Enhanced Real-time WebSocket Manager (Phase 2)
Advanced WebSocket communication with real-time data streaming and event handling
"""

import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from loguru import logger


class MessageType(Enum):
    """WebSocket message type"""

    ALERT = "alert"
    METRIC = "metric"
    LOG = "log"
    STATUS = "status"
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    UNKNOWN = "unknown"


class ConnectionState(Enum):
    """Connection state"""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""

    message_type: MessageType
    data: Dict[str, Any]
    channel: str = "default"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "message_type": self.message_type.value,
            "data": self.data,
            "channel": self.channel,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class ClientInfo:
    """WebSocket client information"""

    client_id: str
    channels: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: ConnectionState = ConnectionState.CONNECTED
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedWebSocketManager:
    """Enhanced WebSocket manager with real-time communication capabilities"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced WebSocket manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Connection management
        self.active_connections: Dict[str, Set[Any]] = defaultdict(set)  # channel -> websockets
        self.client_info: Dict[Any, ClientInfo] = {}  # websocket -> client info
        self.client_id_counter = 0

        # Message handling
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.channel_subscribers: Dict[str, Set[str]] = defaultdict(set)  # channel -> client_ids

        # Event handling
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)

        # Configuration
        self.heartbeat_interval = self.config.get("heartbeat_interval", 30)
        self.max_connections = self.config.get("max_connections", 1000)
        self.message_queue_size = self.config.get("message_queue_size", 1000)

        # Statistics
        self.connection_count = 0
        self.message_count = 0
        self.error_count = 0

        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=self.message_queue_size)

        logger.info("Enhanced WebSocket manager initialized")

    async def connect(
        self,
        websocket: Any,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Connect WebSocket client

        Args:
            websocket: WebSocket connection
            channels: List of channels to subscribe to
            metadata: Optional client metadata

        Returns:
            Client ID
        """
        # Check connection limit
        if len(self.client_info) >= self.max_connections:
            raise Exception("Maximum connections reached")

        # Generate client ID
        client_id = f"client_{self.client_id_counter}_{int(time.time())}"
        self.client_id_counter += 1

        # Accept connection
        await websocket.accept()

        # Create client info
        client_info = ClientInfo(
            client_id=client_id, channels=set(channels or ["default"]), metadata=metadata or {}
        )
        self.client_info[websocket] = client_info

        # Add to channels
        for channel in client_info.channels:
            self.active_connections[channel].add(websocket)
            self.channel_subscribers[channel].add(client_id)

        # Update statistics
        self.connection_count += 1

        logger.info(f"WebSocket client connected: {client_id}, channels: {client_info.channels}")

        # Send welcome message
        welcome_message = WebSocketMessage(
            message_type=MessageType.STATUS,
            data={"status": "connected", "client_id": client_id},
            channel="system",
        )
        await self.send_personal_message(websocket, welcome_message)

        return client_id

    async def disconnect(self, websocket: Any) -> None:
        """
        Disconnect WebSocket client

        Args:
            websocket: WebSocket connection
        """
        if websocket not in self.client_info:
            return

        client_info = self.client_info[websocket]
        client_id = client_info.client_id

        # Remove from channels
        for channel in client_info.channels:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(client_id)

        # Remove client info
        del self.client_info[websocket]

        # Update statistics
        self.connection_count -= 1

        logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, websocket: Any, message: WebSocketMessage) -> bool:
        """
        Send message to specific client

        Args:
            websocket: WebSocket connection
            message: Message to send

        Returns:
            Success status
        """
        try:
            await websocket.send_text(message.to_json())
            self.message_count += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.error_count += 1
            return False

    async def broadcast(self, message: WebSocketMessage, channel: str = "default") -> int:
        """
        Broadcast message to all subscribers in a channel

        Args:
            message: Message to broadcast
            channel: Channel name

        Returns:
            Number of clients message was sent to
        """
        if channel not in self.active_connections:
            logger.info(f"No active connections for channel: {channel}")
            return 0

        message.channel = channel
        message_json = message.to_json()
        sent_count = 0

        # Create copy of connections set to avoid modification during iteration
        connections = list(self.active_connections[channel])

        for websocket in connections:
            try:
                await websocket.send_text(message_json)
                sent_count += 1
                self.message_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}")
                self.error_count += 1
                # Remove failed connection
                await self.disconnect(websocket)

        logger.info(f"Broadcast message to {sent_count} clients in channel: {channel}")
        return sent_count

    async def broadcast_to_channels(
        self, message: WebSocketMessage, channels: List[str]
    ) -> Dict[str, int]:
        """
        Broadcast message to multiple channels

        Args:
            message: Message to broadcast
            channels: List of channel names

        Returns:
            Dictionary with channel -> sent count mapping
        """
        results = {}
        for channel in channels:
            sent_count = await self.broadcast(message, channel)
            results[channel] = sent_count

        return results

    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """
        Register message handler for specific message type

        Args:
            message_type: Message type to handle
            handler: Handler function
        """
        self.message_handlers[message_type].append(handler)
        logger.info(f"Registered handler for message type: {message_type.value}")

    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """
        Register event handler for specific event

        Args:
            event_name: Event name
            handler: Handler function
        """
        self.event_handlers[event_name].append(handler)
        logger.info(f"Registered handler for event: {event_name}")

    async def handle_message(self, websocket: Any, message_data: Dict[str, Any]) -> None:
        """
        Handle incoming message from client

        Args:
            websocket: WebSocket connection
            message_data: Message data dictionary
        """
        try:
            # Parse message
            message_type_str = message_data.get("message_type", "unknown")
            message_type_values = {m.value for m in MessageType}
            message_type = (
                MessageType(message_type_str)
                if message_type_str in message_type_values
                else MessageType.UNKNOWN
            )

            message = WebSocketMessage(
                message_type=message_type,
                data=message_data.get("data", {}),
                channel=message_data.get("channel", "default"),
                correlation_id=message_data.get("correlation_id"),
            )

            # Update client activity
            if websocket in self.client_info:
                self.client_info[websocket].last_activity = datetime.now(timezone.utc)

            # Call registered handlers
            for handler in self.message_handlers[message_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(websocket, message)
                    else:
                        handler(websocket, message)
                except Exception as e:
                    logger.error(f"Message handler failed: {e}")

        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

            # Send error response
            error_message = WebSocketMessage(
                message_type=MessageType.ERROR, data={"error": str(e)}, channel="system"
            )
            await self.send_personal_message(websocket, error_message)

    async def emit_event(self, event_name: str, event_data: Dict[str, Any]) -> None:
        """
        Emit event to registered handlers

        Args:
            event_name: Event name
            event_data: Event data
        """
        for handler in self.event_handlers[event_name]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Event handler failed for {event_name}: {e}")

    async def start_heartbeat(self) -> None:
        """Start heartbeat loop for all connections"""

        async def heartbeat_loop():
            while True:
                try:
                    heartbeat_message = WebSocketMessage(
                        message_type=MessageType.HEARTBEAT,
                        data={"timestamp": datetime.now(timezone.utc).isoformat()},
                        channel="system",
                    )

                    # Send heartbeat to all connected clients
                    for websocket in list(self.client_info.keys()):
                        await self.send_personal_message(websocket, heartbeat_message)

                    await asyncio.sleep(self.heartbeat_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat loop error: {e}")
                    await asyncio.sleep(self.heartbeat_interval)

        self.heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info("Heartbeat loop started")

    async def stop_heartbeat(self) -> None:
        """Stop heartbeat loop"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("Heartbeat loop stopped")

    async def subscribe_channel(self, websocket: Any, channel: str) -> bool:
        """
        Subscribe client to channel

        Args:
            websocket: WebSocket connection
            channel: Channel name

        Returns:
            Success status
        """
        if websocket not in self.client_info:
            return False

        client_info = self.client_info[websocket]

        if channel not in client_info.channels:
            client_info.channels.add(channel)
            self.active_connections[channel].add(websocket)
            self.channel_subscribers[channel].add(client_info.client_id)

            logger.info(f"Client {client_info.client_id} subscribed to channel: {channel}")
            return True

        return False

    async def unsubscribe_channel(self, websocket: Any, channel: str) -> bool:
        """
        Unsubscribe client from channel

        Args:
            websocket: WebSocket connection
            channel: Channel name

        Returns:
            Success status
        """
        if websocket not in self.client_info:
            return False

        client_info = self.client_info[websocket]

        if channel in client_info.channels:
            client_info.channels.remove(channel)
            self.active_connections[channel].discard(websocket)

            if client_info.client_id in self.channel_subscribers[channel]:
                self.channel_subscribers[channel].remove(client_info.client_id)

            logger.info(f"Client {client_info.client_id} unsubscribed from channel: {channel}")
            return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            "connection_count": self.connection_count,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "active_channels": len(self.active_connections),
            "channel_subscribers": {
                channel: len(subscribers)
                for channel, subscribers in self.channel_subscribers.items()
            },
            "client_info": [
                {
                    "client_id": info.client_id,
                    "channels": list(info.channels),
                    "connected_at": info.connected_at.isoformat(),
                    "last_activity": info.last_activity.isoformat(),
                    "state": info.state.value,
                }
                for info in self.client_info.values()
            ],
        }

    def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """Get information about specific channel"""
        return {
            "channel": channel,
            "active_connections": len(self.active_connections.get(channel, set())),
            "subscribers": len(self.channel_subscribers.get(channel, set())),
            "subscriber_ids": list(self.channel_subscribers.get(channel, set())),
        }


def get_enhanced_websocket_manager(
    config: Optional[Dict[str, Any]] = None,
) -> EnhancedWebSocketManager:
    """
    Factory function to get enhanced WebSocket manager instance

    Args:
        config: Optional configuration dictionary

    Returns:
        EnhancedWebSocketManager: Manager instance
    """
    return EnhancedWebSocketManager(config)
