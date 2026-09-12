'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface Scenario {
  id: string;
  name: string;
  description: string | null;
  experiments: string[];
  enabled: boolean;
  schedule: string | null;
  created_at: string | null;
}

export default function ChaosScenariosPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [form, setForm] = useState({ name: '', description: '', experiments: '', schedule: '' });
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [experimentName, setExperimentName] = useState('');

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/chaos/scenarios', { params: { limit: 100 } });
      setScenarios(res.data.data?.items || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载混沌场景失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const createExperimentAndAttach = async () => {
    if (!experimentName.trim()) {
      toast.error('请填写实验名称');
      return;
    }
    try {
      const res = await api.post('/api/v1/chaos/experiments', {
        name: experimentName,
        experiment_type: 'latency_injection',
        parameters: {},
        severity: 'medium',
        tags: [],
      });
      const id = res.data.data?.id;
      if (!id) {
        toast.error('实验创建返回缺少 ID');
        return;
      }
      const existing = form.experiments.split(',').map((s) => s.trim()).filter(Boolean);
      setForm({ ...form, experiments: [...existing, id].join(', ') });
      setExperimentName('');
      toast.success(`实验已创建并加入场景：${id}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建实验失败');
    }
  };

  const createScenario = async () => {
    const experiments = form.experiments.split(',').map((s) => s.trim()).filter(Boolean);
    if (!form.name.trim() || experiments.length === 0) {
      toast.error('请填写场景名称并至少包含 1 个实验 ID');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/chaos/scenarios', {
        name: form.name,
        description: form.description || null,
        experiments,
        enabled: true,
        schedule: form.schedule || null,
      });
      toast.success('场景创建成功');
      setForm({ name: '', description: '', experiments: '', schedule: '' });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建场景失败');
    } finally {
      setCreating(false);
    }
  };

  const runScenario = async (id: string) => {
    try {
      setBusyId(id);
      const res = await api.post(`/api/v1/chaos/scenarios/${id}/run`);
      toast.success(`场景已执行：${JSON.stringify(res.data.data ?? {}).slice(0, 80)}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '执行场景失败');
    } finally {
      setBusyId(null);
    }
  };

  const deleteScenario = async (id: string) => {
    try {
      setBusyId(id);
      await api.delete(`/api/v1/chaos/scenarios/${id}`);
      toast.success('场景已删除');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '删除场景失败');
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">混沌场景</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>新建场景</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="sname">场景名称</Label>
              <Input id="sname" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" />
            </div>
            <div>
              <Label htmlFor="ssched">调度（cron，可选）</Label>
              <Input id="ssched" value={form.schedule} onChange={(e) => setForm({ ...form, schedule: e.target.value })} placeholder="0 2 * * *" className="mt-1" />
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="sdesc">描述</Label>
              <Input id="sdesc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1" />
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="sexp">实验 ID（逗号分隔）</Label>
              <Input id="sexp" value={form.experiments} onChange={(e) => setForm({ ...form, experiments: e.target.value })} placeholder="EXP-XXXX, EXP-YYYY" className="mt-1" />
            </div>
          </div>
          <div className="border rounded p-3 flex flex-wrap items-end gap-3 bg-gray-50">
            <div className="flex-1 min-w-[200px]">
              <Label htmlFor="expname">快速创建实验并加入场景</Label>
              <Input id="expname" value={experimentName} onChange={(e) => setExperimentName(e.target.value)} placeholder="实验名称" className="mt-1" />
            </div>
            <Button variant="secondary" onClick={createExperimentAndAttach}>创建实验</Button>
          </div>
          <Button onClick={createScenario} disabled={creating}>{creating ? '创建中...' : '创建场景'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>场景列表（{scenarios.length}）</CardTitle></CardHeader>
        <CardContent>
          {scenarios.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无场景</div>
          ) : (
            <div className="space-y-3">
              {scenarios.map((s) => (
                <div key={s.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{s.name}</span>
                      <Badge variant={s.enabled ? 'default' : 'secondary'}>{s.enabled ? '启用' : '停用'}</Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => runScenario(s.id)} disabled={busyId === s.id}>执行</Button>
                      <Button size="sm" variant="secondary" onClick={() => deleteScenario(s.id)} disabled={busyId === s.id}>删除</Button>
                    </div>
                  </div>
                  {s.description && <div className="text-sm text-gray-600 mb-1">{s.description}</div>}
                  <div className="text-xs text-gray-500">实验: {s.experiments?.join(', ') || '无'} | 调度: {s.schedule || '手动'}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
