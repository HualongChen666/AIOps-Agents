'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '数据分类规则', path: '/api/v1/enterprise/data/classification/rules' },
  { label: '企业摘要', path: '/api/v1/enterprise/summary' },
];

export default function DataLineagePage() {
  return (
    <EndpointPanel
      title="数据血缘"
      intro="数据血缘视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
