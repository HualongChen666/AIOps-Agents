'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface WindowsMonitoringData {
  hostname?: string;
  os_version?: string;
  os_build?: string;
  uptime?: number;
  cpu?: { usage_percent?: number; cores?: number; logical_processors?: number };
  memory?: { usage_percent?: number; total_gb?: number; available_gb?: number };
  disk?: Array<{ drive: string; label: string; usage_percent: number; total_gb: number; free_gb: number }>;
  services?: Array<{ name: string; display_name: string; status: string; start_type: string }>;
  processes?: number;
  [key: string]: any;
}

export default function WindowsMonitoringPage() {
  const { data: windowsData, isLoading, error, refetch } = useQuery<WindowsMonitoringData>({
    queryKey: ['monitoring-windows-monitoring'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/windows-monitoring');
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

  const handleServiceAction = async (serviceName: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/windows-monitoring/service-action', {
        service_name: serviceName,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform service action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Windows监控</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>系统信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">主机名:</span>
              <span className="font-medium">{windowsData?.hostname || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">操作系统:</span>
              <span className="font-medium">{windowsData?.os_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">系统版本:</span>
              <span className="font-medium">{windowsData?.os_build || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">运行时间:</span>
              <span className="font-medium">
                {windowsData?.uptime ? formatUptime(windowsData.uptime) : '-'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">CPU使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {windowsData?.cpu?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              核心: {windowsData?.cpu?.cores || '-'}
            </div>
            <div className="text-sm text-gray-500">
              逻辑处理器: {windowsData?.cpu?.logical_processors || '-'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {windowsData?.memory?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              可用: {windowsData?.memory?.available_gb?.toFixed(2) || '-'} GB
            </div>
            <div className="text-sm text-gray-500">
              总计: {windowsData?.memory?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">进程数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{windowsData?.processes || '-'}</div>
            <div className="text-sm text-gray-500">运行进程</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">服务数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{windowsData?.services?.length || '-'}</div>
            <div className="text-sm text-gray-500">系统服务</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>磁盘信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">驱动器</th>
                  <th className="px-4 py-2 text-left">标签</th>
                  <th className="px-4 py-2 text-left">使用率</th>
                  <th className="px-4 py-2 text-left">总容量</th>
                  <th className="px-4 py-2 text-left">可用空间</th>
                </tr>
              </thead>
              <tbody>
                {windowsData?.disk?.map((disk, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{disk.drive}</td>
                    <td className="px-4 py-2">{disk.label}</td>
                    <td className="px-4 py-2">{disk.usage_percent.toFixed(2)}%</td>
                    <td className="px-4 py-2">{disk.total_gb.toFixed(2)} GB</td>
                    <td className="px-4 py-2">{disk.free_gb.toFixed(2)} GB</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>系统服务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">服务名称</th>
                  <th className="px-4 py-2 text-left">显示名称</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">启动类型</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {windowsData?.services?.map((service, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{service.name}</td>
                    <td className="px-4 py-2">{service.display_name}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        service.status === 'Running' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {service.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{service.start_type}</td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => handleServiceAction(service.name, service.status === 'Running' ? 'stop' : 'start')}
                      >
                        {service.status === 'Running' ? '停止' : '启动'}
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
