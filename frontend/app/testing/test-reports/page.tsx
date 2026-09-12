'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '覆盖率报告', path: '/api/v1/test-coverage/reports' },
];

export default function TestReportsPage() {
  return (
    <EndpointPanel
      title="测试报告"
      intro="测试报告视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
