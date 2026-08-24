'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface DiscoveredService {
  id: string;
  name: string;
  address: string;
  port: number;
  protocol: string;
  health: 'healthy' | 'unhealthy';
  last_seen: string;
  metadata: Record<string, string>;
}

export default function ServiceDiscoveryPage() {
  const [services, setServices] = useState<DiscoveredService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/service-discovery');
      setServices(res.data.services || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载服务发现数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    try {
      await api.post('/api/topology/service-discovery/scan');
      fetchServices();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '扫描失败');
    }
  };

  const filteredServices = services.filter(s =>
    s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchServices} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务发现</h1>
        <div className="flex gap-2">
          <Button onClick={handleScan}>扫描服务</Button>
          <Button onClick={fetchServices}>刷新</Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Input
            placeholder="搜索服务..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>已发现服务 ({filteredServices.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>地址</TableHead>
                <TableHead>端口</TableHead>
                <TableHead>协议</TableHead>
                <TableHead>健康状态</TableHead>
                <TableHead>最后发现</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredServices.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium">{service.name}</TableCell>
                  <TableCell className="font-mono text-sm">{service.address}</TableCell>
                  <TableCell>{service.port}</TableCell>
                  <TableCell><Badge variant="outline">{service.protocol}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={service.health === 'healthy' ? 'default' : 'destructive'}>
                      {service.health}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(service.last_seen).toLocaleString()}
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
