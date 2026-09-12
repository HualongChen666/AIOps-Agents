'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface Webhook {
  id: string;
  name: string;
  url: string;
  method: string;
  stream_id: string | null;
  enabled: boolean;
  created_at: string;
}

export function WebhooksPanel({ title, intro }: { title: string; intro?: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<Webhook[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', url: '', method: 'POST', stream_id: '' });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/realtime/webhooks');
      setItems(Array.isArray(res.data) ? res.data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载 Webhook 失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim() || !form.url.trim()) {
      toast.error('请填写名称和 URL');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/realtime/webhooks', {
        name: form.name,
        url: form.url,
        method: form.method,
        stream_id: form.stream_id || null,
      });
      toast.success('Webhook 已创建');
      setForm({ name: '', url: '', method: 'POST', stream_id: '' });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/api/v1/realtime/webhooks/${id}`);
      toast.success('Webhook 已删除');
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
        <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>
      {intro && <div className="text-sm text-gray-600">{intro}</div>}

      <Card>
        <CardHeader><CardTitle>新建 Webhook</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div><Label htmlFor="wh-name">名称</Label><Input id="wh-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="wh-url">URL</Label><Input id="wh-url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://..." className="mt-1" /></div>
          <div>
            <Label htmlFor="wh-method">方法</Label>
            <select id="wh-method" className="mt-1 border rounded px-2 py-2 w-full" value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
              <option value="POST">POST</option><option value="PUT">PUT</option><option value="GET">GET</option>
            </select>
          </div>
          <div><Label htmlFor="wh-stream">关联流 ID</Label><Input id="wh-stream" value={form.stream_id} onChange={(e) => setForm({ ...form, stream_id: e.target.value })} placeholder="可选" className="mt-1" /></div>
          <div className="flex items-end"><Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建'}</Button></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Webhook 列表（{items.length}）</CardTitle></CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无 Webhook</div>
          ) : (
            <div className="space-y-2">
              {items.map((w) => (
                <div key={w.id} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{w.name}</span>
                      <Badge variant="secondary">{w.method}</Badge>
                      <Badge variant={w.enabled ? 'default' : 'secondary'}>{w.enabled ? '启用' : '停用'}</Badge>
                    </div>
                    <div className="text-xs text-gray-500">{w.url} | 流: {w.stream_id || '—'}</div>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => remove(w.id)}>删除</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
