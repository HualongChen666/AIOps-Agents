'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function EventStreamPage() {
  return (
    <StreamsPanel
      title="事件流"
      streamType="kafka"
      intro="事件流管道（Kafka 数据源）的管理视图。"
    />
  );
}
