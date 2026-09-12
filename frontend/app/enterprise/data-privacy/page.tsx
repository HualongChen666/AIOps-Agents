'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '隐私主体', path: '/api/v1/security/data-privacy/subjects' },
  { label: '数据分类规则', path: '/api/v1/enterprise/data/classification/rules' },
];

export default function DataPrivacyPage() {
  return (
    <EndpointPanel
      title="数据隐私"
      intro="数据隐私视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
