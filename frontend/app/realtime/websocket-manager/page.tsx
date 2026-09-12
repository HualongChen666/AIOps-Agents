'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function WebsocketManagerPage() {
  return (
    <StreamsPanel
      title="WebSocket 管理"
      streamType="websocket"
      intro="管理 WebSocket 实时流的创建与生命周期，数据来自持久化流注册表。"
    />
  );
}
