'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function EnhancedWebsocketPage() {
  return (
    <StreamsPanel
      title="增强 WebSocket"
      streamType="websocket"
      intro="增强型 WebSocket 通道：基于持久化流配置进行管理。"
    />
  );
}
