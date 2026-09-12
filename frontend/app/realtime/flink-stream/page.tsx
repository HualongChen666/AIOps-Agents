'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function FlinkStreamPage() {
  return (
    <StreamsPanel
      title="Flink 流处理"
      streamType="kafka"
      intro="Flink 处理的实时流（Kafka 数据源）管理视图。"
    />
  );
}
