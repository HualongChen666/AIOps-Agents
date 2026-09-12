'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function SsePage() {
  return (
    <StreamsPanel
      title="SSE 事件流"
      streamType="sse"
      intro="Server-Sent Events 事件流管理；实时事件端点 /api/realtime/events 提供 SSE 推送。"
    />
  );
}
