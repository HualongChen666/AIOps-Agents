'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface Anomaly {
  id?: string;
  timestamp?: string;
  metric_name?: string;
  metric_value?: number;
  expected_value?: number;
  deviation?: number;
  severity?: string;
  status?: string;
  description?: string;
  [key: string]: any;
}

interface AnomalyDetectionData {
  total_anomalies?: number;
  critical_anomalies?: number;
  warning_anomalies?: number;
  info_anomalies?: number;
  detection_rate?: number;
  anomalies?: Anomaly[];
  time_range?: string;
  [key: string]: any;
}

export default function AnomalyDetectionPage() {
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedSeverity, setSelectedSeverity] = useState('all');

  const { data: anomalyData, isLoading, error, refetch } = useQuery<AnomalyDetectionData>({
    queryKey: ['monitoring-anomaly-detection', timeRange, selectedSeverity],
    queryFn: async () => {
      const params: any = { time_range: timeRange };
      if (selectedSeverity !== 'all') params.severity = selectedSeverity;
      const resp = await api.get('/api/v1/monitoring/anomaly-detection', { params });
      return resp.data;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleAnomalyAction = async (anomalyId: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/anomaly-detection/action', {
        anomaly_id: anomalyId,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform anomaly action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">异常检测</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
            <option value="30d">30天</option>
          </Select>
          <Select value={selectedSeverity} onChange={(e) => setSelectedSeverity(e.target.value)}>
            <option value="all">所有严重级别</option>
            <option value="critical">严重</option>
            <option value="warning">警告</option>
            <option value="info">信息</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总异常数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{anomalyData?.total_anomalies || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">严重异常</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{anomalyData?.critical_anomalies || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告异常</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{anomalyData?.warning_anomalies || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">检测率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(anomalyData?.detection_rate || 0).toFixed(2)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>异常列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">时间</th>
                  <th className="px-4 py-2 text-left">指标名称</th>
                  <th className="px-4 py-2 text-left">当前值</th>
                  <th className="px-4 py-2 text-left">期望值</th>
                  <th className="px-4 py-2 text-left">偏差</th>
                  <th className="px-4 py-2 text-left">严重性</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {anomalyData?.anomalies?.map((anomaly, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">
                      {anomaly.timestamp ? new Date(anomaly.timestamp).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">{anomaly.metric_name}</td>
                    <td className="px-4 py-2">{anomaly.metric_value?.toFixed(2)}</td>
                    <td className="px-4 py-2">{anomaly.expected_value?.toFixed(2)}</td>
                    <td className="px-4 py-2">{anomaly.deviation?.toFixed(2)}%</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        anomaly.severity === 'critical' ? 'bg-red-100 text-red-800' : 
                        anomaly.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {anomaly.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        anomaly.status === 'open' ? 'bg-red-100 text-red-800' : 
                        anomaly.status === 'investigating' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {anomaly.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          onClick={() => anomaly.id && handleAnomalyAction(anomaly.id, 'investigate')}
                        >
                          调查
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => anomaly.id && handleAnomalyAction(anomaly.id, 'resolve')}
                        >
                          解决
                        </Button>
                      </div>
                    </td>
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
