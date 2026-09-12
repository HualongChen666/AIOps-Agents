'use client'

import { StreamsPanel } from '@/components/realtime/StreamsPanel';

export default function KafkaStreamPage() {
  return (
    <StreamsPanel
      title="Kafka 流处理"
      streamType="kafka"
      intro="Kafka 数据源实时流的管理视图。"
    />
  );
}
