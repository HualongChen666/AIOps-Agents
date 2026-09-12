'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '本地化资源状态', path: '/api/localization/status' },
  { label: '翻译资源', path: '/api/localization/translations' },
  { label: '缺失翻译', path: '/api/localization/translations/missing' },
];

export default function LocalizationResourcePage() {
  return (
    <EndpointPanel
      title="本地化资源"
      intro="本地化翻译资源与缺失项（/api/localization/*）。"
      endpoints={ENDPOINTS}
    />
  );
}
