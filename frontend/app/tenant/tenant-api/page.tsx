'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '租户列表', path: '/api/v1/tenants/' },
  { label: '租户健康', path: '/api/v1/tenant/health' },
];

export default function TenantApiPage() {
  return (
    <EndpointPanel
      title="租户 API"
      intro="租户 API视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
