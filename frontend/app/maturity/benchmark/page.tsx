'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '基准', path: '/api/maturity/benchmark' },
];

export default function BenchmarkPage() {
  return (
    <EndpointPanel
      title="成熟度基准"
      intro="成熟度基准视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
