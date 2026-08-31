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

interface DatabaseBackup {
  backup_id: string;
  database_name: string;
  backup_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

interface DatabaseMigration {
  migration_id: string;
  version: string;
  name: string;
  description: string;
  status: string;
  applied_at?: string;
  rollback_script?: string;
}

export default function DatabaseAdvancedPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Performance data
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [performanceHistory, setPerformanceHistory] = useState<number[]>([]);

  // Optimizations
  const [optimizations, setOptimizations] = useState<DatabaseOptimization[]>([]);
  const [optimizing, setOptimizing] = useState(false);

  // Queries
  const [queries, setQueries] = useState<DatabaseQuery[]>([]);
  const [slowOnly, setSlowOnly] = useState(false);

  // Indexes
  const [indexes, setIndexes] = useState<DatabaseIndex[]>([]);
  const [newIndex, setNewIndex] = useState({ index_name: '', table_name: '', columns: '', index_type: 'btree', is_unique: false });

  // Backups
  const [backups, setBackups] = useState<DatabaseBackup[]>([]);
  const [newBackup, setNewBackup] = useState({ database_name: '', backup_type: 'full', compression: true });

  // Migrations
  const [migrations, setMigrations] = useState<DatabaseMigration[]>([]);
  const [newMigration, setNewMigration] = useState({ version: '', name: '', description: '', up_script: '', down_script: '' });

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(() => {
      fetchPerformance();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchPerformance(),
        fetchOptimizations(),
        fetchQueries(),
        fetchIndexes(),
        fetchBackups(),
        fetchMigrations(),
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
      setPerformanceHistory(prev => [...prev.slice(-23), res.data.cpu_usage]);
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
      const res = await api.get(`/api/v1/database/queries?limit=20&slow_only=${slowOnly}`);
      setQueries(res.data || []);
    } catch (err: any) {
      console.error('Error fetching queries:', err);
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

  const fetchBackups = async () => {
    try {
      const res = await api.get('/api/v1/database/backups');
      setBackups(res.data || []);
    } catch (err: any) {
      console.error('Error fetching backups:', err);
    }
  };

  const fetchMigrations = async () => {
    try {
      const res = await api.get('/api/v1/database/migrations');
      setMigrations(res.data || []);
    } catch (err: any) {
      console.error('Error fetching migrations:', err);
    }
  };

  const runOptimization = async () => {
    try {
      setOptimizing(true);
      const res = await api.post('/api/v1/database/optimization', {
        enable_query_optimization: true,
        enable_connection_optimization: true,
        enable_cache_optimization: true,
      });
      toast.success('优化任务已启动');
      await fetchOptimizations();
      await fetchPerformance();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '优化失败');
    } finally {
      setOptimizing(false);
    }
  };

  const createIndex = async () => {
    try {
      await api.post('/api/v1/database/indexes', {
        index_name: newIndex.index_name,
        table_name: newIndex.table_name,
        columns: newIndex.columns.split(',').map(c => c.trim()),
        index_type: newIndex.index_type,
        is_unique: newIndex.is_unique,
      });
      toast.success('索引创建成功');
      setNewIndex({ index_name: '', table_name: '', columns: '', index_type: 'btree', is_unique: false });
      await fetchIndexes();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '索引创建失败');
    }
  };

  const createBackup = async () => {
    try {
      await api.post('/api/v1/database/backups', newBackup);
      toast.success('备份任务已启动');
      setNewBackup({ database_name: '', backup_type: 'full', compression: true });
      await fetchBackups();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '备份创建失败');
    }
  };

  const createMigration = async () => {
    try {
      await api.post('/api/v1/database/migrations', newMigration);
      toast.success('迁移脚本已创建');
      setNewMigration({ version: '', name: '', description: '', up_script: '', down_script: '' });
      await fetchMigrations();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '迁移创建失败');
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
        <h1 className="text-3xl font-bold text-gray-900">高级数据库管理</h1>
        <Button onClick={fetchAllData}>刷新数据</Button>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">CPU 使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.cpu_usage.toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.memory_usage.toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">查询延迟</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.query_latency.toFixed(1)}ms</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">活跃连接</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.connection_count}</div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TrendChart
          data={performanceHistory}
          color="#3b82f6"
          height={200}
          title="CPU 使用率趋势"
        />
        <GaugeChart
          value={performance?.memory_usage || 0}
          title="内存使用率"
          unit="%"
          color="#10b981"
        />
      </div>

      {/* Tabs for different features */}
      <Tabs defaultValue="optimization" className="space-y-4">
        <TabsList>
          <TabsTrigger value="optimization">优化管理</TabsTrigger>
          <TabsTrigger value="queries">查询分析</TabsTrigger>
          <TabsTrigger value="indexes">索引管理</TabsTrigger>
          <TabsTrigger value="backups">备份管理</TabsTrigger>
          <TabsTrigger value="migrations">迁移管理</TabsTrigger>
        </TabsList>

        {/* Optimization Tab */}
        <TabsContent value="optimization" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>数据库优化</CardTitle>
                <Button onClick={runOptimization} disabled={optimizing}>
                  {optimizing ? '优化中...' : '运行优化'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {optimizations.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">暂无优化记录</div>
                ) : (
                  optimizations.map((opt) => (
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
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Queries Tab */}
        <TabsContent value="queries" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>查询分析</CardTitle>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={slowOnly}
                      onChange={(e) => {
                        setSlowOnly(e.target.checked);
                        fetchQueries();
                      }}
                    />
                    仅显示慢查询
                  </label>
                  <Button onClick={fetchQueries} size="sm">刷新</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {queries.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">暂无查询记录</div>
                ) : (
                  queries.map((query) => (
                    <div key={query.query_id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant={query.avg_duration_ms > 100 ? 'destructive' : 'default'}>
                          {query.avg_duration_ms > 100 ? '慢查询' : '正常'}
                        </Badge>
                        <div className="text-sm text-gray-500">
                          执行次数: {query.execution_count}
                        </div>
                      </div>
                      <div className="font-mono text-sm bg-gray-50 p-2 rounded mb-2">
                        {query.query_text}
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">平均耗时:</span> {query.avg_duration_ms.toFixed(1)}ms
                        </div>
                        <div>
                          <span className="text-gray-600">数据库:</span> {query.database}
                        </div>
                        <div>
                          <span className="text-gray-600">表:</span> {query.table_name}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Indexes Tab */}
        <TabsContent value="indexes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>索引管理</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="font-semibold">创建新索引</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>索引名称</Label>
                    <Input
                      value={newIndex.index_name}
                      onChange={(e) => setNewIndex({ ...newIndex, index_name: e.target.value })}
                      placeholder="idx_users_email"
                    />
                  </div>
                  <div>
                    <Label>表名</Label>
                    <Input
                      value={newIndex.table_name}
                      onChange={(e) => setNewIndex({ ...newIndex, table_name: e.target.value })}
                      placeholder="users"
                    />
                  </div>
                  <div>
                    <Label>列名 (逗号分隔)</Label>
                    <Input
                      value={newIndex.columns}
                      onChange={(e) => setNewIndex({ ...newIndex, columns: e.target.value })}
                      placeholder="email,created_at"
                    />
                  </div>
                  <div>
                    <Label>索引类型</Label>
                    <Select
                      value={newIndex.index_type}
                      onValueChange={(value) => setNewIndex({ ...newIndex, index_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="btree">B-Tree</SelectItem>
                        <SelectItem value="hash">Hash</SelectItem>
                        <SelectItem value="gin">GIN</SelectItem>
                        <SelectItem value="gist">GiST</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="unique"
                    checked={newIndex.is_unique}
                    onChange={(e) => setNewIndex({ ...newIndex, is_unique: e.target.checked })}
                  />
                  <Label htmlFor="unique">唯一索引</Label>
                </div>
                <Button onClick={createIndex}>创建索引</Button>
              </div>

              <div className="space-y-4">
                {indexes.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">暂无索引</div>
                ) : (
                  indexes.map((index) => (
                    <div key={index.index_id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold">{index.index_name}</div>
                        <Badge variant={index.is_unique ? 'default' : 'secondary'}>
                          {index.is_unique ? '唯一' : '普通'}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">表:</span> {index.table_name}
                        </div>
                        <div>
                          <span className="text-gray-600">类型:</span> {index.index_type}
                        </div>
                        <div>
                          <span className="text-gray-600">大小:</span> {(index.size_bytes / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                      <div className="mt-2 text-sm">
                        <span className="text-gray-600">列:</span> {index.columns.join(', ')}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Backups Tab */}
        <TabsContent value="backups" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>备份管理</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="font-semibold">创建新备份</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>数据库名称</Label>
                    <Input
                      value={newBackup.database_name}
                      onChange={(e) => setNewBackup({ ...newBackup, database_name: e.target.value })}
                      placeholder="production"
                    />
                  </div>
                  <div>
                    <Label>备份类型</Label>
                    <Select
                      value={newBackup.backup_type}
                      onValueChange={(value) => setNewBackup({ ...newBackup, backup_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="full">完整备份</SelectItem>
                        <SelectItem value="incremental">增量备份</SelectItem>
                        <SelectItem value="differential">差异备份</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="compression"
                    checked={newBackup.compression}
                    onChange={(e) => setNewBackup({ ...newBackup, compression: e.target.checked })}
                  />
                  <Label htmlFor="compression">启用压缩</Label>
                </div>
                <Button onClick={createBackup}>创建备份</Button>
              </div>

              <div className="space-y-4">
                {backups.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">暂无备份</div>
                ) : (
                  backups.map((backup) => (
                    <div key={backup.backup_id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold">{backup.database_name}</div>
                        <Badge variant={backup.status === 'completed' ? 'default' : 'secondary'}>
                          {backup.status}
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">类型:</span> {backup.backup_type}
                        </div>
                        <div>
                          <span className="text-gray-600">大小:</span> {(backup.size_bytes / 1024 / 1024 / 1024).toFixed(2)} GB
                        </div>
                        <div>
                          <span className="text-gray-600">创建时间:</span> {new Date(backup.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Migrations Tab */}
        <TabsContent value="migrations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>迁移管理</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border rounded-lg p-4 space-y-4">
                <h3 className="font-semibold">创建新迁移</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>版本号</Label>
                    <Input
                      value={newMigration.version}
                      onChange={(e) => setNewMigration({ ...newMigration, version: e.target.value })}
                      placeholder="001"
                    />
                  </div>
                  <div>
                    <Label>迁移名称</Label>
                    <Input
                      value={newMigration.name}
                      onChange={(e) => setNewMigration({ ...newMigration, name: e.target.value })}
                      placeholder="create_users_table"
                    />
                  </div>
                </div>
                <div>
                  <Label>描述</Label>
                  <Input
                    value={newMigration.description}
                    onChange={(e) => setNewMigration({ ...newMigration, description: e.target.value })}
                    placeholder="Initial users table creation"
                  />
                </div>
                <div>
                  <Label>Up Script (升级脚本)</Label>
                  <Textarea
                    value={newMigration.up_script}
                    onChange={(e) => setNewMigration({ ...newMigration, up_script: e.target.value })}
                    placeholder="CREATE TABLE users (...);"
                    rows={4}
                  />
                </div>
                <div>
                  <Label>Down Script (回滚脚本)</Label>
                  <Textarea
                    value={newMigration.down_script}
                    onChange={(e) => setNewMigration({ ...newMigration, down_script: e.target.value })}
                    placeholder="DROP TABLE users;"
                    rows={4}
                  />
                </div>
                <Button onClick={createMigration}>创建迁移</Button>
              </div>

              <div className="space-y-4">
                {migrations.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">暂无迁移</div>
                ) : (
                  migrations.map((migration) => (
                    <div key={migration.migration_id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold">{migration.version} - {migration.name}</div>
                        <Badge variant={migration.status === 'applied' ? 'default' : 'secondary'}>
                          {migration.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">{migration.description}</div>
                      {migration.applied_at && (
                        <div className="text-sm text-gray-500">
                          应用时间: {new Date(migration.applied_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
