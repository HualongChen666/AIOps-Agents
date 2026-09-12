'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '组件', path: '/api/v1/frontend/components' },
  { label: '本地化', path: '/api/v1/frontend/localization' },
];

export default function FrontendIntegrationPage() {
  return (
    <EndpointPanel
      title="前端集成"
      intro="前端集成视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
