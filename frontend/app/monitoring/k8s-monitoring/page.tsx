'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface PodInfo {
  name?: string;
  namespace?: string;
  status?: string;
  node?: string;
  cpu_usage?: number;
  memory_usage_mb?: number;
  restarts?: number;
  age?: string;
  [key: string]: any;
}

interface NodeInfo {
  name?: string;
  status?: string;
  cpu_capacity?: number;
  cpu_usage?: number;
  memory_capacity_gb?: number;
  memory_usage_gb?: number;
  pods_capacity?: number;
  pods_running?: number;
  [key: string]: any;
}

interface K8sMonitoringData {
  cluster_name?: string;
  kubernetes_version?: string;
  total_nodes?: number;
  total_pods?: number;
  running_pods?: number;
  pending_pods?: number;
  failed_pods?: number;
  nodes?: NodeInfo[];
  pods?: PodInfo[];
  namespaces?: string[];
  [key: string]: any;
}

export default function K8sMonitoringPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNamespace, setSelectedNamespace] = useState('all');
  const [viewType, setViewType] = useState('pods');

  const { data: k8sData, isLoading, error, refetch } = useQuery<K8sMonitoringData>({
    queryKey: ['monitoring-k8s-monitoring', selectedNamespace],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/k8s-monitoring', {
        params: selectedNamespace !== 'all' ? { namespace: selectedNamespace } : {}
      });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const filteredPods = k8sData?.pods?.filter(p =>
    p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.namespace?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const filteredNodes = k8sData?.nodes?.filter(n =>
    n.name?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const handlePodAction = async (podName: string, namespace: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/k8s-monitoring/pod-action', {
        pod_name: podName,
        namespace,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform pod action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Kubernetes监控</h1>
        <div className="flex gap-2">
          <Select value={selectedNamespace} onChange={(e) => setSelectedNamespace(e.target.value)}>
            <option value="all">所有命名空间</option>
            {k8sData?.namespaces?.map(ns => (
              <option key={ns} value={ns}>{ns}</option>
            ))}
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>集群信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">集群名称:</span>
              <span className="font-medium">{k8sData?.cluster_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Kubernetes版本:</span>
              <span className="font-medium">{k8sData?.kubernetes_version || '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">节点数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{k8sData?.total_nodes || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总Pod数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{k8sData?.total_pods || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{k8sData?.running_pods || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">异常Pod</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {(k8sData?.pending_pods || 0) + (k8sData?.failed_pods || 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>视图切换</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button
              variant={viewType === 'pods' ? 'default' : 'outline'}
              onClick={() => setViewType('pods')}
            >
              Pods
            </Button>
            <Button
              variant={viewType === 'nodes' ? 'default' : 'outline'}
              onClick={() => setViewType('nodes')}
            >
              Nodes
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{viewType === 'pods' ? 'Pod列表' : '节点列表'}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={viewType === 'pods' ? '搜索Pod名称或命名空间...' : '搜索节点名称...'}
              className="mb-4"
            />
            <div className="max-h-96 overflow-auto">
              {viewType === 'pods' ? (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left">名称</th>
                      <th className="px-4 py-2 text-left">命名空间</th>
                      <th className="px-4 py-2 text-left">状态</th>
                      <th className="px-4 py-2 text-left">节点</th>
                      <th className="px-4 py-2 text-left">CPU</th>
                      <th className="px-4 py-2 text-left">内存</th>
                      <th className="px-4 py-2 text-left">重启次数</th>
                      <th className="px-4 py-2 text-left">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPods.map((pod, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-4 py-2">{pod.name}</td>
                        <td className="px-4 py-2">{pod.namespace}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            pod.status === 'Running' ? 'bg-green-100 text-green-800' : 
                            pod.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {pod.status}
                          </span>
                        </td>
                        <td className="px-4 py-2">{pod.node}</td>
                        <td className="px-4 py-2">{pod.cpu_usage?.toFixed(2)}%</td>
                        <td className="px-4 py-2">{pod.memory_usage_mb?.toFixed(2)} MB</td>
                        <td className="px-4 py-2">{pod.restarts}</td>
                        <td className="px-4 py-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => pod.name && pod.namespace && handlePodAction(pod.name, pod.namespace, 'restart')}
                          >
                            重启
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left">名称</th>
                      <th className="px-4 py-2 text-left">状态</th>
                      <th className="px-4 py-2 text-left">CPU使用率</th>
                      <th className="px-4 py-2 text-left">内存使用率</th>
                      <th className="px-4 py-2 text-left">Pod容量</th>
                      <th className="px-4 py-2 text-left">运行Pod</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredNodes.map((node, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-4 py-2">{node.name}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            node.status === 'Ready' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {node.status}
                          </span>
                        </td>
                        <td className="px-4 py-2">
                          {node.cpu_usage && node.cpu_capacity ? ((node.cpu_usage / node.cpu_capacity) * 100).toFixed(2) : '-'}%
                        </td>
                        <td className="px-4 py-2">
                          {node.memory_usage_gb && node.memory_capacity_gb ? ((node.memory_usage_gb / node.memory_capacity_gb) * 100).toFixed(2) : '-'}%
                        </td>
                        <td className="px-4 py-2">{node.pods_capacity || '-'}</td>
                        <td className="px-4 py-2">{node.pods_running || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
