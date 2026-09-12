'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '用户列表', path: '/api/v1/users/' },
];

export default function UserManagementPage() {
  return (
    <EndpointPanel
      title="用户管理"
      intro="用户管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
