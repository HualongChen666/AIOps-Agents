'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';

interface ServiceNode {
  id: string;
  name: string;
  type: 'frontend' | 'backend' | 'database' | 'cache' | 'queue' | 'external';
  status: 'healthy' | 'warning' | 'critical';
  dependencies: string[];
  metrics: {
    requests: number;
    errorRate: number;
    latency: number;
  };
}

interface ServiceDependency {
  from: string;
  to: string;
  type: 'http' | 'rpc' | 'database' | 'cache' | 'queue';
  traffic: number;
}

export default function ServiceMapPage() {
  const [selectedService, setSelectedService] = useState<ServiceNode | null>(null);
  const [viewMode, setViewMode] = useState<'topology' | 'dependencies' | 'traffic'>('topology');

  const [services] = useState<ServiceNode[]>([
    {
      id: 'S-001',
      name: 'web-frontend',
      type: 'frontend',
      status: 'healthy',
      dependencies: ['api-gateway'],
      metrics: { requests: 5000, errorRate: 0.1, latency: 45 },
    },
    {
      id: 'S-002',
      name: 'api-gateway',
      type: 'backend',
      status: 'healthy',
      dependencies: ['user-service', 'order-service', 'product-service'],
      metrics: { requests: 4500, errorRate: 0.2, latency: 80 },
    },
    {
      id: 'S-003',
      name: 'user-service',
      type: 'backend',
      status: 'warning',
      dependencies: ['user-db', 'redis-cache'],
      metrics: { requests: 1500, errorRate: 1.5, latency: 120 },
    },
    {
      id: 'S-004',
      name: 'order-service',
      type: 'backend',
      status: 'healthy',
      dependencies: ['order-db', 'redis-cache', 'kafka-queue'],
      metrics: { requests: 2000, errorRate: 0.3, latency: 95 },
    },
    {
      id: 'S-005',
      name: 'product-service',
      type: 'backend',
      status: 'healthy',
      dependencies: ['product-db', 'redis-cache'],
      metrics: { requests: 1000, errorRate: 0.1, latency: 70 },
    },
    {
      id: 'S-006',
      name: 'user-db',
      type: 'database',
      status: 'healthy',
      dependencies: [],
      metrics: { requests: 800, errorRate: 0, latency: 25 },
    },
    {
      id: 'S-007',
      name: 'order-db',
      type: 'database',
      status: 'critical',
      dependencies: [],
      metrics: { requests: 1200, errorRate: 5.2, latency: 350 },
    },
    {
      id: 'S-008',
      name: 'product-db',
      type: 'database',
      status: 'healthy',
      dependencies: [],
      metrics: { requests: 500, errorRate: 0, latency: 20 },
    },
    {
      id: 'S-009',
      name: 'redis-cache',
      type: 'cache',
      status: 'healthy',
      dependencies: [],
      metrics: { requests: 3000, errorRate: 0.1, latency: 5 },
    },
    {
      id: 'S-010',
      name: 'kafka-queue',
      type: 'queue',
      status: 'healthy',
      dependencies: [],
      metrics: { requests: 500, errorRate: 0, latency: 15 },
    },
  ]);

  const [dependencies] = useState<ServiceDependency[]>([
    { from: 'web-frontend', to: 'api-gateway', type: 'http', traffic: 5000 },
    { from: 'api-gateway', to: 'user-service', type: 'http', traffic: 1500 },
    { from: 'api-gateway', to: 'order-service', type: 'http', traffic: 2000 },
    { from: 'api-gateway', to: 'product-service', type: 'http', traffic: 1000 },
    { from: 'user-service', to: 'user-db', type: 'database', traffic: 800 },
    { from: 'user-service', to: 'redis-cache', type: 'cache', traffic: 700 },
    { from: 'order-service', to: 'order-db', type: 'database', traffic: 1200 },
    { from: 'order-service', to: 'redis-cache', type: 'cache', traffic: 800 },
    { from: 'order-service', to: 'kafka-queue', type: 'queue', traffic: 500 },
    { from: 'product-service', to: 'product-db', type: 'database', traffic: 500 },
    { from: 'product-service', to: 'redis-cache', type: 'cache', traffic: 500 },
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

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'frontend':
        return 'bg-blue-100 text-blue-800';
      case 'backend':
        return 'bg-purple-100 text-purple-800';
      case 'database':
        return 'bg-orange-100 text-orange-800';
      case 'cache':
        return 'bg-green-100 text-green-800';
      case 'queue':
        return 'bg-pink-100 text-pink-800';
      case 'external':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'frontend':
        return '前端';
      case 'backend':
        return '后端';
      case 'database':
        return '数据库';
      case 'cache':
        return '缓存';
      case 'queue':
        return '队列';
      case 'external':
        return '外部';
      default:
        return type;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务地图</h1>
        <div className="flex gap-2">
          <Select value={viewMode} onChange={(e) => setViewMode(e.target.value as any)}>
            <option value="topology">拓扑视图</option>
            <option value="dependencies">依赖视图</option>
            <option value="traffic">流量视图</option>
          </Select>
          <Button>刷新</Button>
        </div>
      </div>

      {/* 服务概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">服务总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{services.length}</p>
            <p className="text-sm text-gray-500 mt-1">活跃服务</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">健康服务</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {services.filter(s => s.status === 'healthy').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">正常运行</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告服务</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">
              {services.filter(s => s.status === 'warning').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">需要关注</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">严重服务</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {services.filter(s => s.status === 'critical').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">立即处理</p>
          </CardContent>
        </Card>
      </div>

      {/* 服务拓扑图 */}
      <Card>
        <CardHeader>
          <CardTitle>服务拓扑图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">服务拓扑图 (使用D3.js/Cytoscape.js渲染)</p>
          </div>
          <div className="mt-4 flex gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span>前端服务</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full" />
              <span>后端服务</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-500 rounded-full" />
              <span>数据库</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span>缓存</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-pink-500 rounded-full" />
              <span>队列</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 服务列表 */}
      <Card>
        <CardHeader>
          <CardTitle>服务列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service) => (
              <div
                key={service.id}
                className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${
                  selectedService?.id === service.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
                onClick={() => setSelectedService(service)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{service.name}</h4>
                  <Badge className={getStatusColor(service.status)}>
                    {service.status === 'healthy' ? '健康' : service.status === 'warning' ? '警告' : '严重'}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <Badge className={getTypeColor(service.type)} variant="outline">
                    {getTypeLabel(service.type)}
                  </Badge>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>请求量</span>
                    <span className="font-medium">{service.metrics.requests}/s</span>
                  </div>
                  <div className="flex justify-between">
                    <span>错误率</span>
                    <span className={`font-medium ${service.metrics.errorRate > 1 ? 'text-red-600' : 'text-green-600'}`}>
                      {service.metrics.errorRate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>延迟</span>
                    <span className="font-medium">{service.metrics.latency}ms</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 服务详情 */}
      {selectedService && (
        <Card>
          <CardHeader>
            <CardTitle>服务详情: {selectedService.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* 基本信息 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 border border-gray-200 rounded-lg">
                  <h4 className="font-medium mb-2">基本信息</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">服务ID</span>
                      <span className="font-mono">{selectedService.id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">服务类型</span>
                      <span>{getTypeLabel(selectedService.type)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">状态</span>
                      <Badge className={getStatusColor(selectedService.status)}>
                        {selectedService.status === 'healthy' ? '健康' : selectedService.status === 'warning' ? '警告' : '严重'}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div className="p-4 border border-gray-200 rounded-lg">
                  <h4 className="font-medium mb-2">性能指标</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">请求量</span>
                      <span className="font-medium">{selectedService.metrics.requests}/s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">错误率</span>
                      <span className={`font-medium ${selectedService.metrics.errorRate > 1 ? 'text-red-600' : 'text-green-600'}`}>
                        {selectedService.metrics.errorRate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">平均延迟</span>
                      <span className="font-medium">{selectedService.metrics.latency}ms</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 依赖关系 */}
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-3">依赖服务 ({selectedService.dependencies.length})</h4>
                {selectedService.dependencies.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {selectedService.dependencies.map((depId) => {
                      const depService = services.find(s => s.id === depId);
                      return depService ? (
                        <Badge key={depId} variant="outline" className="cursor-pointer">
                          {depService.name}
                        </Badge>
                      ) : null;
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">无依赖服务</p>
                )}
              </div>

              {/* 流量详情 */}
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-3">流量详情</h4>
                <div className="space-y-2">
                  {dependencies
                    .filter(d => d.from === selectedService.name || d.to === selectedService.name)
                    .map((dep, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{dep.from}</span>
                          <span className="text-gray-400">→</span>
                          <span className="font-medium">{dep.to}</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <Badge variant="outline">{dep.type}</Badge>
                          <span className="text-gray-600">{dep.traffic}/s</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button>查看日志</Button>
                <Button variant="outline">查看指标</Button>
                <Button variant="outline">追踪链路</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
