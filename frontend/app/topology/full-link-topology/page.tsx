'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface ServiceNode {
  id: string;
  name: string;
  type: string;
  status: 'healthy' | 'unhealthy';
  dependencies: string[];
}

export default function FullLinkTopologyPage() {
  const [nodes, setNodes] = useState<ServiceNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedService, setSelectedService] = useState<string | null>(null);

  useEffect(() => {
    fetchTopology();
  }, []);

  const fetchTopology = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/full-link');
      setNodes(res.data.nodes || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载全链路拓扑失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchTopology} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">全链路拓扑</h1>
        <Button onClick={fetchTopology}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>服务依赖图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {nodes.map((node) => (
              <div key={node.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{node.name}</h3>
                  <Badge variant={node.status === 'healthy' ? 'default' : 'destructive'}>
                    {node.status}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600 mb-2">类型: {node.type}</div>
                <div className="text-sm text-gray-600">
                  依赖服务: {node.dependencies.length > 0 ? node.dependencies.join(', ') : '无'}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
