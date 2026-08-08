'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CapacityForecast {
  metric: string;
  currentValue: number;
  forecast7d: number;
  forecast30d: number;
  threshold: number;
  unit: string;
}

interface ScalingRecommendation {
  id: string;
  service: string;
  action: 'scale-up' | 'scale-down' | 'no-action';
  reason: string;
  priority: 'high' | 'medium' | 'low';
  estimatedCost: number;
}

export default function CapacityPage() {
  const [selectedTimeRange, setSelectedTimeRange] = useState('30d');
  const [capacityForecasts, setCapacityForecasts] = useState<CapacityForecast[]>([]);
  const [recommendations, setRecommendations] = useState<ScalingRecommendation[]>([]);
  const [history, setHistory] = useState<Record<string, any>>({});
  const [threshold, setThreshold] = useState<number | ''>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      try {
        setLoading(true);
        const [snapshotRes, historyRes, forecastRes, recRes] = await Promise.all([
          api.get('/api/v1/metrics/snapshot').catch(() => null),
          api.get('/api/v1/metrics/history').catch(() => null),
          api.get('/api/v1/capacity/forecast').catch(() => null),
          api.get('/api/v1/capacity/recommendations').catch(() => null),
        ]);

        if (!mounted) return;

        setHistory(historyRes?.data || {});
        const forecasts = (forecastRes?.data?.data ?? forecastRes?.data ?? []) as CapacityForecast[];
        setCapacityForecasts(forecasts);
        setRecommendations((recRes?.data?.data ?? recRes?.data ?? []) as ScalingRecommendation[]);

        if (forecasts.length > 0) {
          const avg = forecasts.reduce((sum, f) => sum + (Number(f.threshold) || 0), 0) / forecasts.length;
          setThreshold(Math.round(avg));
        } else {
          const cpu = snapshotRes?.data?.cpu?.usage_percent;
          setThreshold(typeof cpu === 'number' ? Math.round(cpu + 20) : 80);
        }
      } catch (err) {
        console.error('Failed to load capacity data:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, [selectedTimeRange]);

  const getThreshold = (forecast: CapacityForecast): number => {
    return threshold !== '' ? Number(threshold) : forecast.threshold;
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'scale-up':
        return 'bg-blue-100 text-blue-800';
      case 'scale-down':
        return 'bg-green-100 text-green-800';
      case 'no-action':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'scale-up':
        return '扩容';
      case 'scale-down':
        return '缩容';
      case 'no-action':
        return '无需操作';
      default:
        return action;
    }
  };

  const renderTrend = (metricKey: string) => {
    const raw = history[metricKey];
    if (!Array.isArray(raw) || raw.length === 0) {
      return <p className="text-sm text-gray-500 h-24 flex items-center justify-center">无历史数据</p>;
    }
    const values = raw.map((v: any) => Number(v) || 0);
    const max = Math.max(1, ...values);
    return (
      <div className="flex items-end h-24 gap-1">
        {values.map((value, index) => (
          <div
            key={index}
            className="flex-1 bg-indigo-400 rounded-sm"
            style={{ height: `${Math.round((value / max) * 100)}%` }}
            title={`${value.toFixed(1)}`}
          />
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-500">
        容量数据加载中...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">容量预测</h1>
        <div className="flex gap-2">
          <Select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
          >
            <option value="7d">7天</option>
            <option value="30d">30天</option>
            <option value="90d">90天</option>
          </Select>
          <Button>刷新预测</Button>
        </div>
      </div>

      {/* 容量预测概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {capacityForecasts.map((forecast) => {
          const t = getThreshold(forecast);
          const exceeds = forecast.forecast30d > t;
          const pct = t > 0 ? Math.min(100, Math.max(0, (forecast.forecast30d / t) * 100)) : 0;
          return (
            <Card key={forecast.metric}>
              <CardHeader>
                <CardTitle className="text-sm">{forecast.metric}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">当前值</span>
                    <span className="font-medium">{forecast.currentValue}{forecast.unit}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">7天预测</span>
                    <span className="font-medium">{forecast.forecast7d}{forecast.unit}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">30天预测</span>
                    <span className={`font-medium ${exceeds ? 'text-red-600' : 'text-green-600'}`}>
                      {forecast.forecast30d}{forecast.unit}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${exceeds ? 'bg-red-500' : 'bg-green-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500">阈值: {t}{forecast.unit}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* 预测趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>容量预测趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {['cpu', 'memory', 'net_in'].map((key) => (
              <div key={key}>
                <p className="text-sm font-medium text-gray-700 mb-2">
                  {key === 'cpu' ? 'CPU' : key === 'memory' ? '内存' : '网络入站'} 历史趋势
                </p>
                {renderTrend(key)}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 扩容建议 */}
      <Card>
        <CardHeader>
          <CardTitle>扩容建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recommendations.length === 0 && (
              <p className="text-sm text-gray-500">暂无扩容建议</p>
            )}
            {recommendations.map((rec) => (
              <div key={rec.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium text-gray-900">{rec.service}</h3>
                      <Badge className={getActionColor(rec.action)}>
                        {getActionLabel(rec.action)}
                      </Badge>
                      <Badge className={getPriorityColor(rec.priority)}>
                        {rec.priority === 'high' ? '高优先级' : rec.priority === 'medium' ? '中优先级' : '低优先级'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{rec.reason}</p>
                    <p className="text-sm text-gray-500">
                      预计成本: ¥{rec.estimatedCost}/月
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    {rec.action !== 'no-action' && (
                      <Button size="sm">
                        应用建议
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 容量规划配置 */}
      <Card>
        <CardHeader>
          <CardTitle>容量规划配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">预测模型</label>
              <Select>
                <option value="linear">线性回归</option>
                <option value="arima">ARIMA</option>
                <option value="lstm">LSTM</option>
                <option value="ensemble">集成模型</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">告警阈值</label>
              <input
                type="number"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="由后端预测阈值自动计算"
              />
              <p className="text-xs text-gray-500 mt-1">默认取自容量预测阈值平均值</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">自动扩容</label>
              <Select>
                <option value="enabled">启用</option>
                <option value="disabled">禁用</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">最大实例数</label>
              <Select>
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
              </Select>
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <Button>保存配置</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
