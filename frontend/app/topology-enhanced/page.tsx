'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface ServiceNode {
  id: string;
  name: string;
  type: string;
  status: 'healthy' | 'warning' | 'critical';
  cpu: number;
  memory: number;
  requests: number;
}

interface Edge {
  source: string;
  target: string;
  traffic: number;
  latency: number;
}

export default function TopologyEnhancedPage() {
  const [selectedView, setSelectedView] = useState('traffic');
  const [selectedService, setSelectedService] = useState<string | null>(null);

  const [nodes, setNodes] = useState<ServiceNode[]>([
    {
      id: 'web-service',
      name: 'Web Service',
      type: 'service',
      status: 'healthy',
      cpu: 45,
      memory: 55,
      requests: 1200,
    },
    {
      id: 'api-gateway',
      name: 'API Gateway',
      type: 'gateway',
      status: 'warning',
      cpu: 72,
      memory: 68,
      requests: 3500,
    },
    {
      id: 'database',
      name: 'Database',
      type: 'database',
      status: 'healthy',
      cpu: 35,
      memory: 80,
      requests: 800,
    },
    {
      id: 'cache',
      name: 'Cache',
      type: 'cache',
      status: 'healthy',
      cpu: 20,
      memory: 45,
      requests: 2000,
    },
  ]);

  const [edges, setEdges] = useState<Edge[]>([
    { source: 'web-service', target: 'api-gateway', traffic: 1200, latency: 15 },
    { source: 'api-gateway', target: 'database', traffic: 800, latency: 25 },
    { source: 'api-gateway', target: 'cache', traffic: 2000, latency: 5 },
  ]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务地图增强</h1>
        <div className="flex gap-2">
          <Select value={selectedView} onChange={(e) => setSelectedView(e.target.value)}>
            <option value="traffic">流量视图</option>
            <option value="latency">延迟视图</option>
            <option value="error">错误视图</option>
          </Select>
          <Button>刷新</Button>
        </div>
      </div>

      {/* 服务拓扑图 */}
      <Card>
        <CardHeader>
          <CardTitle>服务拓扑图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center relative">
            <p className="text-gray-500">服务拓扑图 (使用@antv/g6渲染，支持流量可视化)</p>
            <div className="absolute top-4 right-4 space-x-2">
              <Badge className="bg-green-100 text-green-800">健康</Badge>
              <Badge className="bg-yellow-100 text-yellow-800">警告</Badge>
              <Badge className="bg-red-100 text-red-800">严重</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 服务详情 */}
      {selectedService && (
        <Card>
          <CardHeader>
            <CardTitle>服务详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">CPU使用率</div>
                <div className="text-2xl font-bold">45%</div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">内存使用率</div>
                <div className="text-2xl font-bold">55%</div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">请求速率</div>
                <div className="text-2xl font-bold">1200/s</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 服务列表 */}
      <Card>
        <CardHeader>
          <CardTitle>服务列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {nodes.map((node) => (
              <div
                key={node.id}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                onClick={() => setSelectedService(node.id)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{node.name}</h3>
                      <Badge className={getStatusColor(node.status)}>
                        {node.status === 'healthy' ? '健康' : node.status === 'warning' ? '警告' : '严重'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500">{node.type}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm">CPU: {node.cpu}%</div>
                    <div className="text-sm">内存: {node.memory}%</div>
                    <div className="text-sm">请求: {node.requests}/s</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 流量统计 */}
      <Card>
        <CardHeader>
          <CardTitle>流量统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">总流量</div>
              <div className="text-2xl font-bold">5.2 GB</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">平均延迟</div>
              <div className="text-2xl font-bold">18ms</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">错误率</div>
              <div className="text-2xl font-bold text-red-600">0.05%</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">P99延迟</div>
              <div className="text-2xl font-bold">45ms</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
