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

interface PipelineStage {
  id: string;
  name: string;
  type: 'build' | 'test' | 'deploy' | 'custom';
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  duration?: number;
  log?: string;
}

interface Pipeline {
  id: string;
  name: string;
  description: string;
  repository: string;
  branch: string;
  status: 'idle' | 'running' | 'success' | 'failed' | 'cancelled';
  trigger: 'manual' | 'push' | 'pr' | 'schedule';
  stages: PipelineStage[];
  commit?: string;
  commitMessage?: string;
  author?: string;
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  createdAt: string;
}

export default function CICDPipelinePage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPipeline, setEditingPipeline] = useState<Pipeline | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    repository: '',
    branch: 'main',
    trigger: 'push' as const,
  });

  const loadPipelines = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<Pipeline[]>('/api/v1/cicd-pipeline');
      setPipelines(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedPipeline(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载管道失败');
      console.error('加载管道失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPipelines();
    const interval = setInterval(() => {
      const hasRunning = pipelines.some(p => p.status === 'running');
      if (hasRunning) {
        loadPipelines();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = () => {
    setEditingPipeline(null);
    setFormData({
      name: '',
      description: '',
      repository: '',
      branch: 'main',
      trigger: 'push',
    });
    setDialogOpen(true);
  };

  const handleEdit = (pipeline: Pipeline) => {
    setEditingPipeline(pipeline);
    setFormData({
      name: pipeline.name,
      description: pipeline.description,
      repository: pipeline.repository,
      branch: pipeline.branch,
      trigger: pipeline.trigger,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingPipeline) {
        await api.put(`/api/v1/cicd-pipeline/${editingPipeline.id}`, formData);
      } else {
        await api.post('/api/v1/cicd-pipeline', formData);
      }
      setDialogOpen(false);
      await loadPipelines();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个管道吗？')) return;
    try {
      await api.delete(`/api/v1/cicd-pipeline/${id}`);
      if (selectedPipeline?.id === id) {
        setSelectedPipeline(null);
      }
      await loadPipelines();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleRun = async (id: string) => {
    try {
      await api.post(`/api/v1/cicd-pipeline/${id}/run`);
      await loadPipelines();
    } catch (err: any) {
      setError(err.response?.data?.message || '运行失败');
      console.error('运行失败:', err);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await api.post(`/api/v1/cicd-pipeline/${id}/cancel`);
      await loadPipelines();
    } catch (err: any) {
      setError(err.response?.data?.message || '取消失败');
      console.error('取消失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      idle: 'secondary',
      running: 'default',
      success: 'default',
      failed: 'destructive',
      cancelled: 'outline',
      pending: 'outline',
      skipped: 'secondary',
    };
    const labels: Record<string, string> = {
      idle: '空闲',
      running: '运行中',
      success: '成功',
      failed: '失败',
      cancelled: '已取消',
      pending: '待执行',
      skipped: '已跳过',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const getTriggerBadge = (trigger: string) => {
    const labels: Record<string, string> = {
      manual: '手动',
      push: '推送',
      pr: 'PR',
      schedule: '定时',
    };
    return <Badge variant="outline">{labels[trigger] || trigger}</Badge>;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">CI/CD管道</h1>
          <p className="text-gray-600 mt-1">配置和管理持续集成和部署管道</p>
        </div>
        <Button onClick={handleCreate}>创建管道</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>管道列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : pipelines.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无管道</div>
            ) : (
              <div className="space-y-2">
                {pipelines.map((pipeline) => (
                  <div
                    key={pipeline.id}
                    onClick={() => setSelectedPipeline(pipeline)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedPipeline?.id === pipeline.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{pipeline.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusBadge(pipeline.status)}
                      {getTriggerBadge(pipeline.trigger)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {pipeline.repository}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(pipeline); }}
                      >
                        编辑
                      </Button>
                      {pipeline.status === 'idle' && (
                        <Button
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); handleRun(pipeline.id); }}
                        >
                          运行
                        </Button>
                      )}
                      {pipeline.status === 'running' && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); handleCancel(pipeline.id); }}
                        >
                          取消
                        </Button>
                      )}
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(pipeline.id); }}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>
              {selectedPipeline ? selectedPipeline.name : '选择管道'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedPipeline ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  {selectedPipeline.description}
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">仓库</span>
                    <div className="font-mono">{selectedPipeline.repository}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">分支</span>
                    <div>{selectedPipeline.branch}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">触发方式</span>
                    <div>{getTriggerBadge(selectedPipeline.trigger)}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">状态</span>
                    <div>{getStatusBadge(selectedPipeline.status)}</div>
                  </div>
                  {selectedPipeline.commit && (
                    <div>
                      <span className="text-gray-500">提交</span>
                      <div className="font-mono text-sm">{selectedPipeline.commit.slice(0, 8)}</div>
                    </div>
                  )}
                  {selectedPipeline.author && (
                    <div>
                      <span className="text-gray-500">作者</span>
                      <div>{selectedPipeline.author}</div>
                    </div>
                  )}
                  {selectedPipeline.startedAt && (
                    <div>
                      <span className="text-gray-500">开始时间</span>
                      <div className="text-gray-600">
                        {new Date(selectedPipeline.startedAt).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  )}
                  {selectedPipeline.duration && (
                    <div>
                      <span className="text-gray-500">耗时</span>
                      <div>{selectedPipeline.duration}s</div>
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-medium mb-2">阶段</h3>
                  <div className="space-y-2">
                    {selectedPipeline.stages.map((stage) => (
                      <div
                        key={stage.id}
                        className="flex items-center justify-between p-3 border rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          {getStatusBadge(stage.status)}
                          <div>
                            <div className="font-medium">{stage.name}</div>
                            <div className="text-xs text-gray-500">{stage.type}</div>
                          </div>
                        </div>
                        <div className="text-sm text-gray-600">
                          {stage.duration ? `${stage.duration}s` : '-'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请从左侧选择一个管道
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingPipeline ? '编辑管道' : '创建管道'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入管道名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入管道描述"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">仓库URL</label>
              <Input
                value={formData.repository}
                onChange={(e) => setFormData({ ...formData, repository: e.target.value })}
                placeholder="https://github.com/user/repo"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">分支</label>
              <Input
                value={formData.branch}
                onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                placeholder="main"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">触发方式</label>
              <select
                value={formData.trigger}
                onChange={(e) => setFormData({ ...formData, trigger: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="push">代码推送</option>
                <option value="pr">Pull Request</option>
                <option value="manual">手动触发</option>
                <option value="schedule">定时触发</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name || !formData.repository}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
