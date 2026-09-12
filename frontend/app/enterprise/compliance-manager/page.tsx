'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '合规标准', path: '/api/v1/enterprise/compliance/standards' },
  { label: '合规策略', path: '/api/v1/security/compliance-management/policies' },
];

export default function ComplianceManagerPage() {
  return (
    <EndpointPanel
      title="合规管理"
      intro="合规管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
