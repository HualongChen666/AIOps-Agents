'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '合规标准', path: '/api/v1/enterprise/compliance/standards' },
];

export default function CompliancePage() {
  return (
    <EndpointPanel
      title="合规"
      intro="合规视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
