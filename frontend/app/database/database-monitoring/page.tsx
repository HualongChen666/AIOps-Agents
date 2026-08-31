'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import { TrendChart } from '@/components/charts/TrendChart';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';
import toast from 'react-hot-toast';

// API Response Types
interface DatabasePerformance {
  cpu_usage: number;
  memory_usage: number;
  disk_io: number;
  network_io: number;
  query_latency: number;
  connection_count: number;
  active_queries: number;
  timestamp: string;
}

interface DatabaseQuery {
  query_id: string;
  query_text: string;
  query_params?: any[];
  execution_count: number;
  avg_duration_ms: number;
  last_executed: string;
  database: string;
  table_name: string;
}

interface HealthCheckResult {
  status: 'healthy' | 'warning' | 'critical';
  checks: {
    name: string;
    status: 'pass' | 'fail' | 'warning';
    message: string;
    timestamp: string;
  }[];
}

export default function DatabaseMonitoringPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Performance data
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [performanceHistory, setPerformanceHistory] = useState({
    cpu: [] as number[],
    memory: [] as number[],
    disk_io: [] as number[],
    network_io: [] as number[],
    query_latency: [] as number[],
    connections: [] as number[],
  });

  // Queries
  const [queries, setQueries] = useState<DatabaseQuery[]>([]);
  const [slowQueries, setSlowQueries] = useState<DatabaseQuery[]>([]);

  // Health check
  const [healthStatus, setHealthStatus] = useState<HealthCheckResult | null>(null);

  // Time range filter
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    fetchAllData();
    let interval: NodeJS.Timeout;

    if (autoRefresh) {
      interval = setInterval(() => {
        fetchAllData();
      }, 10000); // Refresh every 10 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, timeRange]);

  const fetchAllData = async () => {
    try {
      await Promise.all([
        fetchPerformance(),
        fetchQueries(),
        fetchSlowQueries(),
        fetchHealthCheck(),
      ]);
    } catch (err: any) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async () => {
    try {
      const res = await api.get('/api/v1/database/performance');
      const data = res.data;
      setPerformance(data);

      // Update history (keep last 30 data points)
      setPerformanceHistory(prev => ({
        cpu: [...prev.cpu.slice(-29), data.cpu_usage],
        memory: [...prev.memory.slice(-29), data.memory_usage],
        disk_io: [...prev.disk_io.slice(-29), data.disk_io],
        network_io: [...prev.network_io.slice(-29), data.network_io],
        query_latency: [...prev.query_latency.slice(-29), data.query_latency],
        connections: [...prev.connections.slice(-29), data.connection_count],
      }));
    } catch (err: any) {
      console.error('Error fetching performance:', err);
    }
  };

  const fetchQueries = async () => {
    try {
      const res = await api.get('/api/v1/database/queries?limit=10&slow_only=false');
      setQueries(res.data || []);
    } catch (err: any) {
      console.error('Error fetching queries:', err);
    }
  };

  const fetchSlowQueries = async () => {
    try {
      const res = await api.get('/api/v1/database/queries?limit=10&slow_only=true');
      setSlowQueries(res.data || []);
    } catch (err: any) {
      console.error('Error fetching slow queries:', err);
    }
  };

  const fetchHealthCheck = async () => {
    try {
      // Simulate health check based on performance metrics
      const res = await api.get('/api/v1/database/performance');
      const data = res.data;

      const checks = [
        {
          name: 'CPU Usage',
          status: data.cpu_usage > 80 ? 'fail' : data.cpu_usage > 60 ? 'warning' : 'pass',
          message: `CPU usage is ${data.cpu_usage.toFixed(1)}%`,
          timestamp: new Date().toISOString(),
        },
        {
          name: 'Memory Usage',
          status: data.memory_usage > 85 ? 'fail' : data.memory_usage > 70 ? 'warning' : 'pass',
          message: `Memory usage is ${data.memory_usage.toFixed(1)}%`,
          timestamp: new Date().toISOString(),
        },
        {
          name: 'Query Latency',
          status: data.query_latency > 50 ? 'fail' : data.query_latency > 20 ? 'warning' : 'pass',
          message: `Query latency is ${data.query_latency.toFixed(1)}ms`,
          timestamp: new Date().toISOString(),
        },
        {
          name: 'Connection Pool',
          status: data.connection_count > 200 ? 'fail' : data.connection_count > 150 ? 'warning' : 'pass',
          message: `Active connections: ${data.connection_count}`,
          timestamp: new Date().toISOString(),
        },
        {
          name: 'Disk I/O',
          status: data.disk_io > 200 ? 'fail' : data.disk_io > 150 ? 'warning' : 'pass',
          message: `Disk I/O is ${data.disk_io.toFixed(1)} MB/s`,
          timestamp: new Date().toISOString(),
        },
      ];

      const overallStatus = checks.some(c => c.status === 'fail')
        ? 'critical'
        : checks.some(c => c.status === 'warning')
          ? 'warning'
          : 'healthy';

      setHealthStatus({
        status: overallStatus,
        checks,
      });
    } catch (err: any) {
      console.error('Error fetching health check:', err);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'pass':
        return 'bg-green-500';
      case 'warning':
        return 'bg-yellow-500';
      case 'critical':
      case 'fail':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'pass':
        return <Badge className="bg-green-500">正常</Badge>;
      case 'warning':
        return <Badge className="bg-yellow-500">警告</Badge>;
      case 'critical':
      case 'fail':
        return <Badge className="bg-red-500">严重</Badge>;
      default:
        return <Badge>未知</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchAllData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据库监控</h1>
        <div className="flex items-center gap-4">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5m">5分钟</SelectItem>
              <SelectItem value="1h">1小时</SelectItem>
              <SelectItem value="24h">24小时</SelectItem>
              <SelectItem value="7d">7天</SelectItem>
            </SelectContent>
          </Select>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            自动刷新
          </label>
          <Button onClick={fetchAllData}>刷新</Button>
        </div>
      </div>

      {/* Health Status Banner */}
      {healthStatus && (
        <Card className={getStatusColor(healthStatus.status)}>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-white font-semibold">
                  数据库状态: {healthStatus.status === 'healthy' ? '正常' : healthStatus.status === 'warning' ? '警告' : '严重'}
                </div>
                {getStatusBadge(healthStatus.status)}
              </div>
              <div className="text-white text-sm">
                最后更新: {new Date().toLocaleString()}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">CPU 使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.cpu_usage.toFixed(1)}%</div>
            <div className="text-xs text-gray-500 mt-1">
              {performance?.cpu_usage > 80 ? '⚠️ 高负载' : '✓ 正常'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.memory_usage.toFixed(1)}%</div>
            <div className="text-xs text-gray-500 mt-1">
              {performance?.memory_usage > 85 ? '⚠️ 高负载' : '✓ 正常'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">查询延迟</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.query_latency.toFixed(1)}ms</div>
            <div className="text-xs text-gray-500 mt-1">
              {performance?.query_latency > 50 ? '⚠️ 延迟高' : '✓ 正常'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">活跃连接</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.connection_count}</div>
            <div className="text-xs text-gray-500 mt-1">
              活跃查询: {performance?.active_queries}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <TrendChart
          data={performanceHistory.cpu}
          color="#3b82f6"
          height={180}
          title="CPU 使用率趋势"
        />
        <TrendChart
          data={performanceHistory.memory}
          color="#10b981"
          height={180}
          title="内存使用率趋势"
        />
        <TrendChart
          data={performanceHistory.query_latency}
          color="#f59e0b"
          height={180}
          title="查询延迟趋势"
        />
        <TrendChart
          data={performanceHistory.disk_io}
          color="#8b5cf6"
          height={180}
          title="磁盘 I/O 趋势"
        />
        <TrendChart
          data={performanceHistory.network_io}
          color="#ec4899"
          height={180}
          title="网络 I/O 趋势"
        />
        <TrendChart
          data={performanceHistory.connections}
          color="#06b6d4"
          height={180}
          title="连接数趋势"
        />
      </div>

      {/* Health Check Details */}
      <Card>
        <CardHeader>
          <CardTitle>健康检查详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {healthStatus?.checks.map((check, index) => (
              <div key={index} className="flex items-center justify-between border rounded-lg p-3">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(check.status)}`} />
                  <div>
                    <div className="font-medium">{check.name}</div>
                    <div className="text-sm text-gray-500">{check.message}</div>
                  </div>
                </div>
                {getStatusBadge(check.status)}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Slow Queries */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>慢查询监控</CardTitle>
            <Badge variant="destructive">{slowQueries.length} 个慢查询</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {slowQueries.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无慢查询</div>
          ) : (
            <div className="space-y-3">
              {slowQueries.map((query) => (
                <div key={query.query_id} className="border rounded-lg p-4 bg-red-50">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="destructive">慢查询</Badge>
                    <div className="text-sm text-gray-500">
                      执行次数: {query.execution_count} | 平均耗时: {query.avg_duration_ms.toFixed(1)}ms
                    </div>
                  </div>
                  <div className="font-mono text-sm bg-white p-2 rounded mb-2">
                    {query.query_text}
                  </div>
                  <div className="text-sm text-gray-500">
                    数据库: {query.database} | 表: {query.table_name}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Queries */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>最近查询</CardTitle>
            <Button onClick={fetchQueries} size="sm">刷新</Button>
          </div>
        </CardHeader>
        <CardContent>
          {queries.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无查询记录</div>
          ) : (
            <div className="space-y-3">
              {queries.map((query) => (
                <div key={query.query_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={query.avg_duration_ms > 100 ? 'destructive' : 'default'}>
                      {query.avg_duration_ms > 100 ? '慢查询' : '正常'}
                    </Badge>
                    <div className="text-sm text-gray-500">
                      执行次数: {query.execution_count} | 平均耗时: {query.avg_duration_ms.toFixed(1)}ms
                    </div>
                  </div>
                  <div className="font-mono text-sm bg-gray-50 p-2 rounded mb-2">
                    {query.query_text}
                  </div>
                  <div className="text-sm text-gray-500">
                    数据库: {query.database} | 表: {query.table_name} | 最后执行: {new Date(query.last_executed).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
