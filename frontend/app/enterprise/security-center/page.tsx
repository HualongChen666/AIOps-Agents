'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '密钥管理', path: '/api/v1/security/key-management/keys' },
  { label: 'MFA 方法', path: '/api/v1/security/mfa/methods' },
  { label: 'RBAC 角色', path: '/api/v1/security/rbac/roles' },
];

export default function SecurityCenterPage() {
  return (
    <EndpointPanel
      title="安全中心"
      intro="安全中心视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
