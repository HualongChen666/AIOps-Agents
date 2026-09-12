'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '企业特性', path: '/api/enterprise/enterprise-features' },
];

export default function EnterpriseFeaturesPage() {
  return (
    <EndpointPanel
      title="企业特性"
      intro="企业特性视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
