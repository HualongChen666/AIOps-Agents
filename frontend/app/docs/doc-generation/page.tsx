'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '生成器状态', path: '/api/doc-generator/status' },
  { label: '模板', path: '/api/doc-generator/templates' },
];

export default function DocGenerationPage() {
  return (
    <EndpointPanel
      title="文档生成"
      intro="文档生成视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
