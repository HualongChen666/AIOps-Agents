'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

// Aggregated from the in-process Prometheus registry: one entry per
// (path, method) that actually received requests.
interface FastAPIEndpointMetric {
  path?: string;
  method?: string;
  request_count?: number;
  avg_latency_ms?: number | null;
  error_rate?: number;
  [key: string]: any;
}

interface FastAPITelemetryData {
  fastapi_version?: string;
  total_requests?: number;
  total_errors?: number;
  avg_response_time_ms?: number | null;
  endpoint?: string | null;
  time_range?: string;
  endpoints?: FastAPIEndpointMetric[];
  [key: string]: any;
}

export default function FastAPITelemetryPage() {
  const { data: fastapiData, isLoading, error, refetch } = useQuery<FastAPITelemetryData>({
    queryKey: ['monitoring-fastapi-telemetry'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/fastapi-telemetry');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">FastAPI遥测</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>应用信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">FastAPI版本:</span>
              <span className="font-medium">{fastapiData?.fastapi_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">统计范围:</span>
              <span className="font-medium">{fastapiData?.time_range || '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fastapiData?.total_requests?.toLocaleString() ?? '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总错误数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{fastapiData?.total_errors?.toLocaleString() ?? '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均响应时间</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {typeof fastapiData?.avg_response_time_ms === 'number' ? `${fastapiData.avg_response_time_ms.toFixed(2)} ms` : '-'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">端点数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fastapiData?.endpoints?.length ?? '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>端点指标</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">端点</th>
                  <th className="px-4 py-2 text-left">方法</th>
                  <th className="px-4 py-2 text-left">请求数</th>
                  <th className="px-4 py-2 text-left">平均耗时</th>
                  <th className="px-4 py-2 text-left">错误率</th>
                </tr>
              </thead>
              <tbody>
                {fastapiData?.endpoints?.length ? (
                  fastapiData.endpoints.map((metric, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">{metric.path}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          metric.method === 'GET' ? 'bg-blue-100 text-blue-800' :
                          metric.method === 'POST' ? 'bg-green-100 text-green-800' :
                          metric.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                          metric.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {metric.method}
                        </span>
                      </td>
                      <td className="px-4 py-2">{metric.request_count?.toLocaleString() ?? '-'}</td>
                      <td className="px-4 py-2">
                        {typeof metric.avg_latency_ms === 'number' ? `${metric.avg_latency_ms.toFixed(2)} ms` : '-'}
                      </td>
                      <td className="px-4 py-2">{((metric.error_rate ?? 0) * 100).toFixed(2)}%</td>
                    </tr>
                  ))
                ) : (
                  <tr className="border-t">
                    <td colSpan={5} className="px-4 py-4 text-center text-gray-500">暂无请求记录</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
