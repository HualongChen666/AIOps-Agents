'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface AnomalyPattern {
  pattern_type?: string;
  frequency?: number;
  avg_duration?: number;
  affected_metrics?: string[];
  last_occurrence?: string;
  confidence?: number;
  [key: string]: any;
}

interface AnomalyAnalysisData {
  total_patterns?: number;
  high_confidence_patterns?: number;
  medium_confidence_patterns?: number;
  low_confidence_patterns?: number;
  patterns?: AnomalyPattern[];
  analysis_time_range?: string;
  [key: string]: any;
}

export default function AnomalyAnalysisPage() {
  const [timeRange, setTimeRange] = useState('7d');
  const [selectedPattern, setSelectedPattern] = useState('all');

  const { data: analysisData, isLoading, error, refetch } = useQuery<AnomalyAnalysisData>({
    queryKey: ['monitoring-anomaly-analysis', timeRange, selectedPattern],
    queryFn: async () => {
      const params: any = { time_range: timeRange };
      if (selectedPattern !== 'all') params.pattern_type = selectedPattern;
      const resp = await api.get('/api/v1/monitoring/anomaly-analysis', { params });
      return resp.data;
    },
    refetchInterval: 120000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handlePatternAnalysis = async (patternType: string) => {
    try {
      await api.post('/api/v1/monitoring/anomaly-analysis/analyze', {
        pattern_type: patternType
      });
      refetch();
    } catch (err) {
      console.error('Failed to analyze pattern:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">异常分析</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
            <option value="30d">30天</option>
            <option value="90d">90天</option>
          </Select>
          <Select value={selectedPattern} onChange={(e) => setSelectedPattern(e.target.value)}>
            <option value="all">所有模式</option>
            <option value="spike">峰值异常</option>
            <option value="drop">下降异常</option>
            <option value="trend">趋势异常</option>
            <option value="seasonal">季节性异常</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总模式数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysisData?.total_patterns || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高置信度</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{analysisData?.high_confidence_patterns || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">中置信度</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{analysisData?.medium_confidence_patterns || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">低置信度</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{analysisData?.low_confidence_patterns || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>异常模式列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">模式类型</th>
                  <th className="px-4 py-2 text-left">频率</th>
                  <th className="px-4 py-2 text-left">平均持续时间</th>
                  <th className="px-4 py-2 text-left">影响指标</th>
                  <th className="px-4 py-2 text-left">最后发生</th>
                  <th className="px-4 py-2 text-left">置信度</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {analysisData?.patterns?.map((pattern, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{pattern.pattern_type}</td>
                    <td className="px-4 py-2">{pattern.frequency} 次</td>
                    <td className="px-4 py-2">{pattern.avg_duration?.toFixed(2)} 分钟</td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {pattern.affected_metrics?.map((metric, j) => (
                          <span key={j} className="px-2 py-1 bg-gray-100 rounded text-xs">
                            {metric}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      {pattern.last_occurrence ? new Date(pattern.last_occurrence).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        (pattern.confidence || 0) > 0.8 ? 'bg-green-100 text-green-800' : 
                        (pattern.confidence || 0) > 0.5 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {((pattern.confidence || 0) * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => pattern.pattern_type && handlePatternAnalysis(pattern.pattern_type)}
                      >
                        深度分析
                      </Button>
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
