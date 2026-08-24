'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface Topology {
  id: string;
  name: string;
  type: 'microservice' | 'monolith' | 'hybrid';
  status: 'active' | 'inactive' | 'error';
  service_count: number;
  last_updated: string;
  description: string;
}

export default function TopologyManagementPage() {
  const [topologies, setTopologies] = useState<Topology[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTopology, setNewTopology] = useState({ name: '', type: 'microservice', description: '' });

  useEffect(() => {
    fetchTopologies();
  }, []);

  const fetchTopologies = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/management');
      setTopologies(res.data.topologies || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载拓扑数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/topology/management', newTopology);
      setNewTopology({ name: '', type: 'microservice', description: '' });
      fetchTopologies();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建拓扑失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/api/topology/management/${id}`);
      fetchTopologies();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除拓扑失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchTopologies} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑管理</h1>
        <Button onClick={fetchTopologies}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>拓扑列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>服务数量</TableHead>
                <TableHead>最后更新</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {topologies.map((topo) => (
                <TableRow key={topo.id}>
                  <TableCell className="font-medium">{topo.name}</TableCell>
                  <TableCell><Badge variant="outline">{topo.type}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={topo.status === 'active' ? 'default' : 'secondary'}>
                      {topo.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{topo.service_count}</TableCell>
                  <TableCell className="text-sm text-gray-500">{new Date(topo.last_updated).toLocaleString()}</TableCell>
                  <TableCell>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(topo.id)}>删除</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>创建新拓扑</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              placeholder="拓扑名称"
              value={newTopology.name}
              onChange={(e) => setNewTopology({ ...newTopology, name: e.target.value })}
            />
            <Input
              placeholder="描述"
              value={newTopology.description}
              onChange={(e) => setNewTopology({ ...newTopology, description: e.target.value })}
            />
            <Button onClick={handleCreate}>创建</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
