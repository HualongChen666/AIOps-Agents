'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '覆盖率汇总', path: '/api/v1/test-coverage/summary' },
  { label: '报告', path: '/api/v1/test-coverage/reports' },
];

export default function TestCoveragePage() {
  return (
    <EndpointPanel
      title="测试覆盖率"
      intro="测试覆盖率视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
