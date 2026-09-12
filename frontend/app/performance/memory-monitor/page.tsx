'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '内存监控数据', path: '/api/performance/memory-monitor' },
];

export default function MemoryMonitorPage() {
  return (
    <EndpointPanel
      title="内存监控"
      intro="内存监控视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
