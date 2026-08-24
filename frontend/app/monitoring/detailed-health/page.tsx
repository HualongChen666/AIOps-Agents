'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface HealthMetric {
  name?: string;
  value?: number;
  unit?: string;
  status?: string;
  threshold?: number;
  [key: string]: any;
}

interface DetailedHealthData {
  service_name?: string;
  overall_status?: string;
  uptime?: number;
  version?: string;
  environment?: string;
  metrics?: HealthMetric[];
  last_updated?: string;
  [key: string]: any;
}

export default function DetailedHealthPage() {
  const [selectedService, setSelectedService] = useState('all');

  const { data: healthData, isLoading, error, refetch } = useQuery<DetailedHealthData>({
    queryKey: ['monitoring-detailed-health', selectedService],
    queryFn: async () => {
      const params = selectedService !== 'all' ? { service_name: selectedService } : {};
      const resp = await api.get('/api/v1/monitoring/detailed-health', { params });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}天 ${hours}小时 ${minutes}分钟`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">详细健康信息</h1>
        <div className="flex gap-2">
          <Select value={selectedService} onChange={(e) => setSelectedService(e.target.value)}>
            <option value="all">所有服务</option>
            <option value="api">API服务</option>
            <option value="worker">Worker服务</option>
            <option value="database">数据库</option>
            <option value="cache">缓存</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>服务信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">服务名称:</span>
              <span className="font-medium">{healthData?.service_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">版本:</span>
              <span className="font-medium">{healthData?.version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">环境:</span>
              <span className="font-medium">{healthData?.environment || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">运行时间:</span>
              <span className="font-medium">
                {healthData?.uptime ? formatUptime(healthData.uptime) : '-'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>整体状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className={`w-4 h-4 rounded-full ${
              healthData?.overall_status === 'healthy' ? 'bg-green-500' : 
              healthData?.overall_status === 'degraded' ? 'bg-yellow-500' :
              'bg-red-500'
            }`} />
            <span className="text-xl font-bold capitalize">{healthData?.overall_status || '-'}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>健康指标</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">指标名称</th>
                  <th className="px-4 py-2 text-left">当前值</th>
                  <th className="px-4 py-2 text-left">单位</th>
                  <th className="px-4 py-2 text-left">阈值</th>
                  <th className="px-4 py-2 text-left">状态</th>
                </tr>
              </thead>
              <tbody>
                {healthData?.metrics?.map((metric, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{metric.name}</td>
                    <td className="px-4 py-2">{metric.value?.toFixed(2)}</td>
                    <td className="px-4 py-2">{metric.unit}</td>
                    <td className="px-4 py-2">{metric.threshold?.toFixed(2)}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        metric.status === 'healthy' ? 'bg-green-100 text-green-800' : 
                        metric.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {metric.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>最后更新</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-500">
            {healthData?.last_updated ? new Date(healthData.last_updated).toLocaleString() : '-'}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
