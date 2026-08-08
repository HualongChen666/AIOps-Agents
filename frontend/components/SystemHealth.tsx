'use client'

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down';
  services: {
    name: string;
    status: 'up' | 'down';
    latency?: number;
  }[];
  last_updated: string;
}

export const SystemHealth: React.FC = () => {
  const { data, isLoading, error } = useQuery<HealthStatus>({
    queryKey: ['system-health'],
    queryFn: async () => {
      const resp = await api.get<HealthStatus>('/api/v1/health/detailed');
      return resp.data;
    },
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <section className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          系统健康状态
        </h2>
        <div className="text-center text-gray-500">加载中…</div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          系统健康状态
        </h2>
        <div className="text-center text-red-500">无法获取健康状态</div>
      </section>
    );
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'healthy':
      case 'up':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20';
      case 'down':
        return 'text-red-600 bg-red-50 dark:bg-red-900/20';
      default:
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  return (
    <section className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          系统健康状态
        </h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(data.status)}`}>
          {data.status ? data.status.toUpperCase() : 'UNKNOWN'}
        </span>
      </div>

      <div className="space-y-3">
        {(data.services || []).map((service) => (
          <div
            key={service.name}
            className="flex justify-between items-center p-3 rounded-md bg-gray-50 dark:bg-gray-700"
          >
            <div className="flex items-center gap-3">
              <div
                className={`w-3 h-3 rounded-full ${service.status === 'up' ? 'bg-green-500' : 'bg-red-500'
                  }`}
              />
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {service.name}
              </span>
            </div>
            <div className="flex items-center gap-4">
              {service.latency !== undefined && (
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {service.latency}ms
                </span>
              )}
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(service.status)}`}
              >
                {service.status.toUpperCase()}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
        最后更新: {new Date(data.last_updated).toLocaleString()}
      </div>
    </section>
  );
};
