'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Service {
  id: string;
  name: string;
  host: string;
  port: number;
  protocol: string;
  status: string;
  metadata: Record<string, any>;
  created_at: string;
}

interface ServiceInstance {
  instance_id: string;
  service_name: string;
  host: string;
  port: number;
  status: string;
  weight: number;
  last_heartbeat: string;
}

export default function ServiceDiscoveryPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [instances, setInstances] = useState<ServiceInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'services' | 'instances'>('services');

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'services') {
        await fetchServices();
      } else {
        await fetchInstances();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchServices = async () => {
    // Mock data for basic service discovery page
    const mockServices: Service[] = [
      {
        id: '1',
        name: 'api-gateway',
        host: 'api-gateway.default.svc.cluster.local',
        port: 8080,
        protocol: 'http',
        status: 'active',
        metadata: { version: '1.0.0', environment: 'production' },
        created_at: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'user-service',
        host: 'user-service.default.svc.cluster.local',
        port: 8081,
        protocol: 'http',
        status: 'active',
        metadata: { version: '2.1.0', environment: 'production' },
        created_at: new Date().toISOString(),
      },
      {
        id: '3',
        name: 'order-service',
        host: 'order-service.default.svc.cluster.local',
        port: 8082,
        protocol: 'http',
        status: 'degraded',
        metadata: { version: '1.5.0', environment: 'production' },
        created_at: new Date().toISOString(),
      },
    ];
    setServices(mockServices);
  };

  const fetchInstances = async () => {
    try {
      const res = await api.get('/api/v1/service-discovery/registrations');
      setInstances(res.data.data?.registrations || []);
    } catch (err) {
      // Fallback to mock data
      const mockInstances: ServiceInstance[] = [
        {
          instance_id: 'api-gateway-001',
          service_name: 'api-gateway',
          host: '10.0.1.10',
          port: 8080,
          status: 'healthy',
          weight: 100,
          last_heartbeat: new Date().toISOString(),
        },
        {
          instance_id: 'user-service-001',
          service_name: 'user-service',
          host: '10.0.1.11',
          port: 8081,
          status: 'healthy',
          weight: 100,
          last_heartbeat: new Date().toISOString(),
        },
        {
          instance_id: 'user-service-002',
          service_name: 'user-service',
          host: '10.0.1.12',
          port: 8081,
          status: 'healthy',
          weight: 50,
          last_heartbeat: new Date().toISOString(),
        },
      ];
      setInstances(mockInstances);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
      case 'warning':
        return 'bg-yellow-500';
      case 'inactive':
      case 'unhealthy':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading && !services.length && !instances.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务发现</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        <button
          onClick={() => setActiveTab('services')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'services'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          服务
        </button>
        <button
          onClick={() => setActiveTab('instances')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'instances'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          实例
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{services.length}</div>
            <div className="text-sm text-gray-500">总服务数</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {services.filter(s => s.status === 'active').length}
            </div>
            <div className="text-sm text-gray-500">活跃服务</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{instances.length}</div>
            <div className="text-sm text-gray-500">总实例数</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {instances.filter(i => i.status === 'healthy').length}
            </div>
            <div className="text-sm text-gray-500">健康实例</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {activeTab === 'services' ? '服务列表' : '实例列表'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : (
            <div className="space-y-4">
              {activeTab === 'services' && services.map((service) => (
                <div key={service.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getStatusColor(service.status)}`} />
                        <h3 className="font-semibold">{service.name}</h3>
                        <Badge variant={service.status === 'active' ? 'default' : 'secondary'}>
                          {service.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {service.protocol}://{service.host}:{service.port}
                      </div>
                      <div className="text-sm text-gray-500">
                        版本: {service.metadata.version} | 环境: {service.metadata.environment}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        创建时间: {new Date(service.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {activeTab === 'instances' && instances.map((instance) => (
                <div key={instance.instance_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getStatusColor(instance.status)}`} />
                        <h3 className="font-semibold">{instance.service_name}</h3>
                        <Badge variant={instance.status === 'healthy' ? 'default' : 'secondary'}>
                          {instance.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        实例ID: {instance.instance_id}
                      </div>
                      <div className="text-sm text-gray-500">
                        {instance.host}:{instance.port}
                      </div>
                      <div className="text-sm text-gray-500">
                        权重: {instance.weight}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        最后心跳: {new Date(instance.last_heartbeat).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {activeTab === 'services' && services.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无服务</div>
              )}
              {activeTab === 'instances' && instances.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无实例</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
