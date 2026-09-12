'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '用户审计日志', path: '/api/v1/users/audit-logs' },
];

export default function UserAuditPage() {
  return (
    <EndpointPanel
      title="用户审计"
      intro="用户审计视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
