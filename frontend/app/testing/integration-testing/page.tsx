'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '测试套件', path: '/api/v1/test-automation/suites' },
  { label: '执行记录', path: '/api/v1/test-automation/executions' },
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
