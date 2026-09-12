'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface Subscription {
  id: string;
  stream_id: string;
  subscriber_id: string;
  subscription_type: string;
  status: string;
  created_at: string;
}

export function SubscriptionsPanel({ title, intro }: { title: string; intro?: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<Subscription[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ stream_id: '', subscriber_id: '', subscription_type: 'sse' });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/realtime/subscriptions');
      setItems(Array.isArray(res.data) ? res.data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载订阅失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.stream_id.trim() || !form.subscriber_id.trim()) {
      toast.error('请填写流 ID 和订阅者 ID');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/realtime/subscriptions', form);
      toast.success('订阅已创建');
      setForm({ stream_id: '', subscriber_id: '', subscription_type: 'sse' });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/api/v1/realtime/subscriptions/${id}`);
      toast.success('订阅已删除');
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
        <CardHeader><CardTitle>新建订阅</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div><Label htmlFor="sub-stream">流 ID</Label><Input id="sub-stream" value={form.stream_id} onChange={(e) => setForm({ ...form, stream_id: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="sub-who">订阅者 ID</Label><Input id="sub-who" value={form.subscriber_id} onChange={(e) => setForm({ ...form, subscriber_id: e.target.value })} className="mt-1" /></div>
          <div>
            <Label htmlFor="sub-type">类型</Label>
            <select id="sub-type" className="mt-1 border rounded px-2 py-2 w-full" value={form.subscription_type} onChange={(e) => setForm({ ...form, subscription_type: e.target.value })}>
              <option value="sse">sse</option>
              <option value="websocket">websocket</option>
            </select>
          </div>
          <div className="flex items-end"><Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建'}</Button></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>订阅列表（{items.length}）</CardTitle></CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无订阅</div>
          ) : (
            <div className="space-y-2">
              {items.map((s) => (
                <div key={s.id} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{s.subscriber_id}</span>
                      <Badge variant="secondary">{s.subscription_type}</Badge>
                      <Badge variant={s.status === 'active' ? 'default' : 'secondary'}>{s.status}</Badge>
                    </div>
                    <div className="text-xs text-gray-500">流: {s.stream_id} | ID: {s.id}</div>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => remove(s.id)}>删除</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
