'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '档案', path: '/api/v1/users/profile' },
  { label: '当前用户', path: '/api/v1/users/me' },
];

export default function UserProfilePage() {
  return (
    <EndpointPanel
      title="用户档案"
      intro="用户档案视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
