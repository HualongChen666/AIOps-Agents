'use client'

import { WebhooksPanel } from '@/components/realtime/WebhooksPanel';

export default function PushNotificationPage() {
  return (
    <WebhooksPanel
      title="推送通知"
      intro="通过 Webhook 将实时事件推送到外部系统；启用状态与目标地址来自持久化记录。"
    />
  );
}
