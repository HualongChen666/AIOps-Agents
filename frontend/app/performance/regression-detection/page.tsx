'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '性能回归检测', path: '/api/performance/regression-detection' },
];

export default function RegressionDetectionPage() {
  return (
    <EndpointPanel
      title="回归检测"
      intro="回归检测视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
