'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface SLA {
  id: string;
  name: string;
  customer: string;
  service: string;
  availability_target: number;
  response_time_target: number;
  start_date: string;
  end_date: string;
  status: 'active' | 'expired' | 'pending';
}

export default function SLAManagementPage() {
  const [slas, setSlas] = useState<SLA[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newSLA, setNewSLA] = useState({
    name: '',
    customer: '',
    service: '',
    availability_target: 99.9,
    response_time_target: 500,
    start_date: '',
    end_date: ''
  });

  useEffect(() => {
    fetchSLAs();
  }, []);

  const fetchSLAs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/sla-management');
      setSlas(res.data.slas || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载SLA失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/slo/sla-management', newSLA);
      setNewSLA({
        name: '',
        customer: '',
        service: '',
        availability_target: 99.9,
        response_time_target: 500,
        start_date: '',
        end_date: ''
      });
      fetchSLAs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建SLA失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchSLAs} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLA管理</h1>
        <Button onClick={fetchSLAs}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>创建新SLA</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="SLA名称"
              value={newSLA.name}
              onChange={(e) => setNewSLA({ ...newSLA, name: e.target.value })}
            />
            <Input
              placeholder="客户"
              value={newSLA.customer}
              onChange={(e) => setNewSLA({ ...newSLA, customer: e.target.value })}
            />
            <Input
              placeholder="服务"
              value={newSLA.service}
              onChange={(e) => setNewSLA({ ...newSLA, service: e.target.value })}
            />
            <Input
              type="number"
              placeholder="可用性目标 (%)"
              value={newSLA.availability_target}
              onChange={(e) => setNewSLA({ ...newSLA, availability_target: parseFloat(e.target.value) || 99.9 })}
            />
            <Input
              type="number"
              placeholder="响应时间目标 (ms)"
              value={newSLA.response_time_target}
              onChange={(e) => setNewSLA({ ...newSLA, response_time_target: parseInt(e.target.value) || 500 })}
            />
            <Input
              type="date"
              value={newSLA.start_date}
              onChange={(e) => setNewSLA({ ...newSLA, start_date: e.target.value })}
            />
            <Input
              type="date"
              value={newSLA.end_date}
              onChange={(e) => setNewSLA({ ...newSLA, end_date: e.target.value })}
            />
          </div>
          <Button onClick={handleCreate} className="mt-4">创建</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>SLA列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>客户</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>可用性目标</TableHead>
                <TableHead>响应时间</TableHead>
                <TableHead>有效期</TableHead>
                <TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slas.map((sla) => (
                <TableRow key={sla.id}>
                  <TableCell className="font-medium">{sla.name}</TableCell>
                  <TableCell>{sla.customer}</TableCell>
                  <TableCell>{sla.service}</TableCell>
                  <TableCell>{sla.availability_target}%</TableCell>
                  <TableCell>{sla.response_time_target}ms</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(sla.start_date).toLocaleDateString()} - {new Date(sla.end_date).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Badge variant={sla.status === 'active' ? 'default' : 'secondary'}>
                      {sla.status === 'active' ? '生效中' : sla.status === 'expired' ? '已过期' : '待生效'}
                    </Badge>
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
