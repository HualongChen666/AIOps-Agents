'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface RegisteredService {
  id: string;
  name: string;
  service_id: string;
  address: string;
  port: number;
  tags: string[];
  registered_at: string;
  health_check_url: string;
}

export default function ServiceRegistrationPage() {
  const [services, setServices] = useState<RegisteredService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newService, setNewService] = useState({
    name: '',
    service_id: '',
    address: '',
    port: 8080,
    tags: '',
    health_check_url: ''
  });

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/service-registration');
      setServices(res.data.services || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载注册服务失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    try {
      await api.post('/api/topology/service-registration', {
        ...newService,
        tags: newService.tags.split(',').map(t => t.trim())
      });
      setNewService({ name: '', service_id: '', address: '', port: 8080, tags: '', health_check_url: '' });
      fetchServices();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '注册服务失败');
    }
  };

  const handleDeregister = async (id: string) => {
    try {
      await api.delete(`/api/topology/service-registration/${id}`);
      fetchServices();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '注销服务失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchServices} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务注册</h1>
        <Button onClick={fetchServices}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>注册新服务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="服务名称"
              value={newService.name}
              onChange={(e) => setNewService({ ...newService, name: e.target.value })}
            />
            <Input
              placeholder="服务ID"
              value={newService.service_id}
              onChange={(e) => setNewService({ ...newService, service_id: e.target.value })}
            />
            <Input
              placeholder="地址"
              value={newService.address}
              onChange={(e) => setNewService({ ...newService, address: e.target.value })}
            />
            <Input
              type="number"
              placeholder="端口"
              value={newService.port}
              onChange={(e) => setNewService({ ...newService, port: parseInt(e.target.value) || 8080 })}
            />
            <Input
              placeholder="标签 (逗号分隔)"
              value={newService.tags}
              onChange={(e) => setNewService({ ...newService, tags: e.target.value })}
            />
            <Input
              placeholder="健康检查URL"
              value={newService.health_check_url}
              onChange={(e) => setNewService({ ...newService, health_check_url: e.target.value })}
            />
          </div>
          <Button onClick={handleRegister} className="mt-4">注册</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>已注册服务</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>服务ID</TableHead>
                <TableHead>地址:端口</TableHead>
                <TableHead>标签</TableHead>
                <TableHead>注册时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {services.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium">{service.name}</TableCell>
                  <TableCell className="font-mono text-sm">{service.service_id}</TableCell>
                  <TableCell className="font-mono text-sm">{service.address}:{service.port}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {service.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(service.registered_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Button variant="destructive" size="sm" onClick={() => handleDeregister(service.id)}>
                      注销
                    </Button>
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
