'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '模板', path: '/api/doc-generator/templates' },
  { label: '文档', path: '/api/doc-generator/documents' },
];

export default function DocGeneratorPage() {
  return (
    <EndpointPanel
      title="文档生成器"
      intro="文档生成器视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
