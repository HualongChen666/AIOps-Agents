'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface KPI {
  id: string;
  name: string;
  category: string;
  unit: string;
  target: number;
  current: number;
  trend: 'up' | 'down' | 'stable';
  last_updated: string;
}

export default function KPIManagementPage() {
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newKPI, setNewKPI] = useState({
    name: '',
    category: '',
    unit: '',
    target: 0
  });

  useEffect(() => {
    fetchKPIs();
  }, []);

  const fetchKPIs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/kpi-management');
      setKpis(res.data.kpis || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载KPI失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/slo/kpi-management', newKPI);
      setNewKPI({ name: '', category: '', unit: '', target: 0 });
      fetchKPIs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建KPI失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/api/slo/kpi-management/${id}`);
      fetchKPIs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除KPI失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchKPIs} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">KPI管理</h1>
        <Button onClick={fetchKPIs}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>创建新KPI</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="KPI名称"
              value={newKPI.name}
              onChange={(e) => setNewKPI({ ...newKPI, name: e.target.value })}
            />
            <Input
              placeholder="类别"
              value={newKPI.category}
              onChange={(e) => setNewKPI({ ...newKPI, category: e.target.value })}
            />
            <Input
              placeholder="单位"
              value={newKPI.unit}
              onChange={(e) => setNewKPI({ ...newKPI, unit: e.target.value })}
            />
            <Input
              type="number"
              placeholder="目标值"
              value={newKPI.target}
              onChange={(e) => setNewKPI({ ...newKPI, target: parseFloat(e.target.value) || 0 })}
            />
          </div>
          <Button onClick={handleCreate} className="mt-4">创建</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>KPI列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>类别</TableHead>
                <TableHead>单位</TableHead>
                <TableHead>目标</TableHead>
                <TableHead>当前值</TableHead>
                <TableHead>趋势</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kpis.map((kpi) => (
                <TableRow key={kpi.id}>
                  <TableCell className="font-medium">{kpi.name}</TableCell>
                  <TableCell><Badge variant="outline">{kpi.category}</Badge></TableCell>
                  <TableCell>{kpi.unit}</TableCell>
                  <TableCell>{kpi.target}</TableCell>
                  <TableCell className="font-semibold">{kpi.current}</TableCell>
                  <TableCell>
                    <Badge variant={kpi.trend === 'up' ? 'default' : kpi.trend === 'down' ? 'destructive' : 'secondary'}>
                      {kpi.trend === 'up' ? '上升' : kpi.trend === 'down' ? '下降' : '稳定'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(kpi.id)}>删除</Button>
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
