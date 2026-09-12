'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'API 响应时间', path: '/api/performance/api-response-time' },
];

export default function ApiResponseTimePage() {
  return (
    <EndpointPanel
      title="API 响应时间"
      intro="API 响应时间视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
