'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '会话列表', path: '/api/v1/users/sessions' },
];

export default function SessionManagementPage() {
  return (
    <EndpointPanel
      title="会话管理"
      intro="会话管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
