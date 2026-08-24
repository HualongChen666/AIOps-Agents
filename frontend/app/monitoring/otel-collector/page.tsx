'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface OTELReceiver {
  name?: string;
  type?: string;
  status?: string;
  endpoint?: string;
  received_spans?: number;
  received_metrics?: number;
  received_logs?: number;
  [key: string]: any;
}

interface OTELProcessor {
  name?: string;
  type?: string;
  status?: string;
  processed_count?: number;
  error_count?: number;
  [key: string]: any;
}

interface OTELExporter {
  name?: string;
  type?: string;
  status?: string;
  endpoint?: string;
  exported_spans?: number;
  exported_metrics?: number;
  exported_logs?: number;
  [key: string]: any;
}

interface OTELCollectorData {
  collector_version?: string;
  total_receivers?: number;
  active_receivers?: number;
  total_processors?: number;
  active_processors?: number;
  total_exporters?: number;
  active_exporters?: number;
  receivers?: OTELReceiver[];
  processors?: OTELProcessor[];
  exporters?: OTELExporter[];
  [key: string]: any;
}

export default function OTELCollectorPage() {
  const [viewType, setViewType] = useState('receivers');

  const { data: otelData, isLoading, error, refetch } = useQuery<OTELCollectorData>({
    queryKey: ['monitoring-otel-collector'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/otel-collector');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleComponentAction = async (componentName: string, componentType: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/otel-collector/component-action', {
        component_name: componentName,
        component_type: componentType,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform component action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">OpenTelemetry采集</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Collector信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between">
            <span className="text-gray-500">版本:</span>
            <span className="font-medium">{otelData?.collector_version || '-'}</span>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">接收器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{otelData?.total_receivers || '-'}</div>
            <div className="text-sm text-gray-500">活跃: {otelData?.active_receivers || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">处理器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{otelData?.total_processors || '-'}</div>
            <div className="text-sm text-gray-500">活跃: {otelData?.active_processors || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">导出器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{otelData?.total_exporters || '-'}</div>
            <div className="text-sm text-gray-500">活跃: {otelData?.active_exporters || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>视图切换</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button
              variant={viewType === 'receivers' ? 'default' : 'outline'}
              onClick={() => setViewType('receivers')}
            >
              接收器
            </Button>
            <Button
              variant={viewType === 'processors' ? 'default' : 'outline'}
              onClick={() => setViewType('processors')}
            >
              处理器
            </Button>
            <Button
              variant={viewType === 'exporters' ? 'default' : 'outline'}
              onClick={() => setViewType('exporters')}
            >
              导出器
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {viewType === 'receivers' ? '接收器列表' : 
             viewType === 'processors' ? '处理器列表' : '导出器列表'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            {viewType === 'receivers' ? (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">名称</th>
                    <th className="px-4 py-2 text-left">类型</th>
                    <th className="px-4 py-2 text-left">状态</th>
                    <th className="px-4 py-2 text-left">端点</th>
                    <th className="px-4 py-2 text-left">接收Span</th>
                    <th className="px-4 py-2 text-left">接收指标</th>
                    <th className="px-4 py-2 text-left">接收日志</th>
                    <th className="px-4 py-2 text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {otelData?.receivers?.map((receiver, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">{receiver.name}</td>
                      <td className="px-4 py-2">{receiver.type}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          receiver.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {receiver.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{receiver.endpoint}</td>
                      <td className="px-4 py-2">{receiver.received_spans?.toLocaleString()}</td>
                      <td className="px-4 py-2">{receiver.received_metrics?.toLocaleString()}</td>
                      <td className="px-4 py-2">{receiver.received_logs?.toLocaleString()}</td>
                      <td className="px-4 py-2">
                        <Button
                          size="sm"
                          onClick={() => receiver.name && handleComponentAction(receiver.name, 'receiver', receiver.status === 'active' ? 'stop' : 'start')}
                        >
                          {receiver.status === 'active' ? '停止' : '启动'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : viewType === 'processors' ? (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">名称</th>
                    <th className="px-4 py-2 text-left">类型</th>
                    <th className="px-4 py-2 text-left">状态</th>
                    <th className="px-4 py-2 text-left">处理数量</th>
                    <th className="px-4 py-2 text-left">错误数量</th>
                    <th className="px-4 py-2 text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {otelData?.processors?.map((processor, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">{processor.name}</td>
                      <td className="px-4 py-2">{processor.type}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          processor.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {processor.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{processor.processed_count?.toLocaleString()}</td>
                      <td className="px-4 py-2">{processor.error_count?.toLocaleString()}</td>
                      <td className="px-4 py-2">
                        <Button
                          size="sm"
                          onClick={() => processor.name && handleComponentAction(processor.name, 'processor', processor.status === 'active' ? 'stop' : 'start')}
                        >
                          {processor.status === 'active' ? '停止' : '启动'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">名称</th>
                    <th className="px-4 py-2 text-left">类型</th>
                    <th className="px-4 py-2 text-left">状态</th>
                    <th className="px-4 py-2 text-left">端点</th>
                    <th className="px-4 py-2 text-left">导出Span</th>
                    <th className="px-4 py-2 text-left">导出指标</th>
                    <th className="px-4 py-2 text-left">导出日志</th>
                    <th className="px-4 py-2 text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {otelData?.exporters?.map((exporter, i) => (
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
                      <td className="px-4 py-2">{exporter.exported_spans?.toLocaleString()}</td>
                      <td className="px-4 py-2">{exporter.exported_metrics?.toLocaleString()}</td>
                      <td className="px-4 py-2">{exporter.exported_logs?.toLocaleString()}</td>
                      <td className="px-4 py-2">
                        <Button
                          size="sm"
                          onClick={() => exporter.name && handleComponentAction(exporter.name, 'exporter', exporter.status === 'active' ? 'stop' : 'start')}
                        >
                          {exporter.status === 'active' ? '停止' : '启动'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
