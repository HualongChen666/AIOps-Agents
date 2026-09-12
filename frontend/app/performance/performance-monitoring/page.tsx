'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '性能监控', path: '/api/performance/performance-monitoring' },
];

export default function PerformanceMonitoringPage() {
  return (
    <EndpointPanel
      title="性能监控"
      intro="性能监控视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
