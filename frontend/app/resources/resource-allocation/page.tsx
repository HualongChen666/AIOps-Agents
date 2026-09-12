'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源摘要', path: '/api/system-resources/summary' },
];

export default function ResourceAllocationPage() {
  return (
    <EndpointPanel
      title="资源分配"
      intro="资源分配视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
