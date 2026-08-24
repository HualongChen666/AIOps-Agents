'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface CloudResource {
  id?: string;
  name?: string;
  type?: string;
  region?: string;
  status?: string;
  cpu_usage?: number;
  memory_usage?: number;
  cost_monthly?: number;
  [key: string]: any;
}

interface CloudMonitoringData {
  provider?: string;
  account_id?: string;
  total_resources?: number;
  running_resources?: number;
  stopped_resources?: number;
  monthly_cost?: number;
  resources?: CloudResource[];
  regions?: string[];
  resource_types?: string[];
  [key: string]: any;
}

export default function CloudMonitoringPage() {
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [selectedType, setSelectedType] = useState('all');

  const { data: cloudData, isLoading, error, refetch } = useQuery<CloudMonitoringData>({
    queryKey: ['monitoring-cloud-monitoring', selectedRegion, selectedType],
    queryFn: async () => {
      const params: any = {};
      if (selectedRegion !== 'all') params.region = selectedRegion;
      if (selectedType !== 'all') params.type = selectedType;
      const resp = await api.get('/api/v1/monitoring/cloud-monitoring', { params });
      return resp.data;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleResourceAction = async (resourceId: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/cloud-monitoring/resource-action', {
        resource_id: resourceId,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform resource action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">云平台监控</h1>
        <div className="flex gap-2">
          <Select value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)}>
            <option value="all">所有区域</option>
            {cloudData?.regions?.map(region => (
              <option key={region} value={region}>{region}</option>
            ))}
          </Select>
          <Select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
            <option value="all">所有类型</option>
            {cloudData?.resource_types?.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>账户信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">云服务商:</span>
              <span className="font-medium">{cloudData?.provider || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">账户ID:</span>
              <span className="font-medium">{cloudData?.account_id || '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总资源数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cloudData?.total_resources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{cloudData?.running_resources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已停止</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{cloudData?.stopped_resources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">月度成本</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${cloudData?.monthly_cost?.toFixed(2) || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>资源列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">名称</th>
                  <th className="px-4 py-2 text-left">类型</th>
                  <th className="px-4 py-2 text-left">区域</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">CPU使用率</th>
                  <th className="px-4 py-2 text-left">内存使用率</th>
                  <th className="px-4 py-2 text-left">月度成本</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {cloudData?.resources?.map((resource, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{resource.name}</td>
                    <td className="px-4 py-2">{resource.type}</td>
                    <td className="px-4 py-2">{resource.region}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        resource.status === 'running' ? 'bg-green-100 text-green-800' : 
                        resource.status === 'stopped' ? 'bg-gray-100 text-gray-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {resource.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{resource.cpu_usage?.toFixed(2)}%</td>
                    <td className="px-4 py-2">{resource.memory_usage?.toFixed(2)}%</td>
                    <td className="px-4 py-2">${resource.cost_monthly?.toFixed(2)}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          onClick={() => resource.id && handleResourceAction(resource.id, resource.status === 'running' ? 'stop' : 'start')}
                        >
                          {resource.status === 'running' ? '停止' : '启动'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => resource.id && handleResourceAction(resource.id, 'restart')}
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
        </CardContent>
      </Card>
    </div>
  );
}
