'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '主题', path: '/api/v1/frontend/themes' },
  { label: '报告模板', path: '/api/v1/frontend/reports/templates' },
];

export default function FrontendEnhancementPage() {
  return (
    <EndpointPanel
      title="前端增强"
      intro="前端增强视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
