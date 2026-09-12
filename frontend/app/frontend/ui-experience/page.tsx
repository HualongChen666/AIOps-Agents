'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '组件', path: '/api/v1/frontend/components' },
  { label: '布局', path: '/api/v1/frontend/layouts' },
];

export default function UiExperiencePage() {
  return (
    <EndpointPanel
      title="UI 体验"
      intro="UI 体验视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
