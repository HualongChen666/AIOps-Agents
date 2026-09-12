'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '配置', path: '/api/v1/tenant/configurations' },
  { label: '设置', path: '/api/v1/tenant/settings' },
];

export default function TenantConfigurationPage() {
  return (
    <EndpointPanel
      title="租户配置"
      intro="租户配置视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
