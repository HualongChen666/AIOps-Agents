'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface SLO {
  id: string;
  name: string;
  service: string;
  target: number;
  current: number;
  window: string;
  status: 'met' | 'breached' | 'at_risk';
  last_updated: string;
}

export default function SLOManagementPage() {
  const [slos, setSlos] = useState<SLO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newSLO, setNewSLO] = useState({
    name: '',
    service: '',
    target: 99.9,
    window: '30d'
  });

  useEffect(() => {
    fetchSLOs();
  }, []);

  const fetchSLOs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/management');
      setSlos(res.data.slos || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载SLO失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/slo/management', newSLO);
      setNewSLO({ name: '', service: '', target: 99.9, window: '30d' });
      fetchSLOs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建SLO失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/api/slo/management/${id}`);
      fetchSLOs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除SLO失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'met': return 'bg-green-100 text-green-800';
      case 'breached': return 'bg-red-100 text-red-800';
      case 'at_risk': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchSLOs} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO管理</h1>
        <Button onClick={fetchSLOs}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>创建新SLO</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="SLO名称"
              value={newSLO.name}
              onChange={(e) => setNewSLO({ ...newSLO, name: e.target.value })}
            />
            <Input
              placeholder="服务名称"
              value={newSLO.service}
              onChange={(e) => setNewSLO({ ...newSLO, service: e.target.value })}
            />
            <Input
              type="number"
              placeholder="目标百分比 (如: 99.9)"
              value={newSLO.target}
              onChange={(e) => setNewSLO({ ...newSLO, target: parseFloat(e.target.value) || 99.9 })}
            />
            <Input
              placeholder="时间窗口 (如: 30d)"
              value={newSLO.window}
              onChange={(e) => setNewSLO({ ...newSLO, window: e.target.value })}
            />
          </div>
          <Button onClick={handleCreate} className="mt-4">创建</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SLO列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>目标</TableHead>
                <TableHead>当前</TableHead>
                <TableHead>窗口</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slos.map((slo) => (
                <TableRow key={slo.id}>
                  <TableCell className="font-medium">{slo.name}</TableCell>
                  <TableCell>{slo.service}</TableCell>
                  <TableCell>{slo.target}%</TableCell>
                  <TableCell>{slo.current.toFixed(2)}%</TableCell>
                  <TableCell>{slo.window}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(slo.status)}>
                      {slo.status === 'met' ? '达成' : slo.status === 'breached' ? '违反' : '风险'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(slo.id)}>删除</Button>
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
