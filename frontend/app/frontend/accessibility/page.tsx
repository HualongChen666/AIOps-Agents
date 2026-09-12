'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '组件', path: '/api/v1/frontend/components' },
  { label: '主题', path: '/api/v1/frontend/themes' },
];

export default function AccessibilityPage() {
  return (
    <EndpointPanel
      title="无障碍"
      intro="无障碍视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
