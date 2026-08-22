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
import { Button } from '@/components/ui/button';
import { RefreshCw, AlertTriangle, CheckCircle, Clock, Activity } from 'lucide-react';

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

interface SystemHealth {
  prometheus: { status: string; metrics_count: number };
  grafana: { status: string; dashboards: number };
  zabbix: { status: string; triggers: number };
  cloudwatch: { status: string; alarms: number };
}

export default function DashboardPage() {
  const { stats, setStats } = useDashboardStore();
  const [resourceData, setResourceData] = useState<ResourceData[]>([]);
  const [healEvents, setHealEvents] = useState<HealEvent[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);

  // 🔧 修复: 使用真实 API 获取仪表盘摘要数据
  const { data: summaryData, isLoading: summaryLoading, error: summaryError, refetch } = useQuery({
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
      const resp = await api.get('/api/v1/repairs/history');
      return { history: resp.data.records || resp.data.history || [] };
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

  // 🔧 新增: 获取系统健康状态
  const { data: healthData } = useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/health');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  useEffect(() => {
    if (healthData) {
      setSystemHealth(healthData);
    }
  }, [healthData]);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'ok':
      case 'connected':
        return 'text-green-500';
      case 'degraded':
      case 'warning':
        return 'text-yellow-500';
      case 'unhealthy':
      case 'error':
      case 'disconnected':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusDot = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'ok':
      case 'connected':
        return 'bg-green-500';
      case 'degraded':
      case 'warning':
        return 'bg-yellow-500';
      case 'unhealthy':
      case 'error':
      case 'disconnected':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">仪表盘</h1>
          <p className="text-sm text-gray-500 mt-1">系统总览与实时监控</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetch()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 系统健康度卡片 */}
      {summaryLoading ? (
        <div className="text-center text-gray-500 py-8">加载中...</div>
      ) : summaryError ? (
        <div className="text-center text-red-500 py-8">加载失败</div>
      ) : (
        <DashboardCards />
      )}

      {/* 系统健康状态 */}
      {systemHealth && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              系统健康状态
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className={`w-3 h-3 rounded-full ${getStatusDot(systemHealth.prometheus?.status || 'unknown')}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium">Prometheus</div>
                  <div className={`text-xs ${getStatusColor(systemHealth.prometheus?.status || 'unknown')}`}>
                    {systemHealth.prometheus?.status || 'Unknown'}
                  </div>
                </div>
                <div className="text-sm text-gray-500">{systemHealth.prometheus?.metrics_count || 0} metrics</div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className={`w-3 h-3 rounded-full ${getStatusDot(systemHealth.grafana?.status || 'unknown')}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium">Grafana</div>
                  <div className={`text-xs ${getStatusColor(systemHealth.grafana?.status || 'unknown')}`}>
                    {systemHealth.grafana?.status || 'Unknown'}
                  </div>
                </div>
                <div className="text-sm text-gray-500">{systemHealth.grafana?.dashboards || 0} dashboards</div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className={`w-3 h-3 rounded-full ${getStatusDot(systemHealth.zabbix?.status || 'unknown')}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium">Zabbix</div>
                  <div className={`text-xs ${getStatusColor(systemHealth.zabbix?.status || 'unknown')}`}>
                    {systemHealth.zabbix?.status || 'Unknown'}
                  </div>
                </div>
                <div className="text-sm text-gray-500">{systemHealth.zabbix?.triggers || 0} triggers</div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className={`w-3 h-3 rounded-full ${getStatusDot(systemHealth.cloudwatch?.status || 'unknown')}`} />
                <div className="flex-1">
                  <div className="text-sm font-medium">CloudWatch</div>
                  <div className={`text-xs ${getStatusColor(systemHealth.cloudwatch?.status || 'unknown')}`}>
                    {systemHealth.cloudwatch?.status || 'Unknown'}
                  </div>
                </div>
                <div className="text-sm text-gray-500">{systemHealth.cloudwatch?.alarms || 0} alarms</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 实时告警列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            实时告警
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AlertStream />
        </CardContent>
      </Card>

      {/* 资源使用趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            资源使用趋势
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResourceTrendChart data={resourceData} />
        </CardContent>
      </Card>

      {/* 修复活动时间线 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5" />
            修复活动
          </CardTitle>
        </CardHeader>
        <CardContent>
          <HealTimeline events={healEvents} />
        </CardContent>
      </Card>
    </div>
  );
}
