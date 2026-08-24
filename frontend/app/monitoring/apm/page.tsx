'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ServiceInfo {
  name?: string;
  status?: string;
  response_time_avg?: number;
  error_rate?: number;
  throughput?: number;
  cpu_usage?: number;
  memory_usage?: number;
  [key: string]: any;
}

interface APMData {
  total_services?: number;
  healthy_services?: number;
  degraded_services?: number;
  down_services?: number;
  avg_response_time?: number;
  total_error_rate?: number;
  services?: ServiceInfo[];
  time_range?: string;
  [key: string]: any;
}

export default function APMPage() {
  const [timeRange, setTimeRange] = useState('1h');

  const { data: apmData, isLoading, error, refetch } = useQuery<APMData>({
    queryKey: ['monitoring-apm', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/apm', {
        params: { time_range: timeRange }
      });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">应用性能监控</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总服务数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apmData?.total_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">健康服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{apmData?.healthy_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">降级服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{apmData?.degraded_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">故障服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{apmData?.down_services || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均响应时间</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apmData?.avg_response_time?.toFixed(2) || '-'} ms</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总错误率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(apmData?.total_error_rate || 0).toFixed(2)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>服务列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">服务名称</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">平均响应时间</th>
                  <th className="px-4 py-2 text-left">错误率</th>
                  <th className="px-4 py-2 text-left">吞吐量</th>
                  <th className="px-4 py-2 text-left">CPU使用率</th>
                  <th className="px-4 py-2 text-left">内存使用率</th>
                </tr>
              </thead>
              <tbody>
                {apmData?.services?.map((service, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{service.name}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        service.status === 'healthy' ? 'bg-green-100 text-green-800' : 
                        service.status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {service.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{service.response_time_avg?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">{(service.error_rate || 0).toFixed(2)}%</td>
                    <td className="px-4 py-2">{service.throughput?.toFixed(2)} req/s</td>
                    <td className="px-4 py-2">{service.cpu_usage?.toFixed(2)}%</td>
                    <td className="px-4 py-2">{service.memory_usage?.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
