'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '租户列表', path: '/api/v1/tenants/' },
];

export default function TenantManagementPage() {
  return (
    <EndpointPanel
      title="租户管理"
      intro="租户管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
