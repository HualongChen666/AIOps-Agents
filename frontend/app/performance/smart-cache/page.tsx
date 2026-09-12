'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '智能缓存状态', path: '/api/performance/smart-cache' },
];

export default function SmartCachePage() {
  return (
    <EndpointPanel
      title="智能缓存"
      intro="智能缓存视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
