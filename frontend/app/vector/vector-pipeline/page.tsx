'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '向量处理管道统计', path: '/api/vector/stats' },
  { label: '集合（管道输出目标）', path: '/api/vector/collections' },
];

export default function VectorPipelinePage() {
  return (
    <EndpointPanel
      title="向量管道"
      intro="向量处理管道的统计与目标集合（/api/vector/stats、/collections）。"
      endpoints={ENDPOINTS}
    />
  );
}
