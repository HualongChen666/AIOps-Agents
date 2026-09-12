'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'i18n 汇总', path: '/api/i18n/summary' },
  { label: 'i18n 状态', path: '/api/i18n/status' },
  { label: 'i18n 配置', path: '/api/i18n/i18n-configuration' },
];

export default function I18nManagementPage() {
  return (
    <EndpointPanel
      title="i18n 管理"
      intro="国际化的汇总、运行状态与配置（/api/i18n/summary、/status、/i18n-configuration）。"
      endpoints={ENDPOINTS}
    />
  );
}
