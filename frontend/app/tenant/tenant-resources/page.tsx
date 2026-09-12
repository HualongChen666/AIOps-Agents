'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '用量', path: '/api/v1/tenant/usage' },
  { label: '限制', path: '/api/v1/tenant/limits' },
];

export default function TenantResourcesPage() {
  return (
    <EndpointPanel
      title="租户资源"
      intro="租户资源视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
