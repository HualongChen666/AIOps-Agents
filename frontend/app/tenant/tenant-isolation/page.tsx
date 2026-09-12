'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '配置', path: '/api/v1/tenant/configurations' },
  { label: '健康', path: '/api/v1/tenant/health' },
];

export default function TenantIsolationPage() {
  return (
    <EndpointPanel
      title="租户隔离"
      intro="租户隔离视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
