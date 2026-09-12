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

interface SearchHit {
  id: number | string;
  score: number;
  payload?: Record<string, unknown>;
}

export default function SimilaritySearchPage() {
  const [collection, setCollection] = useState('');
  const [vectorText, setVectorText] = useState('0.1, 0.2, 0.3');
  const [topK, setTopK] = useState(5);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async () => {
    const query_vector = vectorText.split(',').map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n));
    if (!collection.trim() || query_vector.length === 0) {
      toast.error('请填写集合名称与查询向量');
      return;
    }
    try {
      setSearching(true);
      setError(null);
      const res = await api.post('/api/vector/search', { collection, query_vector, top_k: topK });
      setHits(Array.isArray(res.data) ? res.data : []);
      toast.success(`返回 ${Array.isArray(res.data) ? res.data.length : 0} 条结果`);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '相似度搜索失败');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">相似度搜索</h1>

      <Card>
        <CardHeader><CardTitle>查询向量</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><Label htmlFor="ss-col">集合</Label><Input id="ss-col" value={collection} onChange={(e) => setCollection(e.target.value)} placeholder="collection name" className="mt-1" /></div>
            <div><Label htmlFor="ss-topk">Top K</Label><Input id="ss-topk" type="number" value={topK} onChange={(e) => setTopK(Number(e.target.value) || 1)} className="mt-1" /></div>
          </div>
          <div>
            <Label htmlFor="ss-vec">查询向量（逗号分隔的浮点数）</Label>
            <Textarea id="ss-vec" value={vectorText} onChange={(e) => setVectorText(e.target.value)} rows={3} className="mt-1 font-mono" />
          </div>
          <Button onClick={search} disabled={searching}>{searching ? '搜索中...' : '搜索'}</Button>
          {error && <div className="text-sm text-red-600">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>结果（{hits.length}）</CardTitle></CardHeader>
        <CardContent>
          {hits.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无结果</div>
          ) : (
            <div className="space-y-2">
              {hits.map((h, i) => (
                <div key={`${h.id}-${i}`} className="border rounded p-3 flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-mono text-sm">id: {String(h.id)}</div>
                    <div className="text-xs text-gray-500 font-mono">{h.payload ? JSON.stringify(h.payload) : '—'}</div>
                  </div>
                  <Badge variant="secondary">score {typeof h.score === 'number' ? h.score.toFixed(4) : h.score}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
