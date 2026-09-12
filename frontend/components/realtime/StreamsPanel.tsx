'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

export interface RealtimeStream {
  id: string;
  name: string;
  description: string | null;
  stream_type: string;
  source: string | null;
  status: string;
  created_at: string;
}

interface StreamsPanelProps {
  title: string;
  /** When set, only streams of this ``stream_type`` are shown and created. */
  streamType?: string;
  allowCreate?: boolean;
  allowDelete?: boolean;
  intro?: string;
}

export function StreamsPanel({ title, streamType, allowCreate = true, allowDelete = true, intro }: StreamsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [streams, setStreams] = useState<RealtimeStream[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', source: '', type: streamType || 'sse' });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/realtime/streams');
      const all: RealtimeStream[] = Array.isArray(res.data) ? res.data : [];
      setStreams(streamType ? all.filter((s) => s.stream_type === streamType) : all);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载实时流失败');
    } finally {
      setLoading(false);
    }
  }, [streamType]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim()) {
      toast.error('请填写流名称');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/realtime/streams', {
        name: form.name,
        description: null,
        stream_type: form.type,
        source: form.source || null,
        config: {},
      });
      toast.success('实时流已创建');
      setForm({ name: '', source: '', type: streamType || form.type });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.delete(`/api/v1/realtime/streams/${id}`);
      toast.success('流已删除');
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

      {allowCreate && (
        <Card>
          <CardHeader><CardTitle>新建实时流</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div><Label htmlFor="st-name">流名称</Label><Input id="st-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
            <div><Label htmlFor="st-src">数据源</Label><Input id="st-src" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder="可选" className="mt-1" /></div>
            {!streamType && (
              <div>
                <Label htmlFor="st-type">流类型</Label>
                <select id="st-type" className="mt-1 border rounded px-2 py-2 w-full" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  <option value="sse">sse</option>
                  <option value="websocket">websocket</option>
                  <option value="kafka">kafka</option>
                </select>
              </div>
            )}
            <div className="flex items-end"><Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建流'}</Button></div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>实时流（{streams.length}）</CardTitle></CardHeader>
        <CardContent>
          {streams.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无实时流</div>
          ) : (
            <div className="space-y-2">
              {streams.map((s) => (
                <div key={s.id} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{s.name}</span>
                      <Badge variant="secondary">{s.stream_type}</Badge>
                      <Badge variant={s.status === 'active' ? 'default' : 'secondary'}>{s.status}</Badge>
                    </div>
                    <div className="text-xs text-gray-500">ID: {s.id} | 数据源: {s.source || '—'} | {s.created_at ? new Date(s.created_at).toLocaleString() : ''}</div>
                  </div>
                  {allowDelete && <Button size="sm" variant="secondary" onClick={() => remove(s.id)}>删除</Button>}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
