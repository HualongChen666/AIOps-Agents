'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '当前用户', path: '/api/v1/users/me' },
];

export default function PasswordManagementPage() {
  return (
    <EndpointPanel
      title="密码管理"
      intro="密码管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
