'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ESLogEntry {
  _id?: string;
  _index?: string;
  _source?: {
    timestamp?: string;
    level?: string;
    service?: string;
    message?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

interface ElasticsearchData {
  es_url?: string;
  es_version?: string;
  total_indices?: number;
  total_documents?: number;
  data_size_gb?: number;
  cluster_name?: string;
  nodes_count?: number;
  logs?: ESLogEntry[];
  query?: string;
  [key: string]: any;
}

export default function ElasticsearchPage() {
  const [query, setQuery] = useState('*');
  const [timeRange, setTimeRange] = useState('1h');
  const [isQuerying, setIsQuerying] = useState(false);

  const { data: esData, refetch } = useQuery<ElasticsearchData>({
    queryKey: ['monitoring-elasticsearch', query, timeRange],
    queryFn: async () => {
      if (!query.trim()) return { logs: [] };
      const resp = await api.get('/api/v1/monitoring/elasticsearch', {
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

  if (!esData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Elasticsearch日志</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Elasticsearch查询</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="输入Elasticsearch查询..."
                  className="flex-1"
                  onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                />
                <Button onClick={handleQuery} disabled={isQuerying}>
                  {isQuerying ? '查询中...' : '查询'}
                </Button>
              </div>
              <div className="text-sm text-gray-500">
                示例查询: *, level:error, service:api
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
        <h1 className="text-3xl font-bold text-gray-900">Elasticsearch日志</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Elasticsearch信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">URL:</span>
              <span className="font-medium">{esData?.es_url || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">版本:</span>
              <span className="font-medium">{esData?.es_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">集群名称:</span>
              <span className="font-medium">{esData?.cluster_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">节点数:</span>
              <span className="font-medium">{esData?.nodes_count || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总索引数:</span>
              <span className="font-medium">{esData?.total_indices || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总文档数:</span>
              <span className="font-medium">{esData?.total_documents?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">数据大小:</span>
              <span className="font-medium">{esData?.data_size_gb?.toFixed(2) || '-'} GB</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Elasticsearch查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入Elasticsearch查询..."
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
              示例查询: *, level:error, service:api
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
                  <th className="px-4 py-2 text-left">ID</th>
                  <th className="px-4 py-2 text-left">索引</th>
                  <th className="px-4 py-2 text-left">时间</th>
                  <th className="px-4 py-2 text-left">级别</th>
                  <th className="px-4 py-2 text-left">服务</th>
                  <th className="px-4 py-2 text-left">消息</th>
                </tr>
              </thead>
              <tbody>
                {esData?.logs?.map((log, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2 font-mono text-xs">{log._id}</td>
                    <td className="px-4 py-2">{log._index}</td>
                    <td className="px-4 py-2">
                      {log._source?.timestamp ? new Date(log._source.timestamp).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        log._source?.level === 'error' || log._source?.level === 'critical' ? 'bg-red-100 text-red-800' : 
                        log._source?.level === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {log._source?.level}
                      </span>
                    </td>
                    <td className="px-4 py-2">{log._source?.service}</td>
                    <td className="px-4 py-2 max-w-md">{log._source?.message}</td>
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
