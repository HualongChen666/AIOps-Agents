'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '成员', path: '/api/v1/tenant/members' },
];

export default function TenantPermissionsPage() {
  return (
    <EndpointPanel
      title="租户权限"
      intro="租户权限视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
