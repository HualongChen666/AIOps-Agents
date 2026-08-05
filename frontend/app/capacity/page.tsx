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

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      try {
        const [forecastRes, recRes] = await Promise.all([
          api.get('/api/v1/capacity/forecast'),
          api.get('/api/v1/capacity/recommendations'),
        ]);
        if (!mounted) return;
        setCapacityForecasts(forecastRes.data?.data ?? forecastRes.data ?? []);
        setRecommendations(recRes.data?.data ?? recRes.data ?? []);
      } catch (err) {
        console.error('Failed to load capacity data:', err);
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, [selectedTimeRange]);

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
        {capacityForecasts.map((forecast) => (
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
                  <span className={`font-medium ${forecast.forecast30d > forecast.threshold ? 'text-red-600' : 'text-green-600'}`}>
                    {forecast.forecast30d}{forecast.unit}
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${forecast.forecast30d > forecast.threshold ? 'bg-red-500' : 'bg-green-500'}`}
                    style={{ width: `${(forecast.forecast30d / 100) * 100}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 预测趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>容量预测趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">容量预测趋势图 (使用ECharts渲染)</p>
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
              <Select>
                <option value="70">70%</option>
                <option value="80">80%</option>
                <option value="90">90%</option>
              </Select>
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
