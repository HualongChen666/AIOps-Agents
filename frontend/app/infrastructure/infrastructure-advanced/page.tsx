'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface InfrastructureResource {
  resource_id: string;
  name: string;
  resource_type: string;
  provider: string;
  region: string;
  status: string;
  cpu_cores: number;
  memory_gb: number;
  disk_gb: number;
  tags: Record<string, string>;
  created_at: string;
  updated_at: string;
}

interface TopologyNode {
  node_id: string;
  name: string;
  node_type: string;
  parent_id: string | null;
  children: string[];
  metadata: Record<string, any>;
}

interface TopologyEdge {
  edge_id: string;
  source_id: string;
  target_id: string;
  relationship_type: string;
  metadata: Record<string, any>;
}

interface InfrastructureTopology {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  last_updated: string;
}

interface HealthCheck {
  component_id: string;
  component_name: string;
  status: string;
  health_score: number;
  last_check: string;
  metrics: Record<string, any>;
}

interface InfrastructureHealth {
  overall_status: string;
  overall_health_score: number;
  components: HealthCheck[];
  last_updated: string;
}

interface CapacityMetrics {
  resource_id: string;
  resource_name: string;
  cpu_usage_percent: number;
  memory_usage_percent: number;
  disk_usage_percent: number;
  network_usage_mbps: number;
  forecast_cpu_usage?: number;
  forecast_memory_usage?: number;
  forecast_disk_usage?: number;
}

interface InfrastructureCapacity {
  total_resources: number;
  capacity_metrics: CapacityMetrics[];
  recommendations: string[];
  last_updated: string;
}

export default function InfrastructureAdvancedPage() {
  const [resources, setResources] = useState<InfrastructureResource[]>([]);
  const [topology, setTopology] = useState<InfrastructureTopology | null>(null);
  const [health, setHealth] = useState<InfrastructureHealth | null>(null);
  const [capacity, setCapacity] = useState<InfrastructureCapacity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newResource, setNewResource] = useState({
    name: '',
    resource_type: 'virtual_machine',
    provider: 'aws',
    region: 'us-east-1',
    cpu_cores: 2,
    memory_gb: 4,
    disk_gb: 20
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [resourcesRes, topologyRes, healthRes, capacityRes] = await Promise.all([
        api.get('/api/v1/infrastructure/resources'),
        api.get('/api/v1/infrastructure/topology'),
        api.get('/api/v1/infrastructure/health'),
        api.get('/api/v1/infrastructure/capacity')
      ]);
      setResources(resourcesRes.data || []);
      setTopology(topologyRes.data);
      setHealth(healthRes.data);
      setCapacity(capacityRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateResource = async () => {
    try {
      setError(null);
      await api.post('/api/v1/infrastructure/resources', newResource);
      setShowCreateForm(false);
      setNewResource({
        name: '',
        resource_type: 'virtual_machine',
        provider: 'aws',
        region: 'us-east-1',
        cpu_cores: 2,
        memory_gb: 4,
        disk_gb: 20
      });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建资源失败');
    }
  };

  const handleDeleteResource = async (resourceId: string) => {
    if (!confirm('确定要删除此资源吗？')) return;

    try {
      setError(null);
      await api.delete(`/api/v1/infrastructure/resources/${resourceId}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除资源失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running': return 'default';
      case 'stopped': return 'secondary';
      case 'error': return 'destructive';
      case 'provisioning': return 'secondary';
      default: return 'outline';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级基础设施管理</h1>
        <div className="flex gap-2">
          <Button onClick={() => setShowCreateForm(!showCreateForm)}>
            {showCreateForm ? '取消' : '创建资源'}
          </Button>
          <Button onClick={fetchData} variant="outline">刷新</Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 创建资源表单 */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>创建新资源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
                <input
                  type="text"
                  value={newResource.name}
                  onChange={(e) => setNewResource({ ...newResource, name: e.target.value })}
                  className="w-full border rounded-md p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">资源类型</label>
                <select
                  value={newResource.resource_type}
                  onChange={(e) => setNewResource({ ...newResource, resource_type: e.target.value })}
                  className="w-full border rounded-md p-2"
                >
                  <option value="virtual_machine">虚拟机</option>
                  <option value="database">数据库</option>
                  <option value="storage">存储</option>
                  <option value="network">网络</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">提供商</label>
                <select
                  value={newResource.provider}
                  onChange={(e) => setNewResource({ ...newResource, provider: e.target.value })}
                  className="w-full border rounded-md p-2"
                >
                  <option value="aws">AWS</option>
                  <option value="azure">Azure</option>
                  <option value="gcp">GCP</option>
                  <option value="alibaba">阿里云</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">区域</label>
                <input
                  type="text"
                  value={newResource.region}
                  onChange={(e) => setNewResource({ ...newResource, region: e.target.value })}
                  className="w-full border rounded-md p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CPU核心</label>
                <input
                  type="number"
                  value={newResource.cpu_cores}
                  onChange={(e) => setNewResource({ ...newResource, cpu_cores: parseInt(e.target.value) })}
                  className="w-full border rounded-md p-2"
                  min="1"
                  max="128"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">内存 (GB)</label>
                <input
                  type="number"
                  value={newResource.memory_gb}
                  onChange={(e) => setNewResource({ ...newResource, memory_gb: parseInt(e.target.value) })}
                  className="w-full border rounded-md p-2"
                  min="1"
                  max="512"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">磁盘 (GB)</label>
                <input
                  type="number"
                  value={newResource.disk_gb}
                  onChange={(e) => setNewResource({ ...newResource, disk_gb: parseInt(e.target.value) })}
                  className="w-full border rounded-md p-2"
                  min="10"
                  max="10000"
                />
              </div>
            </div>
            <div className="mt-4">
              <Button onClick={handleCreateResource} className="w-full">创建资源</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 健康状态 */}
      {health && (
        <Card>
          <CardHeader>
            <CardTitle>基础设施健康状态</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="text-sm text-gray-500">整体状态</div>
                <Badge variant={health.overall_status === 'healthy' ? 'default' : 'destructive'}>
                  {health.overall_status}
                </Badge>
              </div>
              <div>
                <div className="text-sm text-gray-500">健康评分</div>
                <div className="text-2xl font-semibold">{health.overall_health_score.toFixed(1)}</div>
              </div>
            </div>
            <div className="space-y-2">
              {health.components.map((component) => (
                <div key={component.component_id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{component.component_name}</div>
                      <div className="text-sm text-gray-500">健康评分: {component.health_score.toFixed(1)}</div>
                    </div>
                    <Badge variant={component.status === 'healthy' ? 'default' : 'destructive'}>
                      {component.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 容量统计 */}
      {capacity && (
        <Card>
          <CardHeader>
            <CardTitle>容量统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="text-sm text-gray-500">总资源数</div>
                <div className="text-2xl font-semibold">{capacity.total_resources}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">建议数量</div>
                <div className="text-2xl font-semibold">{capacity.recommendations.length}</div>
              </div>
            </div>
            {capacity.recommendations.length > 0 && (
              <div className="mb-4">
                <div className="text-sm font-medium text-gray-700 mb-2">优化建议:</div>
                <ul className="text-sm text-gray-600 list-disc list-inside">
                  {capacity.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="space-y-2">
              {capacity.capacity_metrics.map((metric) => (
                <div key={metric.resource_id} className="border rounded-lg p-3">
                  <div className="font-semibold mb-2">{metric.resource_name}</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">CPU: </span>
                      <span className={metric.cpu_usage_percent > 80 ? 'text-red-600 font-semibold' : ''}>
                        {metric.cpu_usage_percent.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">内存: </span>
                      <span className={metric.memory_usage_percent > 80 ? 'text-red-600 font-semibold' : ''}>
                        {metric.memory_usage_percent.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">磁盘: </span>
                      <span className={metric.disk_usage_percent > 70 ? 'text-red-600 font-semibold' : ''}>
                        {metric.disk_usage_percent.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">网络: </span>
                      {metric.network_usage_mbps.toFixed(1)} Mbps
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 资源列表 */}
      <Card>
        <CardHeader>
          <CardTitle>基础设施资源 ({resources.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {resources.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无资源</div>
          ) : (
            <div className="space-y-3">
              {resources.map((resource) => (
                <div key={resource.resource_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{resource.name}</h3>
                    <Badge variant={getStatusColor(resource.status)}>{resource.status}</Badge>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600 mb-2">
                    <div>类型: {resource.resource_type}</div>
                    <div>提供商: {resource.provider}</div>
                    <div>区域: {resource.region}</div>
                    <div>CPU: {resource.cpu_cores}核</div>
                    <div>内存: {resource.memory_gb}GB</div>
                    <div>磁盘: {resource.disk_gb}GB</div>
                  </div>
                  {Object.keys(resource.tags).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {Object.entries(resource.tags).map(([key, value]) => (
                        <Badge key={key} variant="outline" className="text-xs">
                          {key}: {value}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDeleteResource(resource.resource_id)}
                  >
                    删除
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 拓扑图 */}
      {topology && (
        <Card>
          <CardHeader>
            <CardTitle>基础设施拓扑</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="text-sm text-gray-500">节点数</div>
                <div className="text-2xl font-semibold">{topology.nodes.length}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">连接数</div>
                <div className="text-2xl font-semibold">{topology.edges.length}</div>
              </div>
            </div>
            <div className="space-y-2">
              {topology.nodes.map((node) => (
                <div key={node.node_id} className="border rounded-lg p-3">
                  <div className="font-semibold">{node.name}</div>
                  <div className="text-sm text-gray-500">
                    类型: {node.node_type} | 父节点: {node.parent_id || '无'}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
