'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

export default function VectorRetrievalPage() {
  const [collection, setCollection] = useState('');
  const [id, setId] = useState('');
  const [result, setResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const retrieve = async () => {
    if (!collection.trim() || !id.trim()) {
      toast.error('请填写集合与点 ID');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/vector/points/get', { collection, id: Number.isNaN(Number(id)) ? id : Number(id) });
      setResult(res.data);
      toast.success('检索完成');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '检索失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">向量检索</h1>

      <Card>
        <CardHeader><CardTitle>按 ID 检索向量点</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><Label htmlFor="vr-col">集合</Label><Input id="vr-col" value={collection} onChange={(e) => setCollection(e.target.value)} className="mt-1" /></div>
            <div><Label htmlFor="vr-id">点 ID</Label><Input id="vr-id" value={id} onChange={(e) => setId(e.target.value)} className="mt-1" /></div>
          </div>
          <Button onClick={retrieve} disabled={loading}>{loading ? '检索中...' : '检索'}</Button>
          {error && <div className="text-sm text-red-600">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>结果</CardTitle></CardHeader>
        <CardContent>
          {result === null ? (
            <div className="text-gray-500 text-center py-8">尚未检索</div>
          ) : (
            <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(result, null, 2)}</pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
