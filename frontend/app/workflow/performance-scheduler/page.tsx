'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface PerformanceRule {
  id: string;
  name: string;
  description: string;
  metric: string;
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  threshold: number;
  action: 'scale_up' | 'scale_down' | 'alert' | 'restart';
  cooldown: number;
  enabled: boolean;
  triggeredCount: number;
  lastTriggered?: string;
  createdAt: string;
}

interface PerformanceMetrics {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkIn: number;
  networkOut: number;
  activeWorkflows: number;
  queueSize: number;
}

export default function PerformanceSchedulerPage() {
  const [rules, setRules] = useState<PerformanceRule[]>([]);
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    cpuUsage: 0,
    memoryUsage: 0,
    diskUsage: 0,
    networkIn: 0,
    networkOut: 0,
    activeWorkflows: 0,
    queueSize: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<PerformanceRule | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    metric: 'cpuUsage',
    operator: 'gt' as const,
    threshold: 80,
    action: 'scale_up' as const,
    cooldown: 300,
  });

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<PerformanceRule[]>('/api/v1/performance-scheduler/rules');
      setRules(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载规则失败');
      console.error('加载规则失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      const response = await api.get<PerformanceMetrics>('/api/v1/performance-scheduler/metrics');
      setMetrics(response.data || metrics);
    } catch (err: any) {
      console.error('加载指标失败:', err);
    }
  };

  useEffect(() => {
    loadRules();
    loadMetrics();
    const interval = setInterval(() => {
      loadMetrics();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = () => {
    setEditingRule(null);
    setFormData({
      name: '',
      description: '',
      metric: 'cpuUsage',
      operator: 'gt',
      threshold: 80,
      action: 'scale_up',
      cooldown: 300,
    });
    setDialogOpen(true);
  };

  const handleEdit = (rule: PerformanceRule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description,
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold,
      action: rule.action,
      cooldown: rule.cooldown,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingRule) {
        await api.put(`/api/v1/performance-scheduler/rules/${editingRule.id}`, formData);
      } else {
        await api.post('/api/v1/performance-scheduler/rules', formData);
      }
      setDialogOpen(false);
      await loadRules();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个规则吗？')) return;
    try {
      await api.delete(`/api/v1/performance-scheduler/rules/${id}`);
      await loadRules();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/performance-scheduler/rules/${id}/toggle`, { enabled });
      await loadRules();
    } catch (err: any) {
      setError(err.response?.data?.message || '切换状态失败');
      console.error('切换状态失败:', err);
    }
  };

  const getOperatorLabel = (op: string) => {
    const labels: Record<string, string> = {
      gt: '大于',
      lt: '小于',
      eq: '等于',
      gte: '大于等于',
      lte: '小于等于',
    };
    return labels[op] || op;
  };

  const getActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      scale_up: '扩容',
      scale_down: '缩容',
      alert: '告警',
      restart: '重启',
    };
    return labels[action] || action;
  };

  const getMetricLabel = (metric: string) => {
    const labels: Record<string, string> = {
      cpuUsage: 'CPU使用率',
      memoryUsage: '内存使用率',
      diskUsage: '磁盘使用率',
      networkIn: '网络入流量',
      networkOut: '网络出流量',
      activeWorkflows: '活跃工作流',
      queueSize: '队列大小',
    };
    return labels[metric] || metric;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">性能调度器</h1>
          <p className="text-gray-600 mt-1">基于性能指标的自动调度和扩缩容</p>
        </div>
        <Button onClick={handleCreate}>创建规则</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">CPU使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.cpuUsage}%</div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${metrics.cpuUsage}%` }}
              />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">内存使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.memoryUsage}%</div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{ width: `${metrics.memoryUsage}%` }}
              />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">活跃工作流</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.activeWorkflows}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">队列大小</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics.queueSize}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>性能规则</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : rules.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无性能规则</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>规则名称</TableHead>
                  <TableHead>指标</TableHead>
                  <TableHead>条件</TableHead>
                  <TableHead>阈值</TableHead>
                  <TableHead>动作</TableHead>
                  <TableHead>冷却时间</TableHead>
                  <TableHead>触发次数</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>{getMetricLabel(rule.metric)}</TableCell>
                    <TableCell>{getOperatorLabel(rule.operator)}</TableCell>
                    <TableCell className="font-mono">{rule.threshold}</TableCell>
                    <TableCell>{getActionLabel(rule.action)}</TableCell>
                    <TableCell>{rule.cooldown}s</TableCell>
                    <TableCell>{rule.triggeredCount}</TableCell>
                    <TableCell>
                      <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                        {rule.enabled ? '已启用' : '已禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(rule)}
                        >
                          编辑
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggle(rule.id, !rule.enabled)}
                        >
                          {rule.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(rule.id)}
                        >
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingRule ? '编辑规则' : '创建规则'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">规则名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入规则名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入规则描述"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">监控指标</label>
              <select
                value={formData.metric}
                onChange={(e) => setFormData({ ...formData, metric: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="cpuUsage">CPU使用率</option>
                <option value="memoryUsage">内存使用率</option>
                <option value="diskUsage">磁盘使用率</option>
                <option value="networkIn">网络入流量</option>
                <option value="networkOut">网络出流量</option>
                <option value="activeWorkflows">活跃工作流</option>
                <option value="queueSize">队列大小</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">操作符</label>
                <select
                  value={formData.operator}
                  onChange={(e) => setFormData({ ...formData, operator: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="gt">大于</option>
                  <option value="lt">小于</option>
                  <option value="eq">等于</option>
                  <option value="gte">大于等于</option>
                  <option value="lte">小于等于</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">阈值</label>
                <Input
                  type="number"
                  value={formData.threshold}
                  onChange={(e) => setFormData({ ...formData, threshold: parseFloat(e.target.value) })}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">触发动作</label>
              <select
                value={formData.action}
                onChange={(e) => setFormData({ ...formData, action: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="scale_up">扩容</option>
                <option value="scale_down">缩容</option>
                <option value="alert">告警</option>
                <option value="restart">重启</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">冷却时间（秒）</label>
              <Input
                type="number"
                value={formData.cooldown}
                onChange={(e) => setFormData({ ...formData, cooldown: parseInt(e.target.value) })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
