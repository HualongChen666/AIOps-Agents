'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '当前用户', path: '/api/v1/users/me' },
  { label: 'MFA 状态', path: '/api/v1/users/me/mfa/status' },
];

export default function UserAuthenticationPage() {
  return (
    <EndpointPanel
      title="用户认证"
      intro="用户认证视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
