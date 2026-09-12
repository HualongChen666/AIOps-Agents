'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '执行记录', path: '/api/v1/test-automation/executions' },
];

export default function AutomatedTestsPage() {
  return (
    <EndpointPanel
      title="自动化测试"
      intro="自动化测试视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
