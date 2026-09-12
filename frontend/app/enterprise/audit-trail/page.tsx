'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '审计日志', path: '/api/v1/enterprise/audit-logs' },
];

export default function AuditTrailPage() {
  return (
    <EndpointPanel
      title="审计追踪"
      intro="审计追踪视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
