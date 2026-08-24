'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Brain, RefreshCw, TrendingUp, AlertTriangle } from 'lucide-react';

interface Prediction {
  id: string;
  metric: string;
  predicted_value: number;
  confidence: number;
  predicted_at: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  model: string;
}

interface PredictionStats {
  total_predictions: number;
  accurate_predictions: number;
  accuracy_rate: number;
  avg_confidence: number;
}

export default function AlertPredictionPage() {
  const [timeRange, setTimeRange] = useState('24h');
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showError = toast.error;

  const { data: predictionsData, isLoading: predictionsLoading, error: predictionsError, refetch: refetchPredictions } = useQuery<Prediction[]>({
    queryKey: ['alert-predictions', timeRange],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/alerts/prediction?time_range=${timeRange}`);
      return resp.data.predictions || resp.data || [];
    },
    refetchInterval: 60000,
  });

  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery<PredictionStats>({
    queryKey: ['prediction-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/prediction/stats');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (predictionsError) showError('Failed to load predictions');
  }, [predictionsError, showError]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  if (predictionsLoading || statsLoading) {
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
          <Brain className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警预测</h1>
            <p className="text-sm text-gray-500">AI驱动的告警预测和预警</p>
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
          </Select>
          <Button onClick={() => { refetchPredictions(); refetchStats(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {statsData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              预测统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">总预测数</div>
                <div className="text-2xl font-bold text-[var(--accent-blue)]">{statsData.total_predictions}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">准确预测</div>
                <div className="text-2xl font-bold text-[var(--accent-green)]">{statsData.accurate_predictions}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">准确率</div>
                <div className="text-2xl font-bold text-[var(--accent-yellow)]">{(statsData.accuracy_rate * 100).toFixed(1)}%</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">平均置信度</div>
                <div className="text-2xl font-bold text-[var(--accent-cyan)]">{(statsData.avg_confidence * 100).toFixed(1)}%</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>预测结果</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>指标</TableHead>
                <TableHead>预测值</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>严重度</TableHead>
                <TableHead>模型</TableHead>
                <TableHead>预测时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(!predictionsData || predictionsData.length === 0) ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <EmptyState
                      title="没有预测数据"
                      description="当前没有告警预测数据"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                predictionsData.map((prediction) => (
                  <TableRow key={prediction.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{prediction.metric}</TableCell>
                    <TableCell className="font-mono text-sm">{prediction.predicted_value.toFixed(2)}</TableCell>
                    <TableCell>
                      <Badge className={getConfidenceColor(prediction.confidence)}>
                        {(prediction.confidence * 100).toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(prediction.severity)}>
                        {prediction.severity}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{prediction.model}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(prediction.predicted_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            高风险预测
          </CardTitle>
        </CardHeader>
        <CardContent>
          {predictionsData && predictionsData.filter(p => p.severity === 'critical' || p.severity === 'high').length > 0 ? (
            <div className="space-y-2">
              {predictionsData
                .filter(p => p.severity === 'critical' || p.severity === 'high')
                .map((prediction) => (
                  <div key={prediction.id} className="p-3 border rounded-lg border-red-200 bg-red-50">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{prediction.metric}</span>
                      <Badge className={getSeverityColor(prediction.severity)}>
                        {prediction.severity}
                      </Badge>
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      预测值: {prediction.predicted_value.toFixed(2)} | 置信度: {(prediction.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <EmptyState title="没有高风险预测" description="当前没有高风险的告警预测" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
