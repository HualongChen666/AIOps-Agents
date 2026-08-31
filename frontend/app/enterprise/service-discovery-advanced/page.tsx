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
  weight: number;
  created_at: string;
  updated_at: string;
}

interface HealthCheck {
  id: string;
  service_id: string;
  check_type: string;
  endpoint: string;
  interval_seconds: number;
  timeout_seconds: number;
  healthy_threshold: number;
  unhealthy_threshold: number;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ServiceRegistration {
  id: string;
  instance_id: string;
  service_name: string;
  host: string;
  port: number;
  status: string;
  weight: number;
  registered_at: string;
}

interface Endpoint {
  id: string;
  service_name: string;
  host: string;
  port: number;
  protocol: string;
  status: string;
  url: string;
}

type TabType = 'services' | 'health-checks' | 'registrations' | 'endpoints';

export default function ServiceDiscoveryAdvancedPage() {
  const [activeTab, setActiveTab] = useState<TabType>('services');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [services, setServices] = useState<Service[]>([]);
  const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([]);
  const [registrations, setRegistrations] = useState<ServiceRegistration[]>([]);
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);

  // Form states
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<Record<string, any>>({});

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      switch (activeTab) {
        case 'services':
          await fetchServices();
          break;
        case 'health-checks':
          await fetchHealthChecks();
          break;
        case 'registrations':
          await fetchRegistrations();
          break;
        case 'endpoints':
          await fetchEndpoints();
          break;
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchServices = async () => {
    const res = await api.get('/api/v1/service-discovery/services');
    setServices(res.data.data?.services || []);
  };

  const fetchHealthChecks = async () => {
    const res = await api.get('/api/v1/service-discovery/health-checks');
    setHealthChecks(res.data.data?.health_checks || []);
  };

  const fetchRegistrations = async () => {
    const res = await api.get('/api/v1/service-discovery/registrations');
    setRegistrations(res.data.data?.registrations || []);
  };

  const fetchEndpoints = async () => {
    const res = await api.get('/api/v1/service-discovery/endpoints');
    setEndpoints(res.data.data?.endpoints || []);
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      let endpoint = '';
      let data = formData;

      switch (activeTab) {
        case 'services':
          endpoint = '/api/v1/service-discovery/services';
          break;
        case 'health-checks':
          endpoint = '/api/v1/service-discovery/health-checks';
          break;
        case 'registrations':
          endpoint = '/api/v1/service-discovery/registrations';
          break;
        default:
          return;
      }

      await api.post(endpoint, data);
      setShowCreateForm(false);
      setFormData({});
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除吗？')) return;

    try {
      setLoading(true);
      let endpoint = '';

      switch (activeTab) {
        case 'services':
          endpoint = `/api/v1/service-discovery/services/${id}`;
          break;
        case 'health-checks':
          endpoint = `/api/v1/service-discovery/health-checks/${id}`;
          break;
        default:
          return;
      }

      await api.delete(endpoint);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      setLoading(true);
      let endpoint = '';

      switch (activeTab) {
        case 'services':
          endpoint = `/api/v1/service-discovery/services/${id}`;
          break;
        default:
          return;
      }

      await api.patch(endpoint, formData);
      setFormData({});
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新失败');
    } finally {
      setLoading(false);
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
      case 'pending':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading && !services.length && !healthChecks.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级服务发现</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {(['services', 'health-checks', 'registrations', 'endpoints'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </button>
        ))}
      </div>

      {/* Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {activeTab === 'services' && '服务管理'}
              {activeTab === 'health-checks' && '健康检查'}
              {activeTab === 'registrations' && '服务注册'}
              {activeTab === 'endpoints' && '服务端点'}
            </CardTitle>
            {activeTab !== 'endpoints' && (
              <Button onClick={() => setShowCreateForm(true)}>创建</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : (
            <div className="space-y-4">
              {/* Services List */}
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
                      <div className="text-sm text-gray-500">权重: {service.weight}</div>
                      <div className="text-xs text-gray-400 mt-1">
                        创建: {new Date(service.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setFormData({ name: service.name, host: service.host, port: service.port });
                          setShowCreateForm(true);
                        }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(service.id)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Health Checks List */}
              {activeTab === 'health-checks' && healthChecks.map((check) => (
                <div key={check.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getStatusColor(check.status)}`} />
                        <h3 className="font-semibold">健康检查: {check.id.substring(0, 8)}</h3>
                        <Badge variant={check.status === 'healthy' ? 'default' : 'secondary'}>
                          {check.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500">服务ID: {check.service_id}</div>
                      <div className="text-sm text-gray-500">类型: {check.check_type}</div>
                      <div className="text-sm text-gray-500">端点: {check.endpoint}</div>
                      <div className="text-sm text-gray-500">
                        间隔: {check.interval_seconds}s | 超时: {check.timeout_seconds}s
                      </div>
                      <div className="text-sm text-gray-500">
                        健康阈值: {check.healthy_threshold} | 不健康阈值: {check.unhealthy_threshold}
                      </div>
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(check.id)}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              ))}

              {/* Registrations List */}
              {activeTab === 'registrations' && registrations.map((reg) => (
                <div key={reg.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getStatusColor(reg.status)}`} />
                        <h3 className="font-semibold">{reg.service_name}</h3>
                        <Badge variant={reg.status === 'healthy' ? 'default' : 'secondary'}>
                          {reg.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500">实例ID: {reg.instance_id}</div>
                      <div className="text-sm text-gray-500">{reg.host}:{reg.port}</div>
                      <div className="text-sm text-gray-500">权重: {reg.weight}</div>
                      <div className="text-xs text-gray-400 mt-1">
                        注册时间: {new Date(reg.registered_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Endpoints List */}
              {activeTab === 'endpoints' && endpoints.map((endpoint) => (
                <div key={endpoint.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getStatusColor(endpoint.status)}`} />
                        <h3 className="font-semibold">{endpoint.service_name}</h3>
                        <Badge variant={endpoint.status === 'active' ? 'default' : 'secondary'}>
                          {endpoint.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500">{endpoint.url}</div>
                      <div className="text-sm text-gray-500">
                        {endpoint.host}:{endpoint.port}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Empty State */}
              {activeTab === 'services' && services.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无服务</div>
              )}
              {activeTab === 'health-checks' && healthChecks.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无健康检查</div>
              )}
              {activeTab === 'registrations' && registrations.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无注册</div>
              )}
              {activeTab === 'endpoints' && endpoints.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无端点</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-semibold mb-4">创建{activeTab.replace('-', ' ')}</h2>
            <div className="space-y-4">
              {activeTab === 'services' && (
                <>
                  <input
                    type="text"
                    placeholder="服务名称"
                    className="w-full border rounded px-3 py-2"
                    value={formData.name || ''}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="主机地址"
                    className="w-full border rounded px-3 py-2"
                    value={formData.host || ''}
                    onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  />
                  <input
                    type="number"
                    placeholder="端口"
                    className="w-full border rounded px-3 py-2"
                    value={formData.port || ''}
                    onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                  />
                  <select
                    className="w-full border rounded px-3 py-2"
                    value={formData.protocol || 'http'}
                    onChange={(e) => setFormData({ ...formData, protocol: e.target.value })}
                  >
                    <option value="http">HTTP</option>
                    <option value="https">HTTPS</option>
                    <option value="grpc">gRPC</option>
                    <option value="tcp">TCP</option>
                  </select>
                  <input
                    type="number"
                    placeholder="权重 (1-100)"
                    className="w-full border rounded px-3 py-2"
                    value={formData.weight || 1}
                    onChange={(e) => setFormData({ ...formData, weight: parseInt(e.target.value) })}
                  />
                </>
              )}
              {activeTab === 'health-checks' && (
                <>
                  <input
                    type="text"
                    placeholder="服务ID"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, service_id: e.target.value })}
                  />
                  <select
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, check_type: e.target.value })}
                  >
                    <option value="http">HTTP</option>
                    <option value="tcp">TCP</option>
                    <option value="grpc">gRPC</option>
                  </select>
                  <input
                    type="text"
                    placeholder="端点 (如: /health)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
                  />
                  <input
                    type="number"
                    placeholder="检查间隔(秒)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, interval_seconds: parseInt(e.target.value) })}
                  />
                  <input
                    type="number"
                    placeholder="超时(秒)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, timeout_seconds: parseInt(e.target.value) })}
                  />
                  <input
                    type="number"
                    placeholder="健康阈值"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, healthy_threshold: parseInt(e.target.value) })}
                  />
                  <input
                    type="number"
                    placeholder="不健康阈值"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, unhealthy_threshold: parseInt(e.target.value) })}
                  />
                </>
              )}
              {activeTab === 'registrations' && (
                <>
                  <input
                    type="text"
                    placeholder="服务名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, service_name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="实例ID"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, instance_id: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="主机地址"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  />
                  <input
                    type="number"
                    placeholder="端口"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                  />
                  <input
                    type="number"
                    placeholder="权重 (1-100)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, weight: parseInt(e.target.value) })}
                  />
                </>
              )}
            </div>
            <div className="flex justify-end space-x-2 mt-6">
              <Button variant="outline" onClick={() => { setShowCreateForm(false); setFormData({}); }}>取消</Button>
              <Button onClick={handleCreate}>创建</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
