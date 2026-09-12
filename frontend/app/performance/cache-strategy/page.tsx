'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '缓存策略状态', path: '/api/performance/cache-strategy' },
];

export default function CacheStrategyPage() {
  return (
    <EndpointPanel
      title="缓存策略"
      intro="缓存策略视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
