'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '性能报告', path: '/api/performance/performance-report' },
];

export default function PerformanceReportPage() {
  return (
    <EndpointPanel
      title="性能报告"
      intro="性能报告视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
