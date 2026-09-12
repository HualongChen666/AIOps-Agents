'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'CPU 分析', path: '/api/system-resources/cpu' },
];

export default function CpuUsagePage() {
  return (
    <EndpointPanel
      title="CPU 使用"
      intro="CPU 使用视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
