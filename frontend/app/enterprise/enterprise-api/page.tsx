'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '企业摘要', path: '/api/v1/enterprise/summary' },
];

export default function EnterpriseApiPage() {
  return (
    <EndpointPanel
      title="企业 API"
      intro="企业 API视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
