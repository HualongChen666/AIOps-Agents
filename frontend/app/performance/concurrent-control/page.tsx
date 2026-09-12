'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '并发控制状态', path: '/api/performance/concurrent-control' },
];

export default function ConcurrentControlPage() {
  return (
    <EndpointPanel
      title="并发控制"
      intro="并发控制视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
