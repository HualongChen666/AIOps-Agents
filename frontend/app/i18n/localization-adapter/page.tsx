'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '本地化适配器状态', path: '/api/localization-adapter/status' },
  { label: '适配器 Locale', path: '/api/localization-adapter/locales' },
];

export default function LocalizationAdapterPage() {
  return (
    <EndpointPanel
      title="本地化适配器"
      intro="本地化适配器状态与 locode 支持（/api/localization-adapter/*）。"
      endpoints={ENDPOINTS}
    />
  );
}
