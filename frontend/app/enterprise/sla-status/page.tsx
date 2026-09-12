'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'SLA 状态', path: '/priority/sla/status' },
];

export default function SlaStatusPage() {
  return (
    <EndpointPanel
      title="SLA 状态"
      intro="SLA 状态视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
