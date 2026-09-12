'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'API 吞吐量', path: '/api/performance/api-throughput' },
];

export default function ApiThroughputPage() {
  return (
    <EndpointPanel
      title="API 吞吐"
      intro="API 吞吐视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
