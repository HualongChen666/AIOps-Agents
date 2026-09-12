'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'SRE 成熟度', path: '/api/maturity/sre-maturity' },
];

export default function SreMaturityPage() {
  return (
    <EndpointPanel
      title="SRE 成熟度"
      intro="SRE 成熟度视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
