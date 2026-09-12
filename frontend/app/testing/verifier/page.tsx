'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '框架状态', path: '/api/v1/test-framework/status' },
  { label: '配置', path: '/api/v1/test-framework/configurations' },
];

export default function VerifierPage() {
  return (
    <EndpointPanel
      title="校验器"
      intro="校验器视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
