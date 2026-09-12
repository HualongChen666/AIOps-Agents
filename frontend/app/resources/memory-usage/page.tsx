'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '内存分析', path: '/api/system-resources/memory' },
];

export default function MemoryUsagePage() {
  return (
    <EndpointPanel
      title="内存使用"
      intro="内存使用视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
