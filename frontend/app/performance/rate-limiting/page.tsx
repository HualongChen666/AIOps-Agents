'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '速率限制配置与状态', path: '/api/performance/rate-limiting' },
];

export default function RateLimitingPage() {
  return (
    <EndpointPanel
      title="速率限制"
      intro="速率限制视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
