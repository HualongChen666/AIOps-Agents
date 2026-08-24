'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ContainerInfo {
  id?: string;
  name?: string;
  image?: string;
  status?: string;
  cpu_percent?: number;
  memory_percent?: number;
  memory_mb?: number;
  network_rx_mb?: number;
  network_tx_mb?: number;
  uptime?: string;
  [key: string]: any;
}

interface DockerMonitoringData {
  containers?: ContainerInfo[];
  total_containers?: number;
  running_containers?: number;
  stopped_containers?: number;
  docker_version?: string;
  total_images?: number;
  [key: string]: any;
}

export default function DockerMonitoringPage() {
  const [searchQuery, setSearchQuery] = useState('');

  const { data: dockerData, isLoading, error, refetch } = useQuery<DockerMonitoringData>({
    queryKey: ['monitoring-docker-monitoring'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/docker-monitoring');
      return resp.data;
    },
    refetchInterval: 15000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const filteredContainers = dockerData?.containers?.filter(c =>
    c.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.image?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const handleContainerAction = async (containerId: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/docker-monitoring/container-action', {
        container_id: containerId,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform container action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Docker监控</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总容器数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dockerData?.total_containers || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{dockerData?.running_containers || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已停止</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{dockerData?.stopped_containers || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">镜像数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dockerData?.total_images || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Docker信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between">
            <span className="text-gray-500">Docker版本:</span>
            <span className="font-medium">{dockerData?.docker_version || '-'}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>容器列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索容器名称或镜像..."
              className="mb-4"
            />
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">名称</th>
                    <th className="px-4 py-2 text-left">镜像</th>
                    <th className="px-4 py-2 text-left">状态</th>
                    <th className="px-4 py-2 text-left">CPU%</th>
                    <th className="px-4 py-2 text-left">内存%</th>
                    <th className="px-4 py-2 text-left">网络Rx</th>
                    <th className="px-4 py-2 text-left">网络Tx</th>
                    <th className="px-4 py-2 text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredContainers.map((container, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">{container.name}</td>
                      <td className="px-4 py-2">{container.image}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          container.status === 'running' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {container.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">{container.cpu_percent?.toFixed(2)}%</td>
                      <td className="px-4 py-2">{container.memory_percent?.toFixed(2)}%</td>
                      <td className="px-4 py-2">{container.network_rx_mb?.toFixed(2)} MB</td>
                      <td className="px-4 py-2">{container.network_tx_mb?.toFixed(2)} MB</td>
                      <td className="px-4 py-2">
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            onClick={() => container.id && handleContainerAction(container.id, container.status === 'running' ? 'stop' : 'start')}
                          >
                            {container.status === 'running' ? '停止' : '启动'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => container.id && handleContainerAction(container.id, 'restart')}
                          >
                            重启
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
