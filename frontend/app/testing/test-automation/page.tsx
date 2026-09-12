'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '测试套件', path: '/api/v1/test-automation/suites' },
  { label: '执行记录', path: '/api/v1/test-automation/executions' },
];

export default function TestAutomationPage() {
  return (
    <EndpointPanel
      title="测试自动化"
      intro="测试自动化视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
