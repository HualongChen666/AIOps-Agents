'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'CPU 优化分析', path: '/api/performance/cpu-optimization' },
];

export default function CpuOptimizationPage() {
  return (
    <EndpointPanel
      title="CPU 优化"
      intro="CPU 优化视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
