'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { TrendingUp, RefreshCw, LineChart, BarChart3 } from 'lucide-react';

interface TrendData {
  date: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface AlertTrends {
  daily_trends: TrendData[];
  weekly_trends: TrendData[];
  monthly_trends: TrendData[];
  prediction: TrendData[];
}

export default function AlertTrendsPage() {
  const [timeRange, setTimeRange] = useState('7d');
  const [viewType, setViewType] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showError = toast.error;

  const { data: trendsData, isLoading: trendsLoading, error: trendsError, refetch: refetchTrends } = useQuery<AlertTrends>({
    queryKey: ['alert-trends', timeRange],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/alerts/trends?time_range=${timeRange}`);
      return resp.data;
    },
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (trendsError) showError('Failed to load alert trends');
  }, [trendsError, showError]);

  const getTrendData = () => {
    switch (viewType) {
      case 'daily':
        return trendsData?.daily_trends || [];
      case 'weekly':
        return trendsData?.weekly_trends || [];
      case 'monthly':
        return trendsData?.monthly_trends || [];
      default:
        return [];
    }
  };

  const trendData = getTrendData();
  const maxValue = Math.max(...trendData.map(d => d.total), 1);

  if (trendsLoading) {
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
          <TrendingUp className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警趋势</h1>
            <p className="text-sm text-gray-500">告警趋势分析和预测</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
          </Select>
          <Button onClick={() => refetchTrends()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {trendsData && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LineChart className="h-5 w-5" />
                趋势视图
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => setViewType('daily')}
                  className={`px-4 py-2 rounded-lg font-medium transition ${viewType === 'daily' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                >
                  每日
                </button>
                <button
                  onClick={() => setViewType('weekly')}
                  className={`px-4 py-2 rounded-lg font-medium transition ${viewType === 'weekly' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                >
                  每周
                </button>
                <button
                  onClick={() => setViewType('monthly')}
                  className={`px-4 py-2 rounded-lg font-medium transition ${viewType === 'monthly' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                >
                  每月
                </button>
              </div>
              <div className="flex items-end gap-2 h-64">
                {trendData.map((item, idx) => (
                  <div key={idx} className="flex-1 flex flex-col items-center">
                    <div className="w-full flex flex-col gap-1">
                      <div
                        className="w-full bg-red-500 rounded-t"
                        style={{ height: `${(item.critical / maxValue) * 100}%` }}
                        title={`严重: ${item.critical}`}
                      />
                      <div
                        className="w-full bg-orange-500"
                        style={{ height: `${(item.high / maxValue) * 100}%` }}
                        title={`高: ${item.high}`}
                      />
                      <div
                        className="w-full bg-yellow-500"
                        style={{ height: `${(item.medium / maxValue) * 100}%` }}
                        title={`中: ${item.medium}`}
                      />
                      <div
                        className="w-full bg-green-500 rounded-b"
                        style={{ height: `${(item.low / maxValue) * 100}%` }}
                        title={`低: ${item.low}`}
                      />
                    </div>
                    <div className="text-xs mt-2 text-gray-500">{item.date}</div>
                  </div>
                ))}
              </div>
              <div className="flex justify-center gap-4 mt-4 text-sm">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-red-500 rounded" />
                  <span>严重</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-orange-500 rounded" />
                  <span>高</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-yellow-500 rounded" />
                  <span>中</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 bg-green-500 rounded" />
                  <span>低</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                告警预测
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-2 h-64">
                {trendsData.prediction.map((item, idx) => (
                  <div key={idx} className="flex-1 flex flex-col items-center">
                    <div
                      className="w-full bg-[var(--accent-cyan)] rounded-t opacity-50"
                      style={{ height: `${(item.total / maxValue) * 100}%` }}
                    />
                    <div className="text-xs mt-2 text-gray-500">{item.date}</div>
                  </div>
                ))}
              </div>
              <div className="text-center mt-4 text-sm text-gray-500">
                * 预测数据仅供参考
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>趋势摘要</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">总告警数</div>
                  <div className="text-2xl font-bold text-[var(--accent-blue)]">
                    {trendData.reduce((sum, d) => sum + d.total, 0)}
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">平均每日告警</div>
                  <div className="text-2xl font-bold text-[var(--accent-yellow)]">
                    {Math.round(trendData.reduce((sum, d) => sum + d.total, 0) / trendData.length)}
                  </div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-gray-500 mb-1">峰值告警</div>
                  <div className="text-2xl font-bold text-[var(--accent-red)]">
                    {Math.max(...trendData.map(d => d.total))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
