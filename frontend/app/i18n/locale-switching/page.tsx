'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '可用 Locale', path: '/api/i18n/locales' },
  { label: 'Locale 自动检测', path: '/api/i18n/locale/detect' },
];

export default function LocaleSwitchingPage() {
  return (
    <EndpointPanel
      title="Locale 切换"
      intro="可用 locale 列表与自动检测（/api/i18n/locales、/locale/detect）。"
      endpoints={ENDPOINTS}
    />
  );
}
