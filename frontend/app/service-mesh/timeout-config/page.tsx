'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface TimeoutPolicy {
  id: string;
  name: string;
  target_service: string;
  timeout_seconds: number;
  enabled: boolean;
}

export default function TimeoutConfigPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<TimeoutPolicy[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', target_service: '', timeout_seconds: 30 });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/timeout-policies');
      setItems(res.data.data?.timeout_policies || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载超时策略失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim() || !form.target_service.trim()) {
      toast.error('请填写名称和目标服务');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/service-mesh/timeout-policies', form);
      toast.success('超时策略已创建');
      setForm({ name: '', target_service: '', timeout_seconds: 30 });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/api/v1/service-mesh/timeout-policies/${id}`);
      toast.success('策略已删除');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '删除失败');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">超时配置</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>新建超时策略</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div><Label htmlFor="tp-name">名称</Label><Input id="tp-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="tp-svc">目标服务</Label><Input id="tp-svc" value={form.target_service} onChange={(e) => setForm({ ...form, target_service: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="tp-to">超时(秒)</Label><Input id="tp-to" type="number" value={form.timeout_seconds} onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) || 0 })} className="mt-1" /></div>
          <div className="flex items-end"><Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建'}</Button></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>策略列表（{items.length}）</CardTitle></CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无超时策略</div>
          ) : (
            <div className="space-y-3">
              {items.map((p) => (
                <div key={p.id} className="border rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{p.name}</span>
                      <Badge variant={p.enabled ? 'default' : 'secondary'}>{p.enabled ? '启用' : '停用'}</Badge>
                    </div>
                    <div className="text-sm text-gray-500">目标: {p.target_service} | 超时: {p.timeout_seconds}s</div>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => remove(p.id)}>删除</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
