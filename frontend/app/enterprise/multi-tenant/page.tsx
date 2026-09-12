'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '租户列表', path: '/api/v1/enterprise/tenants' },
];

export default function MultiTenantPage() {
  return (
    <EndpointPanel
      title="多租户"
      intro="多租户视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
