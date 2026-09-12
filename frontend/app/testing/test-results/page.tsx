'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '执行记录', path: '/api/v1/test-automation/executions' },
];

export default function TestResultsPage() {
  return (
    <EndpointPanel
      title="测试结果"
      intro="测试结果视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
