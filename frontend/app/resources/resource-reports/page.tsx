'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源摘要', path: '/api/system-resources/summary' },
  { label: '资源状态', path: '/api/system-resources/status' },
];

export default function ResourceReportsPage() {
  return (
    <EndpointPanel
      title="资源报表"
      intro="资源报表视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
