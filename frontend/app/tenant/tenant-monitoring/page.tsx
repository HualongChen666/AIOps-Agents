'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '指标', path: '/api/v1/tenant/metrics' },
  { label: '统计', path: '/api/v1/tenant/statistics' },
  { label: '健康', path: '/api/v1/tenant/health' },
];

export default function TenantMonitoringPage() {
  return (
    <EndpointPanel
      title="租户监控"
      intro="租户监控视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
