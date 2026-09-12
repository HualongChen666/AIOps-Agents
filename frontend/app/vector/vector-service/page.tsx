'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '向量服务健康', path: '/api/vector/health' },
  { label: '向量统计', path: '/api/vector/stats' },
];

export default function VectorServicePage() {
  return (
    <EndpointPanel
      title="向量服务"
      intro="向量服务运行状态与统计（/api/vector/health、/stats）。"
      endpoints={ENDPOINTS}
    />
  );
}
