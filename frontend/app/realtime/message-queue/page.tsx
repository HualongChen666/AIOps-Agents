'use client'

import { SubscriptionsPanel } from '@/components/realtime/SubscriptionsPanel';

export default function MessageQueuePage() {
  return (
    <SubscriptionsPanel
      title="消息队列"
      intro="以订阅（subscription）为消息投递单元：管理订阅者与目标流的绑定关系。"
    />
  );
}
