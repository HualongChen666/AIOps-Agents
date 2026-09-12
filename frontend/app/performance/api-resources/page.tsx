'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'API 资源占用', path: '/api/performance/api-resources' },
];

export default function ApiResourcesPage() {
  return (
    <EndpointPanel
      title="API 资源"
      intro="API 资源视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
