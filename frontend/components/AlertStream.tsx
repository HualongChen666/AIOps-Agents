'use client'

import React, { useEffect, useState } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

interface AlertMessage {
  id: string;
  title: string;
  severity: 'P0' | 'P1' | 'P2' | 'P3';
  timestamp: string; // ISO
  details?: string;
}

export const AlertStream: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertMessage[]>([]);
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    `${process.env.NEXT_PUBLIC_WS_URL || ''}/ws/alerts`,
    {
      shouldReconnect: () => false,
      onOpen: () => console.log('WebSocket connected for alerts'),
      onError: (event) => {
        console.warn('WebSocket error (dev-only log)', event);
      },
    }
  );

  useEffect(() => {
    if (lastMessage?.data) {
      try {
        const msg: AlertMessage = JSON.parse(lastMessage.data);
        setAlerts((prev) => [msg, ...prev].slice(0, 30)); // keep recent 30
      } catch (e) {
        console.warn('Failed to parse alert WS message', e);
      }
    }
  }, [lastMessage]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: '连接中…',
    [ReadyState.OPEN]: '已连接',
    [ReadyState.CLOSING]: '关闭中…',
    [ReadyState.CLOSED]: '已断开',
    [ReadyState.UNINSTANTIATED]: '未实例化',
  }[readyState];

  return (
    <section className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg shadow">
      <h2 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">
        实时告警 ({connectionStatus})
      </h2>
      {alerts.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400">暂无告警</p>
      ) : (
        <ul className="space-y-2 max-h-80 overflow-y-auto">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className={`p-2 rounded-md border-l-4 ${alert.severity === 'P0'
                  ? 'border-danger bg-danger/10'
                  : alert.severity === 'P1'
                    ? 'border-warning bg-warning/10'
                    : alert.severity === 'P2'
                      ? 'border-secondary bg-secondary/10'
                      : 'border-success bg-success/10'
                }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">
                    {alert.title}
                  </p>
                  {alert.details && (
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      {alert.details}
                    </p>
                  )}
                </div>
                <time className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                  {new Date(alert.timestamp).toLocaleString()}
                </time>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
