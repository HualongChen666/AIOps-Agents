'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '模板', path: '/api/v1/documentation/templates' },
];

export default function TemplateManagementPage() {
  return (
    <EndpointPanel
      title="模板管理"
      intro="模板管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
