'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '租户审计日志', path: '/api/v1/tenant/audit-logs' },
];

export default function TenantAuditPage() {
  return (
    <EndpointPanel
      title="租户审计"
      intro="租户审计视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
