'use client'

import { useState } from 'react';

interface HealEvent {
  id: string;
  timestamp: string;
  type: 'auto' | 'manual';
  status: 'success' | 'failed' | 'pending';
  alertId: string;
  description: string;
}

interface HealTimelineProps {
  events: HealEvent[];
}

export const HealTimeline = ({ events }: HealTimelineProps) => {
  const [selectedEvent, setSelectedEvent] = useState<HealEvent | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'pending':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getTypeIcon = (type: string) => {
    return type === 'auto' ? '🤖' : '👤';
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">修复活动时间线</h3>
      
      <div className="relative">
        {/* 时间线 */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
        
        <div className="space-y-6">
          {events.map((event, index) => (
            <div key={event.id} className="relative pl-10">
              {/* 时间点 */}
              <div className={`absolute left-2 w-4 h-4 rounded-full ${getStatusColor(event.status)} border-2 border-white`} />
              
              {/* 事件卡片 */}
              <div
                className={`p-4 rounded-lg border cursor-pointer transition hover:shadow-md ${
                  selectedEvent?.id === event.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'
                }`}
                onClick={() => setSelectedEvent(event)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{getTypeIcon(event.type)}</span>
                      <span className="font-medium text-gray-900">{event.description}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>告警ID: {event.alertId}</span>
                      <span className="mx-2">•</span>
                      <span>{new Date(event.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    event.status === 'success' ? 'bg-green-100 text-green-800' :
                    event.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {event.status === 'success' ? '成功' : event.status === 'failed' ? '失败' : '进行中'}
                  </span>
                </div>
                
                {selectedEvent?.id === event.id && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-sm text-gray-600">
                      {event.type === 'auto' ? '自动修复' : '手动修复'}操作的详细信息...
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
