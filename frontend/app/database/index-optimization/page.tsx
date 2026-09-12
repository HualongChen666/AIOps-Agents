'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DatabaseIndex {
  index_id: string;
  index_name: string;
  table_name: string;
  columns: string[];
  index_type: string;
  is_unique: boolean;
  size_bytes: number;
  created_at: string;
}

interface IndexRecommendation {
  recommendation_id: string;
  table_name: string;
  column_names: string[];
  index_type: string;
  estimated_improvement: number;
  current_query_impact: number;
  priority: string;
  creation_cost: string;
  description: string;
}

export default function IndexOptimizationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [indexes, setIndexes] = useState<DatabaseIndex[]>([]);
  const [recommendations, setRecommendations] = useState<IndexRecommendation[]>([]);
  const [tableFilter, setTableFilter] = useState('');
  const [genTable, setGenTable] = useState('');
  const [generating, setGenerating] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newIndex, setNewIndex] = useState({ index_name: '', table_name: '', columns: '', is_unique: false });

  const fetchIndexes = useCallback(async () => {
    const res = await api.get('/api/v1/database/indexes', {
      params: tableFilter ? { table_name: tableFilter } : {},
    });
    setIndexes(Array.isArray(res.data) ? res.data : []);
  }, [tableFilter]);

  const fetchRecommendations = useCallback(async () => {
    const res = await api.get('/api/v1/database-optimization/index-recommendations');
    setRecommendations(Object.values(res.data || {}));
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([fetchIndexes(), fetchRecommendations()]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, [fetchIndexes, fetchRecommendations]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const generateRecommendations = async () => {
    if (!genTable.trim()) {
      toast.error('请输入表名');
      return;
    }
    try {
      setGenerating(true);
      const res = await api.post('/api/v1/database-optimization/index-recommendations/generate', null, {
        params: { table_name: genTable },
      });
      const count = Object.keys(res.data || {}).length;
      toast.success(count ? `为 ${genTable} 生成 ${count} 条索引建议` : `${genTable} 暂无索引建议`);
      await fetchRecommendations();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '生成索引建议失败');
    } finally {
      setGenerating(false);
    }
  };

  const createIndex = async () => {
    const columns = newIndex.columns.split(',').map((c) => c.trim()).filter(Boolean);
    if (!newIndex.index_name.trim() || !newIndex.table_name.trim() || columns.length === 0) {
      toast.error('请填写索引名称、表名和列（逗号分隔）');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/database/indexes', {
        index_name: newIndex.index_name,
        table_name: newIndex.table_name,
        columns,
        index_type: 'btree',
        is_unique: newIndex.is_unique,
      });
      toast.success('索引记录已创建');
      setNewIndex({ index_name: '', table_name: '', columns: '', is_unique: false });
      await fetchIndexes();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建索引失败');
    } finally {
      setCreating(false);
    }
  };

  const uniqueCount = indexes.filter((i) => i.is_unique).length;
  const tableCount = new Set(indexes.map((i) => i.table_name)).size;

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchAll} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">索引优化</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">索引总数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{indexes.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">覆盖表数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{tableCount}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">唯一索引</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{uniqueCount}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">索引建议</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{recommendations.length}</div></CardContent></Card>
      </div>

      <Tabs defaultValue="list" className="space-y-4">
        <TabsList>
          <TabsTrigger value="list">索引列表</TabsTrigger>
          <TabsTrigger value="create">创建索引</TabsTrigger>
          <TabsTrigger value="recs">索引建议</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>数据库索引（实时目录）</CardTitle>
              <div className="flex items-center gap-2">
                <Input
                  value={tableFilter}
                  onChange={(e) => setTableFilter(e.target.value)}
                  placeholder="按表名筛选"
                  className="w-48"
                />
                <Button size="sm" onClick={fetchIndexes}>筛选</Button>
              </div>
            </CardHeader>
            <CardContent>
              {indexes.length === 0 ? (
                <div className="text-gray-500 text-center py-8">未发现索引</div>
              ) : (
                <div className="max-h-[600px] overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-white">
                      <tr className="border-b text-left text-gray-600">
                        <th className="py-2">索引名</th>
                        <th className="py-2">表</th>
                        <th className="py-2">列</th>
                        <th className="py-2">唯一</th>
                      </tr>
                    </thead>
                    <tbody>
                      {indexes.map((idx) => (
                        <tr key={idx.index_id} className="border-b">
                          <td className="py-2 font-mono">{idx.index_name}</td>
                          <td className="py-2">{idx.table_name}</td>
                          <td className="py-2">{idx.columns.join(', ')}</td>
                          <td className="py-2">
                            <Badge variant={idx.is_unique ? 'default' : 'secondary'}>
                              {idx.is_unique ? '唯一' : '普通'}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="create">
          <Card>
            <CardHeader><CardTitle>登记新索引</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="idx-name">索引名称</Label>
                <Input id="idx-name" value={newIndex.index_name} onChange={(e) => setNewIndex({ ...newIndex, index_name: e.target.value })} placeholder="idx_users_email" className="mt-1" />
              </div>
              <div>
                <Label htmlFor="idx-table">表名</Label>
                <Input id="idx-table" value={newIndex.table_name} onChange={(e) => setNewIndex({ ...newIndex, table_name: e.target.value })} placeholder="users" className="mt-1" />
              </div>
              <div>
                <Label htmlFor="idx-cols">列（逗号分隔）</Label>
                <Input id="idx-cols" value={newIndex.columns} onChange={(e) => setNewIndex({ ...newIndex, columns: e.target.value })} placeholder="email, created_at" className="mt-1" />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="idx-unique">唯一索引</Label>
                <input id="idx-unique" type="checkbox" checked={newIndex.is_unique} onChange={(e) => setNewIndex({ ...newIndex, is_unique: e.target.checked })} />
              </div>
              <Button onClick={createIndex} disabled={creating}>{creating ? '创建中...' : '创建索引'}</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recs">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>索引建议</CardTitle>
              <div className="flex items-center gap-2">
                <Input value={genTable} onChange={(e) => setGenTable(e.target.value)} placeholder="表名" className="w-40" />
                <Button size="sm" onClick={generateRecommendations} disabled={generating}>
                  {generating ? '生成中...' : '生成建议'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {recommendations.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无索引建议</div>
              ) : (
                <div className="space-y-3">
                  {recommendations.map((r) => (
                    <div key={r.recommendation_id} className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={r.priority === 'high' ? 'destructive' : 'secondary'}>{r.priority}</Badge>
                        <span className="font-semibold">{r.table_name}({r.column_names.join(', ')})</span>
                      </div>
                      <div className="text-sm text-gray-600">{r.description}</div>
                      <div className="text-sm text-green-600 mt-1">
                        预计提升 {r.estimated_improvement}% | 影响查询 {r.current_query_impact} | 成本 {r.creation_cost}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
