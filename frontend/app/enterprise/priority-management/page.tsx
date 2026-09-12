'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '优先级健康', path: '/priority/health' },
  { label: 'SLA 状态', path: '/priority/sla/status' },
];

export default function PriorityManagementPage() {
  return (
    <EndpointPanel
      title="优先级管理"
      intro="优先级管理视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
