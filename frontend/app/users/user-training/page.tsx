'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '通知', path: '/api/v1/users/notifications' },
  { label: '当前用户', path: '/api/v1/users/me' },
];

export default function UserTrainingPage() {
  return (
    <EndpointPanel
      title="用户培训"
      intro="用户培训视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
