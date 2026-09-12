'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '租户列表', path: '/api/v1/enterprise/tenants' },
  { label: '企业摘要', path: '/api/v1/enterprise/summary' },
];

export default function TenantEnginePage() {
  return (
    <EndpointPanel
      title="租户引擎"
      intro="租户引擎视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
