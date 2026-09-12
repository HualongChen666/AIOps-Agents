'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'Qdrant 健康检查', path: '/api/vector/health' },
  { label: '向量统计', path: '/api/vector/stats' },
];

export default function QdrantPage() {
  return (
    <EndpointPanel
      title="Qdrant"
      intro="Qdrant 向量数据库健康与统计（/api/vector/health、/stats）。"
      endpoints={ENDPOINTS}
    />
  );
}
