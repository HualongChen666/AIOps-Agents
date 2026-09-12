'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '日期格式化（zh-CN）', path: '/api/i18n/format/date', params: { date_str: '2026-09-12', locale: 'zh-CN' } },
  { label: '日期格式化（en-US）', path: '/api/i18n/format/date', params: { date_str: '2026-09-12', locale: 'en-US' } },
];

export default function DateFormatPage() {
  return (
    <EndpointPanel
      title="日期格式化"
      intro="按 locale 的真实日期格式化结果（/api/i18n/format/date）。"
      endpoints={ENDPOINTS}
    />
  );
}
