'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '能力评估', path: '/api/maturity/capability-assessment' },
];

export default function CapabilityAssessmentPage() {
  return (
    <EndpointPanel
      title="能力评估"
      intro="能力评估视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
