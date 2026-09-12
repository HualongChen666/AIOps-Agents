'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '性能调优状态', path: '/api/performance/performance-tuning' },
];

export default function PerformanceTuningPage() {
  return (
    <EndpointPanel
      title="性能调优"
      intro="性能调优视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
