'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface Collection {
  name: string;
  vector_size?: number;
  points_count?: number;
}

export default function CollectionManagementPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', vector_size: 768, distance: 'Cosine' });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/vector/collections');
      setCollections(Array.isArray(res.data) ? res.data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载集合失败（Qdrant 可能不可用）');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim()) {
      toast.error('请填写集合名称');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/vector/collections', form);
      toast.success('集合已创建');
      setForm({ name: '', vector_size: 768, distance: 'Cosine' });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建集合失败');
    } finally {
      setCreating(false);
    }
  };

  const remove = async (name: string) => {
    try {
      await api.delete(`/api/vector/collections/${encodeURIComponent(name)}`);
      toast.success('集合已删除');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '删除集合失败');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">集合管理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>新建集合</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div><Label htmlFor="col-name">名称</Label><Input id="col-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
          <div><Label htmlFor="col-size">向量维度</Label><Input id="col-size" type="number" value={form.vector_size} onChange={(e) => setForm({ ...form, vector_size: Number(e.target.value) || 0 })} className="mt-1" /></div>
          <div>
            <Label htmlFor="col-dist">距离度量</Label>
            <select id="col-dist" className="mt-1 border rounded px-2 py-2 w-full" value={form.distance} onChange={(e) => setForm({ ...form, distance: e.target.value })}>
              <option value="Cosine">Cosine</option>
              <option value="Euclid">Euclid</option>
              <option value="Dot">Dot</option>
            </select>
          </div>
          <div className="flex items-end"><Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建集合'}</Button></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>集合列表（{collections.length}）</CardTitle></CardHeader>
        <CardContent>
          {collections.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无集合</div>
          ) : (
            <div className="space-y-2">
              {collections.map((c) => (
                <div key={c.name} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{c.name}</span>
                      {c.vector_size && <Badge variant="secondary">维度 {c.vector_size}</Badge>}
                      {typeof c.points_count === 'number' && <Badge variant="secondary">{c.points_count} 点</Badge>}
                    </div>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => remove(c.name)}>删除</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
