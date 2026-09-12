'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '资源摘要', path: '/api/system-resources/summary' },
  { label: '资源状态', path: '/api/system-resources/status' },
];

export default function CapacityPlanningPage() {
  return (
    <EndpointPanel
      title="容量规划"
      intro="容量规划视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
