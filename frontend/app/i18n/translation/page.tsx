'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '翻译 welcome_message', path: '/api/i18n/translate', params: { key: 'welcome_message', namespace: 'common' } },
  { label: '翻译 dashboard_title', path: '/api/i18n/translate', params: { key: 'dashboard_title', namespace: 'common' } },
];

export default function TranslationPage() {
  return (
    <EndpointPanel
      title="翻译"
      intro="按 key/namespace/language 的真实翻译查询（/api/i18n/translate）。"
      endpoints={ENDPOINTS}
    />
  );
}
