'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '缓存预热状态', path: '/api/performance/cache-preheat' },
];

export default function CachePreheatPage() {
  return (
    <EndpointPanel
      title="缓存预热"
      intro="缓存预热视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
