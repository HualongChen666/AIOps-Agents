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

interface GitOpsRepository {
  id: string;
  name: string;
  url: string;
  branch: string;
  path: string;
  syncInterval: number;
  status: 'synced' | 'out_of_sync' | 'error' | 'syncing';
  lastSync?: string;
  lastCommit?: string;
  autoSync: boolean;
  prune: boolean;
  selfHeal: boolean;
  createdAt: string;
}

interface GitOpsStats {
  totalRepos: number;
  syncedRepos: number;
  outOfSyncRepos: number;
  errorRepos: number;
  totalSyncs: number;
}

export default function GitOpsPage() {
  const [repos, setRepos] = useState<GitOpsRepository[]>([]);
  const [stats, setStats] = useState<GitOpsStats>({
    totalRepos: 0,
    syncedRepos: 0,
    outOfSyncRepos: 0,
    errorRepos: 0,
    totalSyncs: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRepo, setEditingRepo] = useState<GitOpsRepository | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    branch: 'main',
    path: './',
    syncInterval: 60,
    autoSync: true,
    prune: false,
    selfHeal: true,
  });

  const loadRepos = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<{ repos: GitOpsRepository[]; stats: GitOpsStats }>('/api/v1/gitops');
      setRepos(response.data?.repos || []);
      setStats(response.data?.stats || stats);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载仓库失败');
      console.error('加载仓库失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepos();
    const interval = setInterval(loadRepos, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = () => {
    setEditingRepo(null);
    setFormData({
      name: '',
      url: '',
      branch: 'main',
      path: './',
      syncInterval: 60,
      autoSync: true,
      prune: false,
      selfHeal: true,
    });
    setDialogOpen(true);
  };

  const handleEdit = (repo: GitOpsRepository) => {
    setEditingRepo(repo);
    setFormData({
      name: repo.name,
      url: repo.url,
      branch: repo.branch,
      path: repo.path,
      syncInterval: repo.syncInterval,
      autoSync: repo.autoSync,
      prune: repo.prune,
      selfHeal: repo.selfHeal,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingRepo) {
        await api.put(`/api/v1/gitops/${editingRepo.id}`, formData);
      } else {
        await api.post('/api/v1/gitops', formData);
      }
      setDialogOpen(false);
      await loadRepos();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个仓库吗？')) return;
    try {
      await api.delete(`/api/v1/gitops/${id}`);
      await loadRepos();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleSync = async (id: string) => {
    try {
      await api.post(`/api/v1/gitops/${id}/sync`);
      await loadRepos();
    } catch (err: any) {
      setError(err.response?.data?.message || '同步失败');
      console.error('同步失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      synced: 'default',
      out_of_sync: 'destructive',
      error: 'destructive',
      syncing: 'outline',
    };
    const labels: Record<string, string> = {
      synced: '已同步',
      out_of_sync: '未同步',
      error: '错误',
      syncing: '同步中',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">GitOps管理</h1>
          <p className="text-gray-600 mt-1">通过Git实现基础设施和应用的持续部署</p>
        </div>
        <Button onClick={handleCreate}>添加仓库</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总仓库</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalRepos}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已同步</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.syncedRepos}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">未同步</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{stats.outOfSyncRepos}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">错误</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-orange-600">{stats.errorRepos}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总同步次数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalSyncs}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>GitOps仓库</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : repos.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无仓库</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>仓库URL</TableHead>
                  <TableHead>分支</TableHead>
                  <TableHead>路径</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>同步间隔</TableHead>
                  <TableHead>自动同步</TableHead>
                  <TableHead>最后同步</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {repos.map((repo) => (
                  <TableRow key={repo.id}>
                    <TableCell className="font-medium">{repo.name}</TableCell>
                    <TableCell className="font-mono text-sm max-w-xs truncate">{repo.url}</TableCell>
                    <TableCell className="text-gray-600">{repo.branch}</TableCell>
                    <TableCell className="text-gray-600">{repo.path}</TableCell>
                    <TableCell>{getStatusBadge(repo.status)}</TableCell>
                    <TableCell className="text-gray-600">{repo.syncInterval}s</TableCell>
                    <TableCell>
                      <Badge variant={repo.autoSync ? 'default' : 'secondary'}>
                        {repo.autoSync ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {repo.lastSync ? new Date(repo.lastSync).toLocaleString('zh-CN') : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(repo)}
                        >
                          编辑
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleSync(repo.id)}
                          disabled={repo.status === 'syncing'}
                        >
                          同步
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(repo.id)}
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
            <DialogTitle>{editingRepo ? '编辑仓库' : '添加仓库'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入仓库名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">仓库URL</label>
              <Input
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
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
              <label className="block text-sm font-medium mb-1">路径</label>
              <Input
                value={formData.path}
                onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                placeholder="./"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">同步间隔（秒）</label>
              <Input
                type="number"
                value={formData.syncInterval}
                onChange={(e) => setFormData({ ...formData, syncInterval: parseInt(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.autoSync}
                  onChange={(e) => setFormData({ ...formData, autoSync: e.target.checked })}
                />
                <span className="text-sm">自动同步</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.prune}
                  onChange={(e) => setFormData({ ...formData, prune: e.target.checked })}
                />
                <span className="text-sm">自动清理（Prune）</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.selfHeal}
                  onChange={(e) => setFormData({ ...formData, selfHeal: e.target.checked })}
                />
                <span className="text-sm">自愈（Self Heal）</span>
              </label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name || !formData.url}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
