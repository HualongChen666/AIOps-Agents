'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'RBAC 角色', path: '/api/v1/security/rbac/roles' },
  { label: 'ABAC 策略', path: '/api/v1/security/abac/policies' },
];

export default function UserAuthorizationPage() {
  return (
    <EndpointPanel
      title="用户授权"
      intro="用户授权视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
