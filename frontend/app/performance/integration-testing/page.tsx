'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '集成测试状态', path: '/api/performance/integration-testing' },
];

export default function IntegrationTestingPage() {
  return (
    <EndpointPanel
      title="集成测试"
      intro="集成测试视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
