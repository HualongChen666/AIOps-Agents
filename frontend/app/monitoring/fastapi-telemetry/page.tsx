'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface FastAPIMetric {
  name?: string;
  endpoint?: string;
  method?: string;
  status_code?: number;
  count?: number;
  avg_duration_ms?: number;
  p95_duration_ms?: number;
  p99_duration_ms?: number;
  error_rate?: number;
  [key: string]: any;
}

interface FastAPITelemetryData {
  app_name?: string;
  app_version?: string;
  total_requests?: number;
  total_errors?: number;
  avg_response_time?: number;
  active_connections?: number;
  metrics?: FastAPIMetric[];
  [key: string]: any;
}

export default function FastAPITelemetryPage() {
  const { data: fastapiData, isLoading, error, refetch } = useQuery<FastAPITelemetryData>({
    queryKey: ['monitoring-fastapi-telemetry'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/fastapi-telemetry');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">FastAPI遥测</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>应用信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">应用名称:</span>
              <span className="font-medium">{fastapiData?.app_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">版本:</span>
              <span className="font-medium">{fastapiData?.app_version || '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fastapiData?.total_requests?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总错误数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{fastapiData?.total_errors?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均响应时间</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fastapiData?.avg_response_time?.toFixed(2) || '-'} ms</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃连接</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fastapiData?.active_connections || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>端点指标</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">端点</th>
                  <th className="px-4 py-2 text-left">方法</th>
                  <th className="px-4 py-2 text-left">状态码</th>
                  <th className="px-4 py-2 text-left">请求数</th>
                  <th className="px-4 py-2 text-left">平均耗时</th>
                  <th className="px-4 py-2 text-left">P95耗时</th>
                  <th className="px-4 py-2 text-left">P99耗时</th>
                  <th className="px-4 py-2 text-left">错误率</th>
                </tr>
              </thead>
              <tbody>
                {fastapiData?.metrics?.map((metric, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{metric.endpoint}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        metric.method === 'GET' ? 'bg-blue-100 text-blue-800' :
                        metric.method === 'POST' ? 'bg-green-100 text-green-800' :
                        metric.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                        metric.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {metric.method}
                      </span>
                    </td>
                    <td className="px-4 py-2">{metric.status_code}</td>
                    <td className="px-4 py-2">{metric.count?.toLocaleString()}</td>
                    <td className="px-4 py-2">{metric.avg_duration_ms?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">{metric.p95_duration_ms?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">{metric.p99_duration_ms?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">{(metric.error_rate || 0).toFixed(2)}%</td>
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
