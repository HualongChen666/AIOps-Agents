'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'RBAC 角色', path: '/api/v1/security/rbac/roles' },
  { label: 'ABAC 策略', path: '/api/v1/security/abac/policies' },
];

export default function UserPermissionsPage() {
  return (
    <EndpointPanel
      title="用户权限"
      intro="用户权限视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
