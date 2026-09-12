'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '框架状态', path: '/api/v1/test-framework/status' },
  { label: '配置', path: '/api/v1/test-framework/configurations' },
];

export default function TestFrameworkPage() {
  return (
    <EndpointPanel
      title="测试框架"
      intro="测试框架视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
