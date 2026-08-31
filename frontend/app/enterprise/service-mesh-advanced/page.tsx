'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MeshConfiguration {
  id: string;
  name: string;
  mesh_type: string;
  namespace: string;
  profile: string;
  auto_injection_enabled: boolean;
  mtls_enabled: boolean;
  resource_limits: Record<string, any>;
  status: string;
  mesh_id: string;
  created_at: string;
  updated_at: string;
}

interface TrafficRule {
  id: string;
  name: string;
  service_name: string;
  match_conditions: Record<string, any>;
  destination: Record<string, any>;
  weight: number;
  timeout_seconds: number;
  retry_policy: Record<string, any> | null;
  fault_injection: Record<string, any> | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface SecurityPolicy {
  id: string;
  name: string;
  policy_type: string;
  target_service: string;
  mtls_mode: string;
  allowed_principals: string[];
  denied_principals: string[];
  jwt_validation: Record<string, any> | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface ObservabilityConfig {
  id: string;
  name: string;
  tracing_enabled: boolean;
  metrics_enabled: boolean;
  access_logging_enabled: boolean;
  sampling_rate: number;
  prometheus_enabled: boolean;
  grafana_enabled: boolean;
  created_at: string;
  updated_at: string;
}

type TabType = 'configurations' | 'traffic' | 'security' | 'observability';

export default function ServiceMeshAdvancedPage() {
  const [activeTab, setActiveTab] = useState<TabType>('configurations');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [configurations, setConfigurations] = useState<MeshConfiguration[]>([]);
  const [trafficRules, setTrafficRules] = useState<TrafficRule[]>([]);
  const [securityPolicies, setSecurityPolicies] = useState<SecurityPolicy[]>([]);
  const [observabilityConfigs, setObservabilityConfigs] = useState<ObservabilityConfig[]>([]);

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
        case 'configurations':
          await fetchConfigurations();
          break;
        case 'traffic':
          await fetchTrafficRules();
          break;
        case 'security':
          await fetchSecurityPolicies();
          break;
        case 'observability':
          await fetchObservabilityConfigs();
          break;
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchConfigurations = async () => {
    const res = await api.get('/api/v1/service-mesh/configurations');
    setConfigurations(res.data.data?.configurations || []);
  };

  const fetchTrafficRules = async () => {
    const res = await api.get('/api/v1/service-mesh/traffic');
    setTrafficRules(res.data.data?.traffic_rules || []);
  };

  const fetchSecurityPolicies = async () => {
    const res = await api.get('/api/v1/service-mesh/security');
    setSecurityPolicies(res.data.data?.policies || []);
  };

  const fetchObservabilityConfigs = async () => {
    // Mock data for observability configs
    const mockConfigs: ObservabilityConfig[] = [
      {
        id: '1',
        name: 'default-observability',
        tracing_enabled: true,
        metrics_enabled: true,
        access_logging_enabled: true,
        sampling_rate: 1.0,
        prometheus_enabled: true,
        grafana_enabled: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];
    setObservabilityConfigs(mockConfigs);
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      let endpoint = '';
      let data = formData;

      switch (activeTab) {
        case 'configurations':
          endpoint = '/api/v1/service-mesh/configurations';
          break;
        case 'traffic':
          endpoint = '/api/v1/service-mesh/traffic';
          break;
        case 'security':
          endpoint = '/api/v1/service-mesh/security';
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
        case 'configurations':
          endpoint = `/api/v1/service-mesh/configurations/${id}`;
          break;
        case 'traffic':
          endpoint = `/api/v1/service-mesh/traffic/${id}`;
          break;
        case 'security':
          endpoint = `/api/v1/service-mesh/security/${id}`;
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
        case 'configurations':
          endpoint = `/api/v1/service-mesh/configurations/${id}`;
          break;
        case 'traffic':
          endpoint = `/api/v1/service-mesh/traffic/${id}`;
          break;
        case 'security':
          endpoint = `/api/v1/service-mesh/security/${id}`;
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

  const handleToggleEnabled = async (id: string, currentEnabled: boolean) => {
    try {
      setLoading(true);
      let endpoint = '';
      let data = { enabled: !currentEnabled };

      switch (activeTab) {
        case 'traffic':
          endpoint = `/api/v1/service-mesh/traffic/${id}`;
          break;
        case 'security':
          endpoint = `/api/v1/service-mesh/security/${id}`;
          break;
        default:
          return;
      }

      await api.patch(endpoint, data);
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
      case 'running':
        return 'bg-green-500';
      case 'degraded':
      case 'warning':
        return 'bg-yellow-500';
      case 'inactive':
      case 'stopped':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading && !configurations.length && !trafficRules.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级服务网格</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {(['configurations', 'traffic', 'security', 'observability'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {activeTab === 'configurations' && '网格配置'}
              {activeTab === 'traffic' && '流量规则'}
              {activeTab === 'security' && '安全策略'}
              {activeTab === 'observability' && '可观测性配置'}
            </CardTitle>
            {activeTab !== 'observability' && (
              <Button onClick={() => setShowCreateForm(true)}>创建</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : (
            <div className="space-y-4">
              {/* Configurations List */}
              {activeTab === 'configurations' && configurations.map((config) => (
                <div key={config.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getStatusColor(config.status)}`} />
                        <h3 className="font-semibold">{config.name}</h3>
                        <Badge variant={config.status === 'active' ? 'default' : 'secondary'}>
                          {config.status}
                        </Badge>
                        <Badge variant="outline">{config.mesh_type}</Badge>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        命名空间: {config.namespace} | Profile: {config.profile}
                      </div>
                      <div className="text-sm text-gray-500">
                        Mesh ID: {config.mesh_id}
                      </div>
                      <div className="text-sm text-gray-500">
                        自动注入: {config.auto_injection_enabled ? '启用' : '禁用'} | 
                        mTLS: {config.mtls_enabled ? '启用' : '禁用'}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        创建: {new Date(config.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setFormData({ name: config.name, namespace: config.namespace });
                          setShowCreateForm(true);
                        }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(config.id)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Traffic Rules List */}
              {activeTab === 'traffic' && trafficRules.map((rule) => (
                <div key={rule.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold">{rule.name}</h3>
                        <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                          {rule.enabled ? '启用' : '禁用'}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-500">服务: {rule.service_name}</div>
                      <div className="text-sm text-gray-500">权重: {rule.weight}%</div>
                      <div className="text-sm text-gray-500">超时: {rule.timeout_seconds}s</div>
                      {rule.retry_policy && (
                        <div className="text-sm text-gray-500">重试策略: 已配置</div>
                      )}
                      {rule.fault_injection && (
                        <div className="text-sm text-gray-500">故障注入: 已配置</div>
                      )}
                      <div className="text-xs text-gray-400 mt-1">
                        创建: {new Date(rule.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleEnabled(rule.id, rule.enabled)}
                      >
                        {rule.enabled ? '禁用' : '启用'}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(rule.id)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Security Policies List */}
              {activeTab === 'security' && securityPolicies.map((policy) => (
                <div key={policy.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold">{policy.name}</h3>
                        <Badge variant={policy.enabled ? 'default' : 'secondary'}>
                          {policy.enabled ? '启用' : '禁用'}
                        </Badge>
                      </div>
                  <div className="text-sm text-gray-500">类型: {policy.policy_type}</div>
                  <div className="text-sm text-gray-500">目标: {policy.target_service}</div>
                  <div className="text-sm text-gray-500">mTLS模式: {policy.mtls_mode}</div>
                  {policy.allowed_principals.length > 0 && (
                    <div className="text-sm text-gray-500">
                      允许主体: {policy.allowed_principals.length}
                    </div>
                  )}
                  {policy.jwt_validation && (
                    <div className="text-sm text-gray-500">JWT验证: 已配置</div>
                  )}
                  <div className="text-xs text-gray-400 mt-1">
                    创建: {new Date(policy.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleToggleEnabled(policy.id, policy.enabled)}
                  >
                    {policy.enabled ? '禁用' : '启用'}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDelete(policy.id)}
                  >
                    删除
                  </Button>
                </div>
              </div>
            </div>
          ))}

          {/* Observability Configs List */}
          {activeTab === 'observability' && observabilityConfigs.map((config) => (
            <div key={config.id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{config.name}</h3>
                  <div className="text-sm text-gray-500">
                    链路追踪: {config.tracing_enabled ? '启用' : '禁用'}
                  </div>
                  <div className="text-sm text-gray-500">
                    指标: {config.metrics_enabled ? '启用' : '禁用'}
                  </div>
                  <div className="text-sm text-gray-500">
                    访问日志: {config.access_logging_enabled ? '启用' : '禁用'}
                  </div>
                  <div className="text-sm text-gray-500">
                    采样率: {(config.sampling_rate * 100).toFixed(0)}%
                  </div>
                  <div className="text-sm text-gray-500">
                    Prometheus: {config.prometheus_enabled ? '启用' : '禁用'}
                  </div>
                  <div className="text-sm text-gray-500">
                    Grafana: {config.grafana_enabled ? '启用' : '禁用'}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Empty State */}
          {activeTab === 'configurations' && configurations.length === 0 && (
            <div className="text-center py-8 text-gray-500">暂无网格配置</div>
          )}
          {activeTab === 'traffic' && trafficRules.length === 0 && (
            <div className="text-center py-8 text-gray-500">暂无流量规则</div>
          )}
          {activeTab === 'security' && securityPolicies.length === 0 && (
            <div className="text-center py-8 text-gray-500">暂无安全策略</div>
          )}
          {activeTab === 'observability' && observabilityConfigs.length === 0 && (
            <div className="text-center py-8 text-gray-500">暂无可观测性配置</div>
          )}
        </div>
      )}
    </CardContent>
  </Card>

  {/* Create Form Modal */}
  {showCreateForm && (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">创建{activeTab}</h2>
        <div className="space-y-4">
          {activeTab === 'configurations' && (
            <>
              <input
                type="text"
                placeholder="配置名称"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
              <select
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, mesh_type: e.target.value })}
              >
                <option value="istio">Istio</option>
                <option value="linkerd">Linkerd</option>
                <option value="consul">Consul</option>
              </select>
              <input
                type="text"
                placeholder="命名空间"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, namespace: e.target.value })}
              />
              <select
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, profile: e.target.value })}
              >
                <option value="default">Default</option>
                <option value="demo">Demo</option>
                <option value="minimal">Minimal</option>
                <option value="preview">Preview</option>
              </select>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="auto-injection"
                  className="rounded"
                  onChange={(e) => setFormData({ ...formData, auto_injection_enabled: e.target.checked })}
                />
                <label htmlFor="auto-injection">启用自动注入</label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="mtls"
                  className="rounded"
                  onChange={(e) => setFormData({ ...formData, mtls_enabled: e.target.checked })}
                />
                <label htmlFor="mtls">启用mTLS</label>
              </div>
            </>
          )}
          {activeTab === 'traffic' && (
            <>
              <input
                type="text"
                placeholder="规则名称"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
              <input
                type="text"
                placeholder="服务名称"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, service_name: e.target.value })}
              />
              <input
                type="text"
                placeholder="匹配条件 (JSON)"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, match_conditions: JSON.parse(e.target.value) })}
              />
              <input
                type="text"
                placeholder="目标配置 (JSON)"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, destination: JSON.parse(e.target.value) })}
              />
              <input
                type="number"
                placeholder="权重 (0-100)"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, weight: parseInt(e.target.value) })}
              />
              <input
                type="number"
                placeholder="超时(秒)"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, timeout_seconds: parseInt(e.target.value) })}
              />
            </>
          )}
          {activeTab === 'security' && (
            <>
              <input
                type="text"
                placeholder="策略名称"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
              <select
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, policy_type: e.target.value })}
              >
                <option value="authentication">认证</option>
                <option value="authorization">授权</option>
                <option value="security">安全</option>
              </select>
              <input
                type="text"
                placeholder="目标服务"
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, target_service: e.target.value })}
              />
              <select
                className="w-full border rounded px-3 py-2"
                onChange={(e) => setFormData({ ...formData, mtls_mode: e.target.value })}
              >
                <option value="STRICT">STRICT</option>
                <option value="PERMISSIVE">PERMISSIVE</option>
                <option value="DISABLE">DISABLE</option>
              </select>
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
