'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '网络分析', path: '/api/system-resources/network' },
];

export default function NetworkUsagePage() {
  return (
    <EndpointPanel
      title="网络使用"
      intro="网络使用视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
