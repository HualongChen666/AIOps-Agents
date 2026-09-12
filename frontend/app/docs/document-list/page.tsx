'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '文档', path: '/api/docs/documents' },
  { label: '高级文档', path: '/api/v1/documentation/documents' },
];

export default function DocumentListPage() {
  return (
    <EndpointPanel
      title="文档列表"
      intro="文档列表视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
