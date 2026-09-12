'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '主题', path: '/api/v1/frontend/themes' },
];

export default function ThemeManagementPage() {
  return (
    <EndpointPanel
      title="主题管理"
      intro="主题管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
