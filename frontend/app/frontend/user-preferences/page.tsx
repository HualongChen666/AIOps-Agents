'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '报告模板', path: '/api/v1/frontend/reports/templates' },
  { label: '主题', path: '/api/v1/frontend/themes' },
];

export default function UserPreferencesPage() {
  return (
    <EndpointPanel
      title="用户偏好"
      intro="用户偏好视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
