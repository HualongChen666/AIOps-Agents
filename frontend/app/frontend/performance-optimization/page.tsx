'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '组件', path: '/api/v1/frontend/components' },
  { label: '主题', path: '/api/v1/frontend/themes' },
];

export default function PerformanceOptimizationPage() {
  return (
    <EndpointPanel
      title="性能优化"
      intro="性能优化视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
