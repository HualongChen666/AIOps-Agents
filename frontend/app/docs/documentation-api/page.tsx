'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '文档状态', path: '/api/docs/status' },
  { label: '文档列表', path: '/api/docs/documents' },
];

export default function DocumentationApiPage() {
  return (
    <EndpointPanel
      title="文档 API"
      intro="文档 API视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
