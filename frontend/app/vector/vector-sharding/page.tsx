'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '集合列表（分片分布）', path: '/api/vector/collections' },
  { label: '向量统计', path: '/api/vector/stats' },
];

export default function VectorShardingPage() {
  return (
    <EndpointPanel
      title="向量分片"
      intro="向量集合的分片/副本布局与整体统计（/api/vector/collections、/stats）。"
      endpoints={ENDPOINTS}
    />
  );
}
