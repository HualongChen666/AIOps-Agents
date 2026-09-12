'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function WebsocketConnectionPage() {
  return (
    <StreamsPanel
      title="WebSocket 连接"
      streamType="websocket"
      intro="查看与维护 WebSocket 连接对应的实时流记录。"
    />
  );
}
