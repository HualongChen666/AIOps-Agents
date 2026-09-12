'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api';
import toast from 'react-hot-toast';

export default function VectorSearchPage() {
  const [collection, setCollection] = useState('');
  const [vectorText, setVectorText] = useState('0.1, 0.2, 0.3');
  const [topK, setTopK] = useState(5);
  const [result, setResult] = useState<unknown>(null);
  const [mode, setMode] = useState<'basic' | 'hybrid' | 'multi'>('basic');
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseVector = () => vectorText.split(',').map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n));

  const search = async () => {
    const vec = parseVector();
    if (!collection.trim() || vec.length === 0) {
      toast.error('请填写集合名称与查询向量');
      return;
    }
    try {
      setSearching(true);
      setError(null);
      let res;
      if (mode === 'basic') {
        res = await api.post('/api/vector/search', { collection, query_vector: vec, top_k: topK });
      } else if (mode === 'hybrid') {
        res = await api.post('/api/vector/search/hybrid', { collection, query_vector: vec, top_k: topK });
      } else {
        res = await api.post('/api/vector/search/multi-vector', { collection, query_vectors: [vec], top_k: topK });
      }
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '向量搜索失败');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">向量搜索</h1>

      <Card>
        <CardHeader><CardTitle>搜索参数</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div><Label htmlFor="vs-col">集合</Label><Input id="vs-col" value={collection} onChange={(e) => setCollection(e.target.value)} className="mt-1" /></div>
            <div><Label htmlFor="vs-topk">Top K</Label><Input id="vs-topk" type="number" value={topK} onChange={(e) => setTopK(Number(e.target.value) || 1)} className="mt-1" /></div>
            <div>
              <Label htmlFor="vs-mode">搜索模式</Label>
              <select id="vs-mode" className="mt-1 border rounded px-2 py-2 w-full" value={mode} onChange={(e) => setMode(e.target.value as any)}>
                <option value="basic">基础</option>
                <option value="hybrid">混合检索</option>
                <option value="multi">多向量</option>
              </select>
            </div>
          </div>
          <div>
            <Label htmlFor="vs-vec">查询向量（逗号分隔）</Label>
            <Textarea id="vs-vec" value={vectorText} onChange={(e) => setVectorText(e.target.value)} rows={3} className="mt-1 font-mono" />
          </div>
          <Button onClick={search} disabled={searching}>{searching ? '搜索中...' : '执行搜索'}</Button>
          {error && <div className="text-sm text-red-600">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>结果</CardTitle></CardHeader>
        <CardContent>
          {result === null ? (
            <div className="text-gray-500 text-center py-8">尚未执行搜索</div>
          ) : (
            <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(result, null, 2)}</pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
