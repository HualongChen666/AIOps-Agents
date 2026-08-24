'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface SLOData {
  id: string;
  slo_id: string;
  timestamp: string;
  value: number;
  metadata: Record<string, any>;
}

export default function SLOStoragePage() {
  const [data, setData] = useState<SLOData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/storage');
      setData(res.data.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO存储</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>存储概览</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold">{data.length}</div>
              <div className="text-sm text-gray-500">总记录数</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold">{new Set(data.map(d => d.slo_id)).size}</div>
              <div className="text-sm text-gray-500">SLO数量</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold">
                {data.length > 0 ? (data.reduce((sum, d) => sum + d.value, 0) / data.length).toFixed(2) : 0}
              </div>
              <div className="text-sm text-gray-500">平均值</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SLO数据记录</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SLO ID</TableHead>
                <TableHead>时间戳</TableHead>
                <TableHead>值</TableHead>
                <TableHead>元数据</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.slice(0, 50).map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-sm">{item.slo_id}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(item.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell className="font-semibold">{item.value.toFixed(2)}%</TableCell>
                  <TableCell className="text-sm">
                    <Badge variant="outline">{Object.keys(item.metadata).length} 项</Badge>
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
