'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface APIEndpoint {
  path?: string;
  method?: string;
  status?: string;
  avg_response_time?: number;
  p95_response_time?: number;
  p99_response_time?: number;
  error_rate?: number;
  request_count?: number;
  throughput?: number;
  [key: string]: any;
}

interface APIPerformanceData {
  total_endpoints?: number;
  total_requests?: number;
  avg_response_time?: number;
  total_error_rate?: number;
  endpoints?: APIEndpoint[];
  time_range?: string;
  [key: string]: any;
}

export default function APIPerformancePage() {
  const [timeRange, setTimeRange] = useState('1h');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('avg_response_time');

  const { data: apiData, isLoading, error, refetch } = useQuery<APIPerformanceData>({
    queryKey: ['monitoring-api-performance', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/api-performance', {
        params: { time_range: timeRange }
      });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const filteredEndpoints = apiData?.endpoints
    ?.filter(e => 
      e.path?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.method?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => ((b[sortBy as keyof APIEndpoint] as number) || 0) - ((a[sortBy as keyof APIEndpoint] as number) || 0)) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">API性能监控</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总端点数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apiData?.total_endpoints || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apiData?.total_requests || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均响应时间</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{apiData?.avg_response_time?.toFixed(2) || '-'} ms</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总错误率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(apiData?.total_error_rate || 0).toFixed(2)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API端点列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索端点路径或方法..."
                className="flex-1"
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-2 border rounded"
              >
                <option value="avg_response_time">按平均响应时间排序</option>
                <option value="p95_response_time">按P95响应时间排序</option>
                <option value="error_rate">按错误率排序</option>
                <option value="throughput">按吞吐量排序</option>
              </select>
            </div>
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">路径</th>
                    <th className="px-4 py-2 text-left">方法</th>
                    <th className="px-4 py-2 text-left">状态</th>
                    <th className="px-4 py-2 text-left">平均响应时间</th>
                    <th className="px-4 py-2 text-left">P95响应时间</th>
                    <th className="px-4 py-2 text-left">P99响应时间</th>
                    <th className="px-4 py-2 text-left">错误率</th>
                    <th className="px-4 py-2 text-left">请求数</th>
                    <th className="px-4 py-2 text-left">吞吐量</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEndpoints.map((endpoint, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">{endpoint.path}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          endpoint.method === 'GET' ? 'bg-blue-100 text-blue-800' :
                          endpoint.method === 'POST' ? 'bg-green-100 text-green-800' :
                          endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                          endpoint.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {endpoint.method}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          endpoint.status === 'healthy' ? 'bg-green-100 text-green-800' : 
                          endpoint.status === 'slow' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {endpoint.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{endpoint.avg_response_time?.toFixed(2)} ms</td>
                      <td className="px-4 py-2">{endpoint.p95_response_time?.toFixed(2)} ms</td>
                      <td className="px-4 py-2">{endpoint.p99_response_time?.toFixed(2)} ms</td>
                      <td className="px-4 py-2">{(endpoint.error_rate || 0).toFixed(2)}%</td>
                      <td className="px-4 py-2">{endpoint.request_count}</td>
                      <td className="px-4 py-2">{endpoint.throughput?.toFixed(2)} req/s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
