'use client'

import { EventsPanel } from '@/components/realtime/EventsPanel';

export default function EventProcessingPage() {
  return (
    <EventsPanel
      title="事件处理"
      intro="实时事件处理视图（数据来自 /api/v1/realtime/events 的真实事件表）。"
    />
  );
}
