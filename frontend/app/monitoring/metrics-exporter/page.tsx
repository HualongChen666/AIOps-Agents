'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ExporterConfig {
  name?: string;
  type?: string;
  status?: string;
  endpoint?: string;
  port?: number;
  metrics_count?: number;
  last_scrape?: string;
  scrape_interval?: number;
  [key: string]: any;
}

interface MetricsExporterData {
  total_exporters?: number;
  active_exporters?: number;
  inactive_exporters?: number;
  total_metrics_exported?: number;
  exporters?: ExporterConfig[];
  [key: string]: any;
}

export default function MetricsExporterPage() {
  const { data: exporterData, isLoading, error, refetch } = useQuery<MetricsExporterData>({
    queryKey: ['monitoring-metrics-exporter'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/metrics-exporter');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleExporterAction = async (exporterName: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/metrics-exporter/action', {
        exporter_name: exporterName,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform exporter action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">指标导出器</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总导出器数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{exporterData?.total_exporters || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃导出器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{exporterData?.active_exporters || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">非活跃导出器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{exporterData?.inactive_exporters || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">导出指标数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{exporterData?.total_metrics_exported?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>导出器列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">名称</th>
                  <th className="px-4 py-2 text-left">类型</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">端点</th>
                  <th className="px-4 py-2 text-left">端口</th>
                  <th className="px-4 py-2 text-left">指标数</th>
                  <th className="px-4 py-2 text-left">抓取间隔</th>
                  <th className="px-4 py-2 text-left">最后抓取</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {exporterData?.exporters?.map((exporter, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{exporter.name}</td>
                    <td className="px-4 py-2">{exporter.type}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        exporter.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {exporter.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{exporter.endpoint}</td>
                    <td className="px-4 py-2">{exporter.port}</td>
                    <td className="px-4 py-2">{exporter.metrics_count}</td>
                    <td className="px-4 py-2">{exporter.scrape_interval}s</td>
                    <td className="px-4 py-2">
                      {exporter.last_scrape ? new Date(exporter.last_scrape).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          onClick={() => exporter.name && handleExporterAction(exporter.name, exporter.status === 'active' ? 'stop' : 'start')}
                        >
                          {exporter.status === 'active' ? '停止' : '启动'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => exporter.name && handleExporterAction(exporter.name, 'restart')}
                        >
                          重启
                        </Button>
                      </div>
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
