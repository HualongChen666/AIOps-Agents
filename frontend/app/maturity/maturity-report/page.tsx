'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '成熟度报告', path: '/api/maturity/maturity-report' },
];

export default function MaturityReportPage() {
  return (
    <EndpointPanel
      title="成熟度报告"
      intro="成熟度报告视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
