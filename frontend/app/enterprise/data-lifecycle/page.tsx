'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '数据分类规则', path: '/api/v1/enterprise/data/classification/rules' },
];

export default function DataLifecyclePage() {
  return (
    <EndpointPanel
      title="数据生命周期"
      intro="数据生命周期视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
