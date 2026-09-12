'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '计费信息', path: '/api/v1/tenant/billing' },
];

export default function TenantBillingPage() {
  return (
    <EndpointPanel
      title="租户计费"
      intro="租户计费视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
