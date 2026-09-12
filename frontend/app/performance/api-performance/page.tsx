'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'API 性能概览', path: '/api/performance/api-performance' },
];

export default function ApiPerformancePage() {
  return (
    <EndpointPanel
      title="API 性能"
      intro="API 性能视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
