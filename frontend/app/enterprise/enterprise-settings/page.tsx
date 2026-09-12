'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: '企业设置', path: '/api/enterprise/enterprise-settings' },
  { label: '运行时设置', path: '/api/v1/enterprise/settings' },
];

export default function EnterpriseSettingsPage() {
  return (
    <EndpointPanel
      title="企业设置"
      intro="企业设置视图（数据来自真实后端端点）。"
      endpoints={ENDPOINTS}
    />
  );
}
