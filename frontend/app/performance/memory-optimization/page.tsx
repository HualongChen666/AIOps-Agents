'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '内存优化分析', path: '/api/performance/memory-optimization' },
];

export default function MemoryOptimizationPage() {
  return (
    <EndpointPanel
      title="内存优化"
      intro="内存优化视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
