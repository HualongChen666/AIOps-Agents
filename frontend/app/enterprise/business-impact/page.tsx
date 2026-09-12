'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '影响评分', path: '/api/v1/business-impact/impact-scores' },
  { label: '业务指标', path: '/api/v1/business-impact/metrics' },
];

export default function BusinessImpactPage() {
  return (
    <EndpointPanel
      title="业务影响"
      intro="业务影响视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
