'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MeshService {
  id: string;
  name: string;
  mesh_type: string;
  namespace: string;
  status: string;
  version: string;
  pods: number;
  created_at: string;
}

interface TrafficRule {
  id: string;
  name: string;
  service_name: string;
  match: string;
  destination: string;
  weight: number;
  status: string;
}

interface SecurityPolicy {
  id: string;
  name: string;
  policy_type: string;
  target_service: string;
  mtls_mode: string;
  status: string;
}

export default function ServiceMeshPage() {
  const [services, setServices] = useState<MeshService[]>([]);
  const [trafficRules, setTrafficRules] = useState<TrafficRule[]>([]);
  const [securityPolicies, setSecurityPolicies] = useState<SecurityPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'services' | 'traffic' | 'security'>('services');

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'services') {
        await fetchServices();
      } else if (activeTab === 'traffic') {
        await fetchTrafficRules();
      } else {
        await fetchSecurityPolicies();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchServices = async () => {
    // Mock data for basic service mesh page
    const mockServices: MeshService[] = [
      {
        id: '1',
        name: 'api-gateway',
        mesh_type: 'istio',
        namespace: 'default',
        status: 'running',
        version: '1.0.0',
        pods: 3,
        created_at: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'user-service',
        mesh_type: 'istio',
        namespace: 'default',
        status: 'running',
        version: '2.1.0',
        pods: 2,
        created_at: new Date().toISOString(),
      },
      {
        id: '3',
        name: 'order-service',
        mesh_type: 'istio',
        namespace: 'production',
        status: 'degraded',
        version: '1.5.0',
        pods: 1,
        created_at: new Date().toISOString(),
      },
    ];
    setServices(mockServices);
  };

  const fetchTrafficRules = async () => {
    try {
      const res = await api.get('/api/v1/service-mesh/traffic');
      setTrafficRules(res.data.data?.traffic_rules || []);
    } catch (err) {
      // Fallback to mock data
      const mockRules: TrafficRule[] = [
        {
          id: '1',
          name: 'api-gateway-canary',
          service_name: 'api-gateway',
          match: 'headers[x-canary]',
          destination: 'api-gateway-v2',
          weight: 20,
          status: 'active',
        },
        {
          id: '2',
          name: 'user-service-blue-green',
          service_name: 'user-service',
          match: 'headers[x-env]',
          destination: 'user-service-green',
          weight: 50,
          status: 'active',
        },
      ];
      setTrafficRules(mockRules);
    }
  };

  const fetchSecurityPolicies = async () => {
    try {
      const res = await api.get('/api/v1/service-mesh/security');
      setSecurityPolicies(res.data.data?.policies || []);
    } catch (err) {
      // Fallback to mock data
      const mockPolicies: SecurityPolicy[] = [
        {
          id: '1',
          name: 'mtls-strict',
          policy_type: 'authentication',
          target_service: '*',
          mtls_mode: 'STRICT',
          status: 'enabled',
        },
        {
          id: '2',
          name: 'user-service-authz',
          policy_type: 'authorization',
          target_service: 'user-service',
          mtls_mode: 'PERMISSIVE',
          status: 'enabled',
        },
      ];
      setSecurityPolicies(mockPolicies);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
      case 'active':
      case 'enabled':
        return 'bg-green-500';
      case 'degraded':
      case 'warning':
        return 'bg-yellow-500';
      case 'stopped':
      case 'inactive':
      case 'disabled':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading && !services.length && !trafficRules.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务网格</h1>
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
          网格服务
        </button>
        <button
          onClick={() => setActiveTab('traffic')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'traffic'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          流量管理
        </button>
        <button
          onClick={() => setActiveTab('security')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'security'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          安全策略
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{services.length}</div>
            <div className="text-sm text-gray-500">网格服务</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {services.filter(s => s.status === 'running').length}
            </div>
            <div className="text-sm text-gray-500">运行中</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{trafficRules.length}</div>
            <div className="text-sm text-gray-500">流量规则</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{securityPolicies.length}</div>
            <div className="text-sm text-gray-500">安全策略</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {activeTab === 'services' && '网格服务列表'}
            {activeTab === 'traffic' && '流量规则'}
            {activeTab === 'security' && '安全策略'}
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
                        <Badge variant={service.status === 'running' ? 'default' : 'secondary'}>
                          {service.status}
                        </Badge>
                        <Badge variant="outline">{service.mesh_type}</Badge>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        命名空间: {service.namespace}
                      </div>
                      <div className="text-sm text-gray-500">
                        版本: {service.version} | Pod数: {service.pods}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        创建时间: {new Date(service.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {activeTab === 'traffic' && trafficRules.map((rule) => (
                <div key={rule.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold">{rule.name}</h3>
                        <Badge variant={rule.status === 'active' ? 'default' : 'secondary'}>
                          {rule.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500">服务: {rule.service_name}</div>
                      <div className="text-sm text-gray-500">匹配: {rule.match}</div>
                      <div className="text-sm text-gray-500">目标: {rule.destination}</div>
                      <div className="text-sm text-gray-500">权重: {rule.weight}%</div>
                    </div>
                  </div>
                </div>
              ))}

              {activeTab === 'security' && securityPolicies.map((policy) => (
                <div key={policy.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold">{policy.name}</h3>
                        <Badge variant={policy.status === 'enabled' ? 'default' : 'secondary'}>
                          {policy.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500">类型: {policy.policy_type}</div>
                      <div className="text-sm text-gray-500">目标: {policy.target_service}</div>
                      <div className="text-sm text-gray-500">mTLS模式: {policy.mtls_mode}</div>
                    </div>
                  </div>
                </div>
              ))}

              {activeTab === 'services' && services.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无网格服务</div>
              )}
              {activeTab === 'traffic' && trafficRules.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无流量规则</div>
              )}
              {activeTab === 'security' && securityPolicies.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无安全策略</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
