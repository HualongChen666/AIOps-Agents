'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源摘要', path: '/api/system-resources/summary' },
  { label: '资源状态', path: '/api/system-resources/status' },
];

export default function ResourceOptimizationPage() {
  return (
    <EndpointPanel
      title="资源优化"
      intro="资源优化视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
