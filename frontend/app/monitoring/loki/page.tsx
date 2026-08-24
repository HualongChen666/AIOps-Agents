'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LokiLogEntry {
  timestamp?: string;
  line?: string;
  stream?: Record<string, string>;
  labels?: Record<string, string>;
  [key: string]: any;
}

interface LokiData {
  loki_url?: string;
  loki_version?: string;
  total_streams?: number;
  total_entries?: number;
  ingestion_rate?: number;
  retention_days?: number;
  logs?: LokiLogEntry[];
  query?: string;
  [key: string]: any;
}

export default function LokiPage() {
  const [query, setQuery] = useState('{level="error"}');
  const [timeRange, setTimeRange] = useState('1h');
  const [isQuerying, setIsQuerying] = useState(false);

  const { data: lokiData, refetch } = useQuery<LokiData>({
    queryKey: ['monitoring-loki', query, timeRange],
    queryFn: async () => {
      if (!query.trim()) return { logs: [] };
      const resp = await api.get('/api/v1/monitoring/loki', {
        params: { query, time_range: timeRange }
      });
      return resp.data;
    },
    enabled: query.length > 0,
    refetchInterval: false,
  });

  const handleQuery = async () => {
    setIsQuerying(true);
    await refetch();
    setIsQuerying(false);
  };

  if (!lokiData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Loki日志存储</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>LogQL查询</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="输入LogQL查询..."
                  className="flex-1"
                  onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                />
                <Button onClick={handleQuery} disabled={isQuerying}>
                  {isQuerying ? '查询中...' : '查询'}
                </Button>
              </div>
              <div className="text-sm text-gray-500">
                示例查询: {`{level="error"}`}, {`{job="api"} |= "error"`}, {`{service="worker"} | logfmt`}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Loki日志存储</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Loki信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">URL:</span>
              <span className="font-medium">{lokiData?.loki_url || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">版本:</span>
              <span className="font-medium">{lokiData?.loki_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总流数:</span>
              <span className="font-medium">{lokiData?.total_streams?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总日志条目:</span>
              <span className="font-medium">{lokiData?.total_entries?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">摄入速率:</span>
              <span className="font-medium">{lokiData?.ingestion_rate?.toFixed(2) || '-'} MB/s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">保留期:</span>
              <span className="font-medium">{lokiData?.retention_days || '-'} 天</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>LogQL查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入LogQL查询..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              />
              <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
                <option value="5m">5分钟</option>
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
              </Select>
              <Button onClick={handleQuery} disabled={isQuerying}>
                {isQuerying ? '查询中...' : '查询'}
              </Button>
            </div>
            <div className="text-sm text-gray-500">
              示例查询: {`{level="error"}`}, {`{job="api"} |= "error"`}, {`{service="worker"} | logfmt`}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>日志结果</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">时间</th>
                  <th className="px-4 py-2 text-left">流标签</th>
                  <th className="px-4 py-2 text-left">日志内容</th>
                </tr>
              </thead>
              <tbody>
                {lokiData?.logs?.map((log, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {log.stream && Object.entries(log.stream).map(([key, value], j) => (
                          <span key={j} className="px-2 py-1 bg-gray-100 rounded text-xs">
                            {key}={value}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2 max-w-md">{log.line}</td>
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
