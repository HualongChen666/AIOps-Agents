'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '改进计划', path: '/api/maturity/improvement-plan' },
];

export default function ImprovementPlanPage() {
  return (
    <EndpointPanel
      title="改进计划"
      intro="改进计划视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
