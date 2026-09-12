'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '命名空间翻译', path: '/api/i18n/translations/namespace' },
  { label: '本地化翻译资源', path: '/api/localization/translations' },
];

export default function ResourceManagementPage() {
  return (
    <EndpointPanel
      title="资源管理"
      intro="翻译资源命名空间与本地化资源清单（/api/i18n/translations/namespace、/api/localization/translations）。"
      endpoints={ENDPOINTS}
    />
  );
}
