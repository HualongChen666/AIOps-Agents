'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function StreamMonitoringPage() {
  return (
    <StreamsPanel
      title="流监控"
      streamType="sse"
      intro="监控 SSE 流的运行状态（数据来自 /api/v1/realtime/streams 的真实记录）。"
    />
  );
}
