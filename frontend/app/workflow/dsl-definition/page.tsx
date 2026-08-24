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

interface DSLDefinition {
  id: string;
  name: string;
  version: string;
  description: string;
  language: 'yaml' | 'json' | 'python';
  content: string;
  status: 'draft' | 'published' | 'deprecated';
  createdAt: string;
  updatedAt: string;
  author: string;
}

export default function DSLDefinitionPage() {
  const [definitions, setDefinitions] = useState<DSLDefinition[]>([]);
  const [selectedDef, setSelectedDef] = useState<DSLDefinition | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDef, setEditingDef] = useState<DSLDefinition | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    version: '1.0.0',
    description: '',
    language: 'yaml' as const,
    content: '',
    status: 'draft' as const,
  });

  const loadDefinitions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<DSLDefinition[]>('/api/v1/dsl-definition');
      setDefinitions(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedDef(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载DSL定义失败');
      console.error('加载DSL定义失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDefinitions();
  }, []);

  const handleCreate = () => {
    setEditingDef(null);
    setFormData({
      name: '',
      version: '1.0.0',
      description: '',
      language: 'yaml',
      content: '',
      status: 'draft',
    });
    setDialogOpen(true);
  };

  const handleEdit = (def: DSLDefinition) => {
    setEditingDef(def);
    setFormData({
      name: def.name,
      version: def.version,
      description: def.description,
      language: def.language,
      content: def.content,
      status: def.status,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingDef) {
        await api.put(`/api/v1/dsl-definition/${editingDef.id}`, formData);
      } else {
        await api.post('/api/v1/dsl-definition', formData);
      }
      setDialogOpen(false);
      await loadDefinitions();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个DSL定义吗？')) return;
    try {
      await api.delete(`/api/v1/dsl-definition/${id}`);
      if (selectedDef?.id === id) {
        setSelectedDef(null);
      }
      await loadDefinitions();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleValidate = async () => {
    if (!selectedDef) return;
    try {
      const response = await api.post(`/api/v1/dsl-definition/${selectedDef.id}/validate`);
      alert(response.data?.message || '验证通过');
    } catch (err: any) {
      setError(err.response?.data?.message || '验证失败');
      console.error('验证失败:', err);
    }
  };

  const handlePublish = async () => {
    if (!selectedDef) return;
    try {
      await api.post(`/api/v1/dsl-definition/${selectedDef.id}/publish`);
      await loadDefinitions();
    } catch (err: any) {
      setError(err.response?.data?.message || '发布失败');
      console.error('发布失败:', err);
    }
  };

  const handleExport = async () => {
    if (!selectedDef) return;
    try {
      const response = await api.get(`/api/v1/dsl-definition/${selectedDef.id}/export`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${selectedDef.name}-${selectedDef.version}.${selectedDef.language}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      setError(err.response?.data?.message || '导出失败');
      console.error('导出失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      draft: 'secondary',
      published: 'default',
      deprecated: 'outline',
    };
    const labels: Record<string, string> = {
      draft: '草稿',
      published: '已发布',
      deprecated: '已废弃',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const getLanguageBadge = (language: string) => {
    const colors: Record<string, string> = {
      yaml: 'bg-red-100 text-red-800',
      json: 'bg-blue-100 text-blue-800',
      python: 'bg-green-100 text-green-800',
    };
    return <Badge className={colors[language] || 'bg-gray-100'}>{language}</Badge>;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">DSL定义</h1>
          <p className="text-gray-600 mt-1">定义和管理工作流领域特定语言</p>
        </div>
        <Button onClick={handleCreate}>创建DSL</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>DSL列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : definitions.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无DSL定义</div>
            ) : (
              <div className="space-y-2">
                {definitions.map((def) => (
                  <div
                    key={def.id}
                    onClick={() => setSelectedDef(def)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedDef?.id === def.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{def.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline">{def.version}</Badge>
                      {getLanguageBadge(def.language)}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(def); }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(def.id); }}
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
            <div className="flex items-center justify-between">
              <CardTitle>
                {selectedDef ? selectedDef.name : '选择DSL'}
              </CardTitle>
              {selectedDef && (
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleValidate}>
                    验证
                  </Button>
                  {selectedDef.status === 'draft' && (
                    <Button onClick={handlePublish}>
                      发布
                    </Button>
                  )}
                  <Button variant="outline" onClick={handleExport}>
                    导出
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedDef ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">版本</span>
                    <div className="font-medium">{selectedDef.version}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">语言</span>
                    <div>{getLanguageBadge(selectedDef.language)}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">状态</span>
                    <div>{getStatusBadge(selectedDef.status)}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">作者</span>
                    <div>{selectedDef.author}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">创建时间</span>
                    <div className="text-gray-600">
                      {new Date(selectedDef.createdAt).toLocaleString('zh-CN')}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">更新时间</span>
                    <div className="text-gray-600">
                      {new Date(selectedDef.updatedAt).toLocaleString('zh-CN')}
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium mb-1">描述</h3>
                  <p className="text-gray-600">{selectedDef.description}</p>
                </div>

                <div>
                  <h3 className="text-sm font-medium mb-2">DSL内容</h3>
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-md overflow-auto max-h-96">
                    <pre className="text-sm font-mono whitespace-pre-wrap">
                      {selectedDef.content}
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请从左侧选择一个DSL定义
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>{editingDef ? '编辑DSL' : '创建DSL'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">名称</label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="输入DSL名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">版本</label>
                <Input
                  value={formData.version}
                  onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  placeholder="1.0.0"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入DSL描述"
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">语言</label>
                <select
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="yaml">YAML</option>
                  <option value="json">JSON</option>
                  <option value="python">Python</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">状态</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="draft">草稿</option>
                  <option value="published">已发布</option>
                  <option value="deprecated">已废弃</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">DSL内容</label>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="输入DSL内容"
                rows={12}
                className="font-mono text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name || !formData.content}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
