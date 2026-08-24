'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface CostSource {
  id: string;
  name: string;
  type: 'cloud' | 'on-premise' | 'saas';
  status: 'active' | 'inactive' | 'error';
  last_sync: string;
  data_points: number;
}

export default function CostCollectionPage() {
  const [sources, setSources] = useState<CostSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/cost/cost-collection');
      setSources(res.data.sources || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载成本源失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (id: string) => {
    try {
      await api.post(`/api/cost/cost-collection/${id}/sync`);
      fetchSources();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '同步失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchSources} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">成本收集</h1>
        <Button onClick={fetchSources}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>成本数据源</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>最后同步</TableHead>
                <TableHead>数据点</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.map((source) => (
                <TableRow key={source.id}>
                  <TableCell className="font-medium">{source.name}</TableCell>
                  <TableCell><Badge variant="outline">{source.type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={source.status === 'active' ? 'default' : 'secondary'}>
                      {source.status === 'active' ? '活跃' : source.status === 'inactive' ? '未激活' : '错误'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(source.last_sync).toLocaleString()}
                  </TableCell>
                  <TableCell>{source.data_points.toLocaleString()}</TableCell>
                  <TableCell>
                    <Button size="sm" onClick={() => handleSync(source.id)}>同步</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
