'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LogPattern {
  pattern?: string;
  count?: number;
  frequency?: number;
  first_seen?: string;
  last_seen?: string;
  severity?: string;
  [key: string]: any;
}

interface LogAnalysisData {
  total_logs_analyzed?: number;
  unique_patterns?: number;
  error_patterns?: number;
  warning_patterns?: number;
  time_range?: string;
  patterns?: LogPattern[];
  [key: string]: any;
}

export default function LogAnalysisPage() {
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedSeverity, setSelectedSeverity] = useState('all');

  const { data: analysisData, isLoading, error, refetch } = useQuery<LogAnalysisData>({
    queryKey: ['monitoring-log-analysis', timeRange, selectedSeverity],
    queryFn: async () => {
      const params: any = { time_range: timeRange };
      if (selectedSeverity !== 'all') params.severity = selectedSeverity;
      const resp = await api.get('/api/v1/monitoring/log-analysis', { params });
      return resp.data;
    },
    refetchInterval: 120000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handlePatternAction = async (pattern: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/log-analysis/pattern-action', {
        pattern,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform pattern action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">日志分析</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
            <option value="30d">30天</option>
          </Select>
          <Select value={selectedSeverity} onChange={(e) => setSelectedSeverity(e.target.value)}>
            <option value="all">所有级别</option>
            <option value="error">错误</option>
            <option value="warning">警告</option>
            <option value="info">信息</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">分析日志数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysisData?.total_logs_analyzed?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">唯一模式</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analysisData?.unique_patterns || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">错误模式</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{analysisData?.error_patterns || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告模式</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{analysisData?.warning_patterns || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>日志模式列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">模式</th>
                  <th className="px-4 py-2 text-left">出现次数</th>
                  <th className="px-4 py-2 text-left">频率</th>
                  <th className="px-4 py-2 text-left">首次出现</th>
                  <th className="px-4 py-2 text-left">最后出现</th>
                  <th className="px-4 py-2 text-left">严重性</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {analysisData?.patterns?.map((pattern, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2 max-w-md truncate">{pattern.pattern}</td>
                    <td className="px-4 py-2">{pattern.count?.toLocaleString()}</td>
                    <td className="px-4 py-2">{pattern.frequency?.toFixed(2)}/min</td>
                    <td className="px-4 py-2">
                      {pattern.first_seen ? new Date(pattern.first_seen).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      {pattern.last_seen ? new Date(pattern.last_seen).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        pattern.severity === 'error' ? 'bg-red-100 text-red-800' : 
                        pattern.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {pattern.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => pattern.pattern && handlePatternAction(pattern.pattern, 'investigate')}
                      >
                        调查
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
