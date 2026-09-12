'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '文档', path: '/api/v1/documentation/documents' },
  { label: '模板', path: '/api/v1/documentation/templates' },
];

export default function DocumentationManagementPage() {
  return (
    <EndpointPanel
      title="文档管理"
      intro="文档管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
