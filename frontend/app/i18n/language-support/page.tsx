'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '支持的语言', path: '/api/i18n/languages' },
  { label: 'i18n 汇总', path: '/api/i18n/summary' },
];

export default function LanguageSupportPage() {
  return (
    <EndpointPanel
      title="语言支持"
      intro="子系统支持的语言与整体状态（/api/i18n/languages、/summary）。"
      endpoints={ENDPOINTS}
    />
  );
}
