'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '货币格式化（100, zh-CN）', path: '/api/i18n/format/currency', params: { amount: 100, locale: 'zh-CN' } },
  { label: '货币格式化（100, en-US）', path: '/api/i18n/format/currency', params: { amount: 100, locale: 'en-US' } },
];

export default function CurrencyFormatPage() {
  return (
    <EndpointPanel
      title="货币格式化"
      intro="按 locale 的真实货币格式化结果（/api/i18n/format/currency）。"
      endpoints={ENDPOINTS}
    />
  );
}
