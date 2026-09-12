'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源状态', path: '/api/system-resources/status' },
  { label: 'CPU', path: '/api/system-resources/cpu' },
  { label: '内存', path: '/api/system-resources/memory' },
  { label: '网络', path: '/api/system-resources/network' },
];

export default function ResourceMonitoringPage() {
  return (
    <EndpointPanel
      title="资源监控"
      intro="资源监控视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
