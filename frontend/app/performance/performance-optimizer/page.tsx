'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '性能优化器', path: '/api/performance/performance-optimizer' },
];

export default function PerformanceOptimizerPage() {
  return (
    <EndpointPanel
      title="性能优化器"
      intro="性能优化器视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
