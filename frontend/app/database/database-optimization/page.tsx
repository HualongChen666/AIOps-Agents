'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TrendChart } from '@/components/charts/TrendChart';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';
import toast from 'react-hot-toast';

// API Response Types
interface DatabaseOptimization {
  optimization_id: string;
  status: string;
  query_optimizations: number;
  connection_optimizations: number;
  cache_optimizations: number;
  performance_improvement: number;
  timestamp: string;
}

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

interface DatabaseIndex {
  index_id: string;
  index_name: string;
  table_name: string;
  columns: string[];
  index_type: string;
  is_unique: boolean;
  size_bytes: number;
  created_at: string;
}

interface OptimizationSuggestion {
  type: 'query' | 'index' | 'cache' | 'connection';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  sql?: string;
  expected_improvement: string;
}

export default function DatabaseOptimizationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Performance data
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [performanceHistory, setPerformanceHistory] = useState({
    before: [] as number[],
    after: [] as number[],
  });

  // Optimizations
  const [optimizations, setOptimizations] = useState<DatabaseOptimization[]>([]);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizationConfig, setOptimizationConfig] = useState({
    enable_query_optimization: true,
    enable_connection_optimization: true,
    enable_cache_optimization: true,
    target_tables: [] as string[],
  });

  // Queries
  const [queries, setQueries] = useState<DatabaseQuery[]>([]);
  const [slowQueries, setSlowQueries] = useState<DatabaseQuery[]>([]);

  // Indexes
  const [indexes, setIndexes] = useState<DatabaseIndex[]>([]);
  const [indexSuggestions, setIndexSuggestions] = useState<OptimizationSuggestion[]>([]);

  // Optimization suggestions
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchPerformance(),
        fetchOptimizations(),
        fetchQueries(),
        fetchSlowQueries(),
        fetchIndexes(),
        generateSuggestions(),
      ]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformance = async () => {
    try {
      const res = await api.get('/api/v1/database/performance');
      setPerformance(res.data);
    } catch (err: any) {
      console.error('Error fetching performance:', err);
    }
  };

  const fetchOptimizations = async () => {
    try {
      const res = await api.get('/api/v1/database/optimization?limit=10');
      setOptimizations(res.data || []);
    } catch (err: any) {
      console.error('Error fetching optimizations:', err);
    }
  };

  const fetchQueries = async () => {
    try {
      const res = await api.get('/api/v1/database/queries?limit=20&slow_only=false');
      setQueries(res.data || []);
    } catch (err: any) {
      console.error('Error fetching queries:', err);
    }
  };

  const fetchSlowQueries = async () => {
    try {
      const res = await api.get('/api/v1/database/queries?limit=20&slow_only=true');
      setSlowQueries(res.data || []);
    } catch (err: any) {
      console.error('Error fetching slow queries:', err);
    }
  };

  const fetchIndexes = async () => {
    try {
      const res = await api.get('/api/v1/database/indexes');
      setIndexes(res.data || []);
    } catch (err: any) {
      console.error('Error fetching indexes:', err);
    }
  };

  const generateSuggestions = async () => {
    // Generate optimization suggestions based on current data
    const suggestions: OptimizationSuggestion[] = [];

    // Query optimization suggestions
    if (slowQueries.length > 0) {
      suggestions.push({
        type: 'query',
        priority: 'high',
        title: '优化慢查询',
        description: `发现 ${slowQueries.length} 个慢查询，建议添加索引或重写查询`,
        expected_improvement: '查询性能提升 30-50%',
      });
    }

    // Index suggestions
    const tablesWithoutIndexes = new Set(queries.map(q => q.table_name));
    indexes.forEach(idx => tablesWithoutIndexes.delete(idx.table_name));

    if (tablesWithoutIndexes.size > 0) {
      suggestions.push({
        type: 'index',
        priority: 'medium',
        title: '添加缺失的索引',
        description: `以下表缺少索引: ${Array.from(tablesWithoutIndexes).join(', ')}`,
        expected_improvement: '查询性能提升 20-40%',
      });
    }

    // Cache optimization
    if (performance && performance.query_latency > 20) {
      suggestions.push({
        type: 'cache',
        priority: 'high',
        title: '启用查询缓存',
        description: '查询延迟较高，建议启用查询缓存以减少重复查询开销',
        expected_improvement: '查询性能提升 40-60%',
      });
    }

    // Connection optimization
    if (performance && performance.connection_count > 150) {
      suggestions.push({
        type: 'connection',
        priority: 'medium',
        title: '优化连接池配置',
        description: '活跃连接数较高，建议调整连接池大小或启用连接复用',
        expected_improvement: '资源使用降低 20-30%',
      });
    }

    setSuggestions(suggestions);
  };

  const runOptimization = async () => {
    try {
      setOptimizing(true);
      const res = await api.post('/api/v1/database/optimization', optimizationConfig);
      toast.success('优化任务已启动');

      // Record performance before optimization
      if (performance) {
        setPerformanceHistory(prev => ({
          before: [...prev.before, performance.query_latency],
          after: prev.after,
        }));
      }

      await fetchOptimizations();
      await fetchPerformance();

      // Record performance after optimization
      setTimeout(async () => {
        await fetchPerformance();
        if (performance) {
          setPerformanceHistory(prev => ({
            before: prev.before,
            after: [...prev.after, performance.query_latency],
          }));
        }
      }, 5000);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '优化失败');
    } finally {
      setOptimizing(false);
    }
  };

  const applySuggestion = async (suggestion: OptimizationSuggestion) => {
    try {
      switch (suggestion.type) {
        case 'query':
          toast.info('请手动优化慢查询');
          break;
        case 'index':
          toast.info('请在索引管理中创建建议的索引');
          break;
        case 'cache':
          setOptimizationConfig(prev => ({ ...prev, enable_cache_optimization: true }));
          toast.success('已启用缓存优化配置');
          break;
        case 'connection':
          setOptimizationConfig(prev => ({ ...prev, enable_connection_optimization: true }));
          toast.success('已启用连接优化配置');
          break;
      }
    } catch (err: any) {
      toast.error('应用建议失败');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'high':
        return <Badge className="bg-red-500">高优先级</Badge>;
      case 'medium':
        return <Badge className="bg-yellow-500">中优先级</Badge>;
      case 'low':
        return <Badge className="bg-green-500">低优先级</Badge>;
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
        <h1 className="text-3xl font-bold text-gray-900">数据库优化</h1>
        <Button onClick={fetchAllData}>刷新数据</Button>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">当前查询延迟</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.query_latency.toFixed(1)}ms</div>
            <div className="text-xs text-gray-500 mt-1">
              {performance?.query_latency > 20 ? '需要优化' : '表现良好'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">慢查询数量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{slowQueries.length}</div>
            <div className="text-xs text-gray-500 mt-1">
              {slowQueries.length > 0 ? '需要优化' : '无慢查询'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">索引数量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{indexes.length}</div>
            <div className="text-xs text-gray-500 mt-1">
              覆盖 {new Set(indexes.map(i => i.table_name)).size} 个表
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">优化次数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optimizations.length}</div>
            <div className="text-xs text-gray-500 mt-1">
              总计提升 {optimizations.reduce((sum, opt) => sum + opt.performance_improvement, 0).toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Comparison Chart */}
      {performanceHistory.before.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>优化前后性能对比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <TrendChart
                data={performanceHistory.before}
                color="#ef4444"
                height={200}
                title="优化前查询延迟"
              />
              <TrendChart
                data={performanceHistory.after.length > 0 ? performanceHistory.after : [performance?.query_latency || 0]}
                color="#10b981"
                height={200}
                title="优化后查询延迟"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs for different optimization areas */}
      <Tabs defaultValue="suggestions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="suggestions">优化建议</TabsTrigger>
          <TabsTrigger value="query">查询优化</TabsTrigger>
          <TabsTrigger value="index">索引优化</TabsTrigger>
          <TabsTrigger value="cache">缓存优化</TabsTrigger>
          <TabsTrigger value="connection">连接优化</TabsTrigger>
        </TabsList>

        {/* Suggestions Tab */}
        <TabsContent value="suggestions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>智能优化建议</CardTitle>
            </CardHeader>
            <CardContent>
              {suggestions.length === 0 ? (
                <div className="text-gray-500 text-center py-8">当前数据库状态良好，暂无优化建议</div>
              ) : (
                <div className="space-y-4">
                  {suggestions.map((suggestion, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          {getPriorityBadge(suggestion.priority)}
                          <div className="font-semibold">{suggestion.title}</div>
                        </div>
                        <Button onClick={() => applySuggestion(suggestion)} size="sm">
                          应用建议
                        </Button>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">{suggestion.description}</div>
                      {suggestion.sql && (
                        <div className="font-mono text-sm bg-gray-50 p-2 rounded mb-2">
                          {suggestion.sql}
                        </div>
                      )}
                      <div className="text-sm text-green-600">
                        预期提升: {suggestion.expected_improvement}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Query Optimization Tab */}
        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>慢查询优化</CardTitle>
            </CardHeader>
            <CardContent>
              {slowQueries.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无慢查询</div>
              ) : (
                <div className="space-y-4">
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
                      <div className="text-sm text-gray-500 mb-2">
                        数据库: {query.database} | 表: {query.table_name}
                      </div>
                      <div className="text-sm text-blue-600">
                        建议: 考虑为 {query.table_name} 表添加索引或重写查询
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Index Optimization Tab */}
        <TabsContent value="index" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>索引优化</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-2">当前索引状态</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">总索引数:</span> {indexes.length}
                    </div>
                    <div>
                      <span className="text-gray-600">覆盖表数:</span> {new Set(indexes.map(i => i.table_name)).size}
                    </div>
                    <div>
                      <span className="text-gray-600">唯一索引:</span> {indexes.filter(i => i.is_unique).length}
                    </div>
                    <div>
                      <span className="text-gray-600">总大小:</span> {(indexes.reduce((sum, i) => sum + i.size_bytes, 0) / 1024 / 1024).toFixed(2)} MB
                    </div>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-2">索引列表</h3>
                  {indexes.length === 0 ? (
                    <div className="text-gray-500 text-center py-4">暂无索引</div>
                  ) : (
                    <div className="space-y-2">
                      {indexes.map((index) => (
                        <div key={index.index_id} className="border rounded p-3">
                          <div className="flex items-center justify-between mb-1">
                            <div className="font-medium">{index.index_name}</div>
                            <Badge variant={index.is_unique ? 'default' : 'secondary'}>
                              {index.is_unique ? '唯一' : '普通'}
                            </Badge>
                          </div>
                          <div className="text-sm text-gray-600">
                            表: {index.table_name} | 类型: {index.index_type} | 列: {index.columns.join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cache Optimization Tab */}
        <TabsContent value="cache" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>缓存优化</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-4">缓存配置</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="cache-query">启用查询缓存</Label>
                    <input
                      type="checkbox"
                      id="cache-query"
                      checked={optimizationConfig.enable_cache_optimization}
                      onChange={(e) => setOptimizationConfig({
                        ...optimizationConfig,
                        enable_cache_optimization: e.target.checked
                      })}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="cache-connection">启用连接缓存</Label>
                    <input
                      type="checkbox"
                      id="cache-connection"
                      checked={optimizationConfig.enable_connection_optimization}
                      onChange={(e) => setOptimizationConfig({
                        ...optimizationConfig,
                        enable_connection_optimization: e.target.checked
                      })}
                    />
                  </div>
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-2">缓存优化建议</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span>为频繁查询的数据启用查询缓存，可减少 40-60% 的数据库负载</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span>配置适当的缓存过期时间，平衡数据一致性和性能</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span>使用 Redis 或 Memcached 作为分布式缓存层</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Connection Optimization Tab */}
        <TabsContent value="connection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>连接优化</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-4">连接池状态</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">活跃连接:</span> {performance?.connection_count || 0}
                  </div>
                  <div>
                    <span className="text-gray-600">活跃查询:</span> {performance?.active_queries || 0}
                  </div>
                </div>
                <GaugeChart
                  value={performance?.connection_count || 0}
                  min={0}
                  max={200}
                  title="连接池使用率"
                  unit=""
                  color={performance?.connection_count > 150 ? '#ef4444' : '#10b981'}
                />
              </div>

              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-4">连接优化配置</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="conn-opt">启用连接优化</Label>
                    <input
                      type="checkbox"
                      id="conn-opt"
                      checked={optimizationConfig.enable_connection_optimization}
                      onChange={(e) => setOptimizationConfig({
                        ...optimizationConfig,
                        enable_connection_optimization: e.target.checked
                      })}
                    />
                  </div>
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-2">连接优化建议</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span>配置适当的连接池大小，避免连接泄漏</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span>启用连接复用，减少连接建立开销</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-500">✓</span>
                    <span>设置连接超时时间，自动回收空闲连接</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Run Optimization Button */}
      <Card>
        <CardHeader>
          <CardTitle>执行优化</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="opt-query"
                  checked={optimizationConfig.enable_query_optimization}
                  onChange={(e) => setOptimizationConfig({
                    ...optimizationConfig,
                    enable_query_optimization: e.target.checked
                  })}
                />
                <Label htmlFor="opt-query">查询优化</Label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="opt-connection"
                  checked={optimizationConfig.enable_connection_optimization}
                  onChange={(e) => setOptimizationConfig({
                    ...optimizationConfig,
                    enable_connection_optimization: e.target.checked
                  })}
                />
                <Label htmlFor="opt-connection">连接优化</Label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="opt-cache"
                  checked={optimizationConfig.enable_cache_optimization}
                  onChange={(e) => setOptimizationConfig({
                    ...optimizationConfig,
                    enable_cache_optimization: e.target.checked
                  })}
                />
                <Label htmlFor="opt-cache">缓存优化</Label>
              </div>
            </div>
            <Button onClick={runOptimization} disabled={optimizing} className="w-full">
              {optimizing ? '优化中...' : '执行优化'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Optimization History */}
      <Card>
        <CardHeader>
          <CardTitle>优化历史</CardTitle>
        </CardHeader>
        <CardContent>
          {optimizations.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无优化记录</div>
          ) : (
            <div className="space-y-4">
              {optimizations.map((opt) => (
                <div key={opt.optimization_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={opt.status === 'completed' ? 'default' : 'secondary'}>
                      {opt.status}
                    </Badge>
                    <div className="text-sm text-gray-500">
                      {new Date(opt.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">查询优化:</span> {opt.query_optimizations}
                    </div>
                    <div>
                      <span className="text-gray-600">连接优化:</span> {opt.connection_optimizations}
                    </div>
                    <div>
                      <span className="text-gray-600">缓存优化:</span> {opt.cache_optimizations}
                    </div>
                  </div>
                  <div className="mt-2 text-sm">
                    <span className="text-gray-600">性能提升:</span> {opt.performance_improvement.toFixed(1)}%
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
