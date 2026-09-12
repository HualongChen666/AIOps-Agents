'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '数字格式化（1234.56）', path: '/api/i18n/format/number', params: { number: 1234.56, decimals: 2 } },
  { label: '数字格式化（0.5）', path: '/api/i18n/format/number', params: { number: 0.5, decimals: 3 } },
];

export default function FormattingPage() {
  return (
    <EndpointPanel
      title="格式化"
      intro="数字等本地化格式化（/api/i18n/format/number）。"
      endpoints={ENDPOINTS}
    />
  );
}
