'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源状态', path: '/api/system-resources/status' },
  { label: '资源摘要', path: '/api/system-resources/summary' },
];

export default function SystemResourcesPage() {
  return (
    <EndpointPanel
      title="系统资源"
      intro="系统资源视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
