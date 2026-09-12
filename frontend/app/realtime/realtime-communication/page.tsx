'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function RealtimeCommunicationPage() {
  return (
    <StreamsPanel
      title="实时通信"
      intro="所有实时流的统一管理入口（SSE / WebSocket / Kafka）。"
    />
  );
}
