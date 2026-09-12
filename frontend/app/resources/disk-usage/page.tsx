'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源状态', path: '/api/system-resources/status' },
  { label: '资源摘要', path: '/api/system-resources/summary' },
];

export default function DiskUsagePage() {
  return (
    <EndpointPanel
      title="磁盘使用"
      intro="磁盘使用视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
