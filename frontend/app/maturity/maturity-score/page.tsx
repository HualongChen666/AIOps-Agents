'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '成熟度评分', path: '/api/maturity/maturity-score' },
];

export default function MaturityScorePage() {
  return (
    <EndpointPanel
      title="成熟度评分"
      intro="成熟度评分视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
