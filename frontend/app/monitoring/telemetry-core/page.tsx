'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface TelemetrySource {
  name?: string;
  type?: string;
  status?: string;
  data_points?: number;
  last_received?: string;
  [key: string]: any;
}

interface TelemetryCoreData {
  core_version?: string;
  total_sources?: number;
  active_sources?: number;
  total_data_points?: number;
  data_rate?: number;
  sources?: TelemetrySource[];
  [key: string]: any;
}

export default function TelemetryCorePage() {
  const { data: telemetryData, isLoading, error, refetch } = useQuery<TelemetryCoreData>({
    queryKey: ['monitoring-telemetry-core'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/telemetry-core');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleSourceAction = async (sourceName: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/telemetry-core/source-action', {
        source_name: sourceName,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform source action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">遥测核心</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>核心信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between">
            <span className="text-gray-500">版本:</span>
            <span className="font-medium">{telemetryData?.core_version || '-'}</span>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总数据源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{telemetryData?.total_sources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃数据源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{telemetryData?.active_sources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总数据点</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{telemetryData?.total_data_points?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">数据速率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{telemetryData?.data_rate?.toFixed(2) || '-'} points/s</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>数据源列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">名称</th>
                  <th className="px-4 py-2 text-left">类型</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">数据点数</th>
                  <th className="px-4 py-2 text-left">最后接收</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {telemetryData?.sources?.map((source, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{source.name}</td>
                    <td className="px-4 py-2">{source.type}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        source.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {source.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{source.data_points?.toLocaleString()}</td>
                    <td className="px-4 py-2">
                      {source.last_received ? new Date(source.last_received).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => source.name && handleSourceAction(source.name, source.status === 'active' ? 'stop' : 'start')}
                      >
                        {source.status === 'active' ? '停止' : '启动'}
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
