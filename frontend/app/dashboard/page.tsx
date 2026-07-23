'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DashboardCards } from '@/components/DashboardCards';
import { AlertStream } from '@/components/AlertStream';
import { ResourceTrendChart } from '@/components/charts/ResourceTrendChart';
import { HealTimeline } from '@/components/charts/HealTimeline';
import { useDashboardStore } from '@/store/dashboard';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ResourceData {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
}

interface HealEvent {
  id: string;
  timestamp: string;
  type: 'auto' | 'manual';
  status: 'success' | 'failed' | 'pending';
  alertId: string;
  description: string;
}

export default function DashboardPage() {
  const { stats, setStats } = useDashboardStore();
  const [resourceData, setResourceData] = useState<ResourceData[]>([]);
  const [healEvents, setHealEvents] = useState<HealEvent[]>([]);

  // 🔧 修复: 使用真实 API 获取仪表盘摘要数据
  const { data: summaryData, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/summary');
      return resp.data;
    },
    refetchInterval: 30000, // 30秒刷新
  });

  useEffect(() => {
    if (summaryData) {
      setStats({
        alertCount: summaryData.total_alerts || 0,
        healSuccessRate: summaryData.heal_rate || 0,
        mttr: summaryData.mttd_min || 0,
        availability: summaryData.availability || 0,
      });
    }
  }, [summaryData, setStats]);

  // 🔧 修复: 使用真实 API 获取指标历史数据
  const { data: historyData } = useQuery({
    queryKey: ['metrics-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/history?hours=24');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  useEffect(() => {
    if (historyData && historyData.data) {
      setResourceData(historyData.data);
    }
  }, [historyData]);

  // 🔧 修复: 使用真实 API 获取修复历史
  const { data: repairHistory } = useQuery({
    queryKey: ['repair-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/history');
      return resp.data;
    },
    refetchInterval: 120000, // 120秒刷新
  });

  useEffect(() => {
    if (repairHistory && repairHistory.history) {
      setHealEvents(repairHistory.history.map((item: any) => ({
        id: item.id || String(Date.now()),
        timestamp: item.timestamp || new Date().toISOString(),
        type: item.type || 'auto',
        status: item.status || 'success',
        alertId: item.alert_id || 'N/A',
        description: item.description || item.script_name || '修复操作',
      })));
    }
  }, [repairHistory]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">仪表盘</h1>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            刷新
          </button>
        </div>
      </div>

      {/* 系统健康度卡片 */}
      {summaryLoading ? (
        <div className="text-center text-gray-500">加载中...</div>
      ) : summaryError ? (
        <div className="text-center text-red-500">加载失败</div>
      ) : (
        <DashboardCards />
      )}

      {/* 实时告警列表 */}
      <Card>
        <CardHeader>
          <CardTitle>实时告警</CardTitle>
        </CardHeader>
        <CardContent>
          <AlertStream />
        </CardContent>
      </Card>

      {/* 资源使用趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>资源使用趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <ResourceTrendChart data={resourceData} />
        </CardContent>
      </Card>

      {/* 修复活动时间线 */}
      <Card>
        <CardHeader>
          <CardTitle>修复活动</CardTitle>
        </CardHeader>
        <CardContent>
          <HealTimeline events={healEvents} />
        </CardContent>
      </Card>
    </div>
  );
}
