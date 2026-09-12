'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface OptimizationTask {
  task_id: string;
  task_name: string;
  optimization_type: string;
  status: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  progress: number;
  result?: Record<string, unknown> | null;
  error_message?: string | null;
}

interface DatabaseStatistics {
  table_name: string;
  row_count: number;
  table_size_mb: number;
  index_count: number;
  index_size_mb: number;
  last_analyzed: string;
  vacuum_status: string;
  bloat_percentage: number;
}

interface PerformanceSummary {
  total_queries_analyzed: number;
  slow_queries: number;
  index_recommendations: number;
  optimization_tasks: number;
  tables_monitored: number;
  last_analysis: string | null;
  performance_score: number;
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  completed: 'default',
  running: 'secondary',
  pending: 'secondary',
  failed: 'destructive',
};

export default function OptimizationManagerPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<OptimizationTask[]>([]);
  const [stats, setStats] = useState<DatabaseStatistics[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [executing, setExecuting] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({ task_name: '', optimization_type: 'query' });
  const [creating, setCreating] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [tasksRes, statsRes, summaryRes] = await Promise.all([
        api.get('/api/v1/database-optimization/optimization-tasks'),
        api.get('/api/v1/database-optimization/database-statistics'),
        api.get('/api/v1/database-optimization/performance-summary'),
      ]);
      setTasks(Object.values(tasksRes.data || {}));
      setStats(Object.values(statsRes.data || {}));
      setSummary(summaryRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const createTask = async () => {
    if (!newTask.task_name.trim()) {
      toast.error('请填写任务名称');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/database-optimization/optimization-tasks', {
        task_id: `task_${crypto.randomUUID()}`,
        task_name: newTask.task_name,
        optimization_type: newTask.optimization_type,
        status: 'pending',
        progress: 0,
      });
      toast.success('优化任务已创建');
      setNewTask({ task_name: '', optimization_type: 'query' });
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建任务失败');
    } finally {
      setCreating(false);
    }
  };

  const executeTask = async (taskId: string) => {
    try {
      setExecuting(taskId);
      await api.post(`/api/v1/database-optimization/optimization-tasks/${taskId}/execute`);
      toast.success('任务已执行');
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '执行任务失败');
    } finally {
      setExecuting(null);
    }
  };

  const analyzeTable = async (tableName: string) => {
    try {
      await api.post(`/api/v1/database-optimization/database-statistics/${tableName}/analyze`);
      toast.success(`已分析 ${tableName}`);
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '分析失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchAll} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">优化管理器</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">性能评分</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary.performance_score}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">已分析查询</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary.total_queries_analyzed}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">慢查询</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{summary.slow_queries}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">索引建议</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary.index_recommendations}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">优化任务</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary.optimization_tasks}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">监控表</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary.tables_monitored}</div></CardContent></Card>
        </div>
      )}

      <Tabs defaultValue="tasks" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tasks">优化任务</TabsTrigger>
          <TabsTrigger value="tables">表统计</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-4">
          <Card>
            <CardHeader><CardTitle>新建优化任务</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap items-end gap-4">
              <div className="flex-1 min-w-[200px]">
                <Label htmlFor="task-name">任务名称</Label>
                <Input
                  id="task-name"
                  value={newTask.task_name}
                  onChange={(e) => setNewTask({ ...newTask, task_name: e.target.value })}
                  placeholder="例如：清理 users 表膨胀"
                  className="mt-1"
                />
              </div>
              <div className="w-48">
                <Label>优化类型</Label>
                <Select
                  value={newTask.optimization_type}
                  onValueChange={(v) => setNewTask({ ...newTask, optimization_type: v })}
                >
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="query">查询</SelectItem>
                    <SelectItem value="index">索引</SelectItem>
                    <SelectItem value="schema">表结构</SelectItem>
                    <SelectItem value="configuration">配置</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={createTask} disabled={creating}>{creating ? '创建中...' : '创建任务'}</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>任务列表</CardTitle></CardHeader>
            <CardContent>
              {tasks.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无优化任务</div>
              ) : (
                <div className="space-y-3">
                  {tasks.map((task) => (
                    <div key={task.task_id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-semibold">{task.task_name}</div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">{task.optimization_type}</Badge>
                          <Badge variant={STATUS_VARIANT[task.status] ?? 'secondary'}>{task.status}</Badge>
                          <Button
                            size="sm"
                            onClick={() => executeTask(task.task_id)}
                            disabled={executing === task.task_id}
                          >
                            {executing === task.task_id ? '执行中...' : '执行'}
                          </Button>
                        </div>
                      </div>
                      <div className="w-full bg-gray-100 rounded h-2">
                        <div className="bg-blue-500 h-2 rounded" style={{ width: `${Math.min(100, task.progress || 0)}%` }} />
                      </div>
                      {task.error_message && <div className="text-sm text-red-600 mt-2">{task.error_message}</div>}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tables">
          <Card>
            <CardHeader><CardTitle>数据库表统计（实时采集）</CardTitle></CardHeader>
            <CardContent>
              {stats.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂未采集统计信息，点击刷新获取</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-gray-600">
                        <th className="py-2">表名</th>
                        <th className="py-2">行数</th>
                        <th className="py-2">大小 (MB)</th>
                        <th className="py-2">索引数</th>
                        <th className="py-2">膨胀率</th>
                        <th className="py-2">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.map((s) => (
                        <tr key={s.table_name} className="border-b">
                          <td className="py-2 font-mono">{s.table_name}</td>
                          <td className="py-2">{s.row_count.toLocaleString()}</td>
                          <td className="py-2">{s.table_size_mb.toFixed(2)}</td>
                          <td className="py-2">{s.index_count}</td>
                          <td className="py-2">{s.bloat_percentage.toFixed(1)}%</td>
                          <td className="py-2">
                            <Button size="sm" variant="secondary" onClick={() => analyzeTable(s.table_name)}>分析</Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
