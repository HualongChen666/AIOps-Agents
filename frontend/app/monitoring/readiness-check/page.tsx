'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ReadinessCheckResult {
  service?: string;
  status?: string;
  dependencies?: Array<{ name: string; status: string }>;
  resources?: Array<{ name: string; status: string; usage: number }>;
  last_check?: string;
  [key: string]: any;
}

interface ReadinessCheckData {
  overall_status?: string;
  total_services?: number;
  ready_services?: number;
  not_ready_services?: number;
  checks?: ReadinessCheckResult[];
  [key: string]: any;
}

export default function ReadinessCheckPage() {
  const { data: readinessData, isLoading, error, refetch } = useQuery<ReadinessCheckData>({
    queryKey: ['monitoring-readiness-check'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/readiness-check');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleServiceCheck = async (serviceName: string) => {
    try {
      await api.post('/api/v1/monitoring/readiness-check/check', {
        service_name: serviceName
      });
      refetch();
    } catch (err) {
      console.error('Failed to check service readiness:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">就绪检查</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>整体就绪状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className={`w-4 h-4 rounded-full ${
              readinessData?.overall_status === 'ready' ? 'bg-green-500' : 
              readinessData?.overall_status === 'not_ready' ? 'bg-red-500' :
              'bg-yellow-500'
            }`} />
            <span className="text-xl font-bold capitalize">
              {readinessData?.overall_status === 'ready' ? '就绪' : 
               readinessData?.overall_status === 'not_ready' ? '未就绪' :
               readinessData?.overall_status || '-'}
            </span>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总服务数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{readinessData?.total_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">就绪服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{readinessData?.ready_services || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">未就绪服务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{readinessData?.not_ready_services || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>服务就绪状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">服务名称</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">依赖</th>
                  <th className="px-4 py-2 text-left">资源</th>
                  <th className="px-4 py-2 text-left">最后检查</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {readinessData?.checks?.map((check, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{check.service}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        check.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {check.status === 'ready' ? '就绪' : '未就绪'}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {check.dependencies?.map((dep, j) => (
                          <span key={j} className={`px-2 py-1 rounded text-xs ${
                            dep.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {dep.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {check.resources?.map((res, j) => (
                          <span key={j} className={`px-2 py-1 rounded text-xs ${
                            res.status === 'ok' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {res.name} ({res.usage.toFixed(0)}%)
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      {check.last_check ? new Date(check.last_check).toLocaleString() : '-'}
                    </td>
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
