'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '配额', path: '/api/v1/tenant/quotas' },
  { label: '限制', path: '/api/v1/tenant/limits' },
];

export default function TenantQuotaPage() {
  return (
    <EndpointPanel
      title="租户配额"
      intro="租户配额视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
