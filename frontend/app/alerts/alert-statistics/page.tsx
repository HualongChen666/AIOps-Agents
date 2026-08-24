'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { BarChart3, RefreshCw, TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface AlertStatistics {
  total_alerts: number;
  open_alerts: number;
  acknowledged_alerts: number;
  resolved_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  avg_resolution_time: number;
  avg_acknowledgement_time: number;
  alerts_by_source: Array<{ source: string; count: number }>;
  alerts_by_service: Array<{ service: string; count: number }>;
  alerts_by_hour: Array<{ hour: number; count: number }>;
  alerts_by_day: Array<{ date: string; count: number }>;
}

export default function AlertStatisticsPage() {
  const [timeRange, setTimeRange] = useState('24h');
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showError = toast.error;

  const { data: statsData, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useQuery<AlertStatistics>({
    queryKey: ['alert-statistics', timeRange],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/alerts/statistics?time_range=${timeRange}`);
      return resp.data;
    },
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (statsError) showError('Failed to load alert statistics');
  }, [statsError, showError]);

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警统计</h1>
            <p className="text-sm text-gray-500">告警数据的统计分析</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <option value="1h">最近1小时</option>
            <option value="24h">最近24小时</option>
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
          </Select>
          <Button onClick={() => refetchStats()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {statsData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">总告警数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-[var(--accent-blue)]">{statsData.total_alerts}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  未处理
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">{statsData.open_alerts}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  已解决
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">{statsData.resolved_alerts}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  平均解决时间
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-[var(--accent-yellow)]">{Math.round(statsData.avg_resolution_time / 60)}m</div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>按严重度分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">严重</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div className="bg-red-500 h-2 rounded-full" style={{ width: `${(statsData.critical_alerts / statsData.total_alerts) * 100}%` }} />
                      </div>
                      <span className="text-sm font-medium">{statsData.critical_alerts}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">高</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${(statsData.high_alerts / statsData.total_alerts) * 100}%` }} />
                      </div>
                      <span className="text-sm font-medium">{statsData.high_alerts}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">中</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div className="bg-yellow-500 h-2 rounded-full" style={{ width: `${(statsData.medium_alerts / statsData.total_alerts) * 100}%` }} />
                      </div>
                      <span className="text-sm font-medium">{statsData.medium_alerts}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">低</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{ width: `${(statsData.low_alerts / statsData.total_alerts) * 100}%` }} />
                      </div>
                      <span className="text-sm font-medium">{statsData.low_alerts}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>按来源分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {statsData.alerts_by_source.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm">{item.source}</span>
                      <span className="text-sm font-medium">{item.count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>按服务分布</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {statsData.alerts_by_service.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm">{item.service}</span>
                    <span className="text-sm font-medium">{item.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                每小时告警趋势
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-2 h-40">
                {statsData.alerts_by_hour.map((item, idx) => (
                  <div key={idx} className="flex-1 flex flex-col items-center">
                    <div
                      className="w-full bg-[var(--accent-blue)] rounded-t"
                      style={{ height: `${Math.min((item.count / Math.max(...statsData.alerts_by_hour.map(h => h.count))) * 100, 100)}%` }}
                    />
                    <div className="text-xs mt-1">{item.hour}:00</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
