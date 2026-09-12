'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '性能数据', path: '/api/performance/performance-data' },
];

export default function PerformanceDataPage() {
  return (
    <EndpointPanel
      title="性能数据"
      intro="性能数据视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
