'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ProcessInfo {
  pid?: number;
  name?: string;
  cpu_percent?: number;
  memory_percent?: number;
  status?: string;
  user?: string;
  command?: string;
  [key: string]: any;
}

interface ProcessMonitoringData {
  processes?: ProcessInfo[];
  total_count?: number;
  [key: string]: any;
}

export default function ProcessMonitoringPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('cpu_percent');

  const { data: processData, isLoading, error, refetch } = useQuery<ProcessMonitoringData>({
    queryKey: ['monitoring-process-monitoring'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/process-monitoring');
      return resp.data;
    },
    refetchInterval: 10000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const filteredProcesses = processData?.processes
    ?.filter(p => 
      p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.command?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => ((b[sortBy as keyof ProcessInfo] as number) || 0) - ((a[sortBy as keyof ProcessInfo] as number) || 0)) || [];

  const handleKillProcess = async (pid: number) => {
    try {
      await api.post('/api/v1/monitoring/process-monitoring/kill', { pid });
      refetch();
    } catch (err) {
      console.error('Failed to kill process:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">进程监控</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总进程数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{processData?.total_count || '-'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {processData?.processes?.filter(p => p.status === 'running').length || '-'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高CPU进程</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {processData?.processes?.filter(p => (p.cpu_percent || 0) > 50).length || '-'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>进程列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索进程名称或命令..."
                className="flex-1"
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-2 border rounded"
              >
                <option value="cpu_percent">按CPU排序</option>
                <option value="memory_percent">按内存排序</option>
                <option value="pid">按PID排序</option>
              </select>
            </div>
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">PID</th>
                    <th className="px-4 py-2 text-left">名称</th>
                    <th className="px-4 py-2 text-left">CPU%</th>
                    <th className="px-4 py-2 text-left">内存%</th>
                    <th className="px-4 py-2 text-left">状态</th>
                    <th className="px-4 py-2 text-left">用户</th>
                    <th className="px-4 py-2 text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProcesses.map((process, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">{process.pid}</td>
                      <td className="px-4 py-2">{process.name}</td>
                      <td className="px-4 py-2">{process.cpu_percent?.toFixed(2)}%</td>
                      <td className="px-4 py-2">{process.memory_percent?.toFixed(2)}%</td>
                      <td className="px-4 py-2">{process.status}</td>
                      <td className="px-4 py-2">{process.user}</td>
                      <td className="px-4 py-2">
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => process.pid && handleKillProcess(process.pid)}
                        >
                          终止
                        </Button>
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
