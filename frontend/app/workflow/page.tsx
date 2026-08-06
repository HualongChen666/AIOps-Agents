'use client'

import React, { useEffect, useRef, useState } from 'react';
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

interface WorkflowStep {
  key: string;
  title: string;
  desc: string;
}

interface Workflow {
  name: string;
  description?: string;
  steps: WorkflowStep[];
  time?: string;
  rate?: string;
  nodes?: number;
}

const emptyStep = (): WorkflowStep => ({ key: '', title: '', desc: '' });

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:3000';

function getInternalKey(): string {
  if (typeof window === 'undefined') return '';
  return process.env.NEXT_PUBLIC_INTERNAL_API_KEY || localStorage.getItem('internal_key') || '';
}

export default function WorkflowPage() {
  const [workflows, setWorkflows] = useState<Record<string, Workflow>>({});
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [form, setForm] = useState<{
    wf_key: string;
    name: string;
    description: string;
    time: string;
    rate: string;
    steps: WorkflowStep[];
  }>({
    wf_key: '',
    name: '',
    description: '',
    time: 'N/A',
    rate: 'N/A',
    steps: [emptyStep()],
  });

  const [runningKey, setRunningKey] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadWorkflows = async () => {
    setLoading(true);
    try {
      const resp = await api.get<Record<string, Workflow>>('/api/v1/workflows/definitions');
      const data = resp.data ?? {};
      setWorkflows(data);
      if (selectedKey && !data[selectedKey]) {
        setSelectedKey(null);
      }
    } catch (err) {
      console.error('加载工作流失败', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflows();
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const openCreate = () => {
    setEditingKey(null);
    setForm({
      wf_key: '',
      name: '',
      description: '',
      time: 'N/A',
      rate: 'N/A',
      steps: [emptyStep()],
    });
    setDialogOpen(true);
  };

  const openEdit = (key: string) => {
    const wf = workflows[key];
    if (!wf) return;
    setEditingKey(key);
    setForm({
      wf_key: key,
      name: wf.name || '',
      description: wf.description || '',
      time: wf.time || 'N/A',
      rate: wf.rate || 'N/A',
      steps: wf.steps?.length ? wf.steps.map((s) => ({ ...s })) : [emptyStep()],
    });
    setDialogOpen(true);
  };

  const saveWorkflow = async () => {
    const payload = {
      name: form.name,
      description: form.description,
      steps: form.steps.filter((s) => s.key.trim() && s.title.trim()),
      time: form.time,
      rate: form.rate,
    };
    try {
      if (editingKey) {
        await api.put(`/api/v1/workflows/definitions/${editingKey}`, payload);
      } else {
        await api.post('/api/v1/workflows/definitions', { wf_key: form.wf_key, ...payload });
      }
      setDialogOpen(false);
      await loadWorkflows();
    } catch (err) {
      console.error('保存工作流失败', err);
    }
  };

  const deleteWorkflow = async (key: string) => {
    if (!window.confirm(`确定删除工作流 ${key} 吗？`)) return;
    try {
      await api.delete(`/api/v1/workflows/definitions/${key}`);
      if (selectedKey === key) setSelectedKey(null);
      await loadWorkflows();
    } catch (err) {
      console.error('删除工作流失败', err);
    }
  };

  const runWorkflow = async (key: string) => {
    if (runningKey) return;
    setRunningKey(key);
    setLogs([]);
    setActiveNode(null);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${API_BASE}/api/v1/workflows/simulate/${key}`, {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          'X-Internal-Key': getInternalKey(),
        } as Record<string, string>,
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        setLogs((prev) => [...prev, `[ERROR] 启动失败: HTTP ${resp.status}`]);
        setRunningKey(null);
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          const dataLine = part.split('\n').find((line) => line.startsWith('data:'));
          if (!dataLine) continue;
          const json = dataLine.slice(5).trim();
          try {
            const event = JSON.parse(json);
            if (event.log) {
              setLogs((prev) => [...prev, event.log]);
            }
            if (event.type === 'step_start' && event.node_key) {
              setActiveNode(event.node_key);
            } else if (event.type === 'workflow_done') {
              setActiveNode(null);
            }
          } catch {
            setLogs((prev) => [...prev, json]);
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setLogs((prev) => [...prev, `[ERROR] ${err.message || '执行异常'}`]);
      }
    } finally {
      setRunningKey(null);
      abortRef.current = null;
    }
  };

  const updateStep = (idx: number, field: keyof WorkflowStep, value: string) => {
    setForm((prev) => {
      const steps = [...prev.steps];
      steps[idx] = { ...steps[idx], [field]: value };
      return { ...prev, steps };
    });
  };

  const removeStep = (idx: number) => {
    setForm((prev) => ({ ...prev, steps: prev.steps.filter((_, i) => i !== idx) }));
  };

  const addStep = () => {
    setForm((prev) => ({ ...prev, steps: [...prev.steps, emptyStep()] }));
  };

  const selected = selectedKey ? workflows[selectedKey] : null;

  return (
    <main className="h-[calc(100vh-4rem)] p-6 space-y-6 bg-gray-100 overflow-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">工作流</h1>
        <Button onClick={openCreate}>创建工作流</Button>
      </div>

      {loading && <p className="text-gray-600">加载中…</p>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">工作流列表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(workflows).map(([key, wf]) => (
                <div
                  key={key}
                  onClick={() => setSelectedKey(key)}
                  className={`p-4 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${selectedKey === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{wf.name}</span>
                    <Badge variant="outline">{key}</Badge>
                  </div>
                  <div className="text-xs text-gray-500 mb-2">
                    节点 {wf.steps?.length || 0} · {wf.time || 'N/A'} · {wf.rate || 'N/A'}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); openEdit(key); }}>
                      编辑
                    </Button>
                    <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); deleteWorkflow(key); }}>
                      删除
                    </Button>
                    <Button
                      size="sm"
                      disabled={runningKey === key}
                      onClick={(e) => { e.stopPropagation(); runWorkflow(key); }}
                    >
                      {runningKey === key ? '运行中' : '运行'}
                    </Button>
                  </div>
                </div>
              ))}
              {Object.keys(workflows).length === 0 && !loading && (
                <div className="text-sm text-gray-500">暂无工作流</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">
              {selected ? selected.name : '工作流详情'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selected ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">KEY</span>
                    <div className="font-mono">{selectedKey}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">节点数</span>
                    <div>{selected.steps?.length || 0}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">耗时</span>
                    <div>{selected.time || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">成功率</span>
                    <div>{selected.rate || 'N/A'}</div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium mb-2">节点定义</h3>
                  <div className="space-y-2">
                    {(selected.steps || []).map((step, i) => (
                      <div
                        key={`${step.key}-${i}`}
                        className={`p-3 border rounded-md flex items-center justify-between ${activeNode === step.key ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                          }`}
                      >
                        <div>
                          <div className="font-medium">{step.title}</div>
                          <div className="text-xs text-gray-500 font-mono">{step.key}</div>
                          <div className="text-xs text-gray-500">{step.desc}</div>
                        </div>
                        {activeNode === step.key && <Badge>执行中</Badge>}
                      </div>
                    ))}
                  </div>
                </div>

                {logs.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">执行日志</h3>
                    <div className="h-48 overflow-auto rounded-md bg-gray-900 text-gray-100 p-3 text-xs font-mono space-y-1">
                      {logs.map((log, i) => (
                        <div key={i}>{log}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                请选择或创建一个工作流
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>{editingKey ? '编辑工作流' : '创建工作流'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">唯一标识 (wf_key)</label>
              <Input
                value={form.wf_key}
                disabled={!!editingKey}
                onChange={(e) => setForm((p) => ({ ...p, wf_key: e.target.value }))}
                placeholder="data-collection"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="数据采集与摄入"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                placeholder="工作流用途说明"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">平均耗时展示</label>
                <Input
                  value={form.time}
                  onChange={(e) => setForm((p) => ({ ...p, time: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">成功率展示</label>
                <Input
                  value={form.rate}
                  onChange={(e) => setForm((p) => ({ ...p, rate: e.target.value }))}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium">节点</label>
                <Button variant="outline" size="sm" type="button" onClick={addStep}>
                  添加节点
                </Button>
              </div>
              <div className="space-y-3">
                {form.steps.map((step, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 items-end border p-3 rounded-md">
                    <div className="col-span-3">
                      <Input
                        value={step.key}
                        onChange={(e) => updateStep(idx, 'key', e.target.value)}
                        placeholder="key"
                      />
                    </div>
                    <div className="col-span-4">
                      <Input
                        value={step.title}
                        onChange={(e) => updateStep(idx, 'title', e.target.value)}
                        placeholder="标题"
                      />
                    </div>
                    <div className="col-span-4">
                      <Input
                        value={step.desc}
                        onChange={(e) => updateStep(idx, 'desc', e.target.value)}
                        placeholder="描述"
                      />
                    </div>
                    <div className="col-span-1">
                      <Button variant="destructive" size="sm" type="button" onClick={() => removeStep(idx)}>
                        删
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={saveWorkflow} disabled={!form.name || !form.wf_key}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
