'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'MFA 状态', path: '/api/v1/users/me/mfa/status' },
];

export default function MfaPage() {
  return (
    <EndpointPanel
      title="多因素认证"
      intro="多因素认证视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
