'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface MacOSMonitoringData {
  hostname?: string;
  os_version?: string;
  macos_version?: string;
  uptime?: number;
  cpu?: { usage_percent?: number; cores?: number; physical_cores?: number };
  memory?: { usage_percent?: number; total_gb?: number; used_gb?: number; free_gb?: number };
  disk?: { usage_percent?: number; total_gb?: number; used_gb?: number; free_gb?: number };
  battery?: { percentage?: number; is_charging?: boolean; time_remaining?: number };
  thermals?: { cpu_temp?: number; gpu_temp?: number; fan_speed?: number };
  [key: string]: any;
}

export default function MacOSMonitoringPage() {
  const { data: macosData, isLoading, error, refetch } = useQuery<MacOSMonitoringData>({
    queryKey: ['monitoring-macos-monitoring'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/macos-monitoring');
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

  const formatBatteryTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}小时 ${minutes}分钟`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">macOS监控</h1>
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
              <span className="font-medium">{macosData?.hostname || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">macOS版本:</span>
              <span className="font-medium">{macosData?.macos_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">系统版本:</span>
              <span className="font-medium">{macosData?.os_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">运行时间:</span>
              <span className="font-medium">
                {macosData?.uptime ? formatUptime(macosData.uptime) : '-'}
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
              {macosData?.cpu?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              核心: {macosData?.cpu?.cores || '-'}
            </div>
            <div className="text-sm text-gray-500">
              物理核心: {macosData?.cpu?.physical_cores || '-'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {macosData?.memory?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              已用: {macosData?.memory?.used_gb?.toFixed(2) || '-'} GB
            </div>
            <div className="text-sm text-gray-500">
              总计: {macosData?.memory?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">磁盘使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {macosData?.disk?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              已用: {macosData?.disk?.used_gb?.toFixed(2) || '-'} GB
            </div>
            <div className="text-sm text-gray-500">
              总计: {macosData?.disk?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">电池状态</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {macosData?.battery?.percentage?.toFixed(0) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              {macosData?.battery?.is_charging ? '充电中' : '使用电池'}
            </div>
            <div className="text-sm text-gray-500">
              {macosData?.battery?.time_remaining ? formatBatteryTime(macosData.battery.time_remaining) : '-'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>热管理</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">CPU温度</div>
              <div className="text-2xl font-bold">
                {macosData?.thermals?.cpu_temp?.toFixed(1) || '-'}°C
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">GPU温度</div>
              <div className="text-2xl font-bold">
                {macosData?.thermals?.gpu_temp?.toFixed(1) || '-'}°C
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">风扇转速</div>
              <div className="text-2xl font-bold">
                {macosData?.thermals?.fan_speed?.toFixed(0) || '-'} RPM
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
