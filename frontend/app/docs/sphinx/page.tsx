'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '文档状态', path: '/api/docs/status' },
  { label: '模板', path: '/api/docs/templates' },
];

export default function SphinxPage() {
  return (
    <EndpointPanel
      title="Sphinx"
      intro="Sphinx视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
