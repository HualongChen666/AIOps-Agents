'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function BidirectionalCommunicationPage() {
  return (
    <StreamsPanel
      title="双向通信"
      streamType="websocket"
      intro="双向实时通信链路（WebSocket 流）的管理视图。"
    />
  );
}
