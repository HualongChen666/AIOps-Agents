'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '查询优化分析', path: '/api/performance/query-optimization' },
];

export default function QueryOptimizationPage() {
  return (
    <EndpointPanel
      title="查询优化"
      intro="查询优化视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
