'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface SnapshotData {
  timestamp?: string;
  cpu?: { usage_percent?: number; cores?: number };
  memory?: { usage_percent?: number; total_gb?: number; used_gb?: number };
  network?: { recv_speed_mb?: number; sent_speed_mb?: number };
  disk?: { usage_percent?: number; total_gb?: number; used_gb?: number };
  processes?: number;
  uptime?: number;
  [key: string]: any;
}

export default function MetricsSnapshotPage() {
  const { data: snapshotData, isLoading, error, refetch } = useQuery<SnapshotData>({
    queryKey: ['monitoring-metrics-snapshot'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/metrics-snapshot');
      return resp.data;
    },
    refetchInterval: 15000,
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
        <h1 className="text-3xl font-bold text-gray-900">指标快照</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">CPU使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {snapshotData?.cpu?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              核心数: {snapshotData?.cpu?.cores || '-'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {snapshotData?.memory?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              {snapshotData?.memory?.used_gb?.toFixed(2) || '-'} / {snapshotData?.memory?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">网络流量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">
              入: {snapshotData?.network?.recv_speed_mb?.toFixed(2) || '-'} MB/s
            </div>
            <div className="text-sm">
              出: {snapshotData?.network?.sent_speed_mb?.toFixed(2) || '-'} MB/s
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">磁盘使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {snapshotData?.disk?.usage_percent?.toFixed(2) || '-'}%
            </div>
            <div className="text-sm text-gray-500">
              {snapshotData?.disk?.used_gb?.toFixed(2) || '-'} / {snapshotData?.disk?.total_gb?.toFixed(2) || '-'} GB
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">系统信息</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-500">进程数:</span>
                <span className="font-medium">{snapshotData?.processes || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">运行时间:</span>
                <span className="font-medium">
                  {snapshotData?.uptime ? formatUptime(snapshotData.uptime) : '-'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">快照时间:</span>
                <span className="font-medium">
                  {snapshotData?.timestamp ? new Date(snapshotData.timestamp).toLocaleString() : '-'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">原始数据</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs overflow-auto max-h-64 bg-gray-50 p-4 rounded">
              {JSON.stringify(snapshotData, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
