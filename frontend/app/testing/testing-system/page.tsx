'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '框架状态', path: '/api/v1/test-framework/status' },
  { label: '覆盖率汇总', path: '/api/v1/test-coverage/summary' },
];

export default function TestingSystemPage() {
  return (
    <EndpointPanel
      title="测试系统"
      intro="测试系统视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
