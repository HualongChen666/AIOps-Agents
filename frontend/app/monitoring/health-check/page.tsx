'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface HealthCheckResult {
  service?: string;
  status?: string;
  response_time_ms?: number;
  last_check?: string;
  error_message?: string;
  [key: string]: any;
}

interface HealthCheckData {
  overall_status?: string;
  total_services?: number;
  healthy_services?: number;
  unhealthy_services?: number;
  checks?: HealthCheckResult[];
  [key: string]: any;
}

export default function HealthCheckPage() {
  const { data: healthData, isLoading, error, refetch } = useQuery<HealthCheckData>({
    queryKey: ['monitoring-health-check'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/health-check');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleServiceCheck = async (serviceName: string) => {
    try {
      await api.post('/api/v1/monitoring/health-check/check', {
        service_name: serviceName
      });
      refetch();
    } catch (err) {
      console.error('Failed to check service:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">健康检查</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总服务数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{healthData?.total_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">健康服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{healthData?.healthy_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">异常服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{healthData?.unhealthy_services || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>服务健康状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">服务名称</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">响应时间</th>
                  <th className="px-4 py-2 text-left">最后检查</th>
                  <th className="px-4 py-2 text-left">错误信息</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {healthData?.checks?.map((check, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{check.service}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        check.status === 'healthy' ? 'bg-green-100 text-green-800' : 
                        check.status === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {check.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{check.response_time_ms?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">
                      {check.last_check ? new Date(check.last_check).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2 max-w-xs truncate">{check.error_message || '-'}</td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => check.service && handleServiceCheck(check.service)}
                      >
                        重新检查
                      </Button>
                    </td>
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
