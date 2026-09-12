'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '测试套件', path: '/api/v1/test-automation/suites' },
];

export default function TestSchedulingPage() {
  return (
    <EndpointPanel
      title="测试调度"
      intro="测试调度视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
