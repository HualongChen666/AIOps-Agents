'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LinuxMonitoringData {
  hostname?: string;
  os_version?: string;
  kernel_version?: string;
  uptime?: number;
  cpu?: { usage_percent?: number; cores?: number; load_avg?: number[] };
  memory?: { usage_percent?: number; total_gb?: number; used_gb?: number; free_gb?: number };
  disk?: { usage_percent?: number; total_gb?: number; used_gb?: number; free_gb?: number };
  network?: { interfaces?: Array<{ name: string; ip: string; rx_bytes: number; tx_bytes: number }> };
  [key: string]: any;
}

export default function LinuxMonitoringPage() {
  const { data: linuxData, isLoading, error, refetch } = useQuery<LinuxMonitoringData>({
    queryKey: ['monitoring-linux-monitoring'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/linux-monitoring');
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
        <h1 className="text-3xl font-bold text-gray-900">Linux监控</h1>
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
              <span className="font-medium">{linuxData?.hostname || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">操作系统:</span>
              <span className="font-medium">{linuxData?.os_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">内核版本:</span>
              <span className="font-medium">{linuxData?.kernel_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">运行时间:</span>
              <span className="font-medium">
                {linuxData?.uptime ? formatUptime(linuxData.uptime) : '-'}
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
              {linuxData?.cpu?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              核心数: {linuxData?.cpu?.cores || '-'}
            </div>
            <div className="text-sm text-gray-500">
              负载: {linuxData?.cpu?.load_avg?.join(', ') || '-'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {linuxData?.memory?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              已用: {linuxData?.memory?.used_gb?.toFixed(2) || '-'} GB
            </div>
            <div className="text-sm text-gray-500">
              总计: {linuxData?.memory?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">磁盘使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {linuxData?.disk?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              已用: {linuxData?.disk?.used_gb?.toFixed(2) || '-'} GB
            </div>
            <div className="text-sm text-gray-500">
              总计: {linuxData?.disk?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">网络接口</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {linuxData?.network?.interfaces?.length || '-'}
            </div>
            <div className="text-sm text-gray-500">活动接口数</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>网络接口详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">接口名称</th>
                  <th className="px-4 py-2 text-left">IP地址</th>
                  <th className="px-4 py-2 text-left">接收字节</th>
                  <th className="px-4 py-2 text-left">发送字节</th>
                </tr>
              </thead>
              <tbody>
                {linuxData?.network?.interfaces?.map((iface, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{iface.name}</td>
                    <td className="px-4 py-2">{iface.ip}</td>
                    <td className="px-4 py-2">{(iface.rx_bytes / 1024 / 1024).toFixed(2)} MB</td>
                    <td className="px-4 py-2">{(iface.tx_bytes / 1024 / 1024).toFixed(2)} MB</td>
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
