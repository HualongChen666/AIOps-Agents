'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LinuxLogEntry {
  timestamp?: string;
  facility?: string;
  severity?: string;
  message?: string;
  process?: string;
  pid?: number;
  [key: string]: any;
}

interface LinuxLogsData {
  total_logs?: number;
  kernel_logs?: number;
  system_logs?: number;
  application_logs?: number;
  logs?: LinuxLogEntry[];
  log_file?: string;
  [key: string]: any;
}

export default function LinuxLogsPage() {
  const [selectedLogFile, setSelectedLogFile] = useState('/var/log/syslog');
  const [tailLines, setTailLines] = useState(100);

  const { data: linuxLogsData, isLoading, error, refetch } = useQuery<LinuxLogsData>({
    queryKey: ['monitoring-linux-logs', selectedLogFile, tailLines],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/linux-logs', {
        params: { log_file: selectedLogFile, tail_lines: tailLines }
      });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Linux日志</h1>
        <div className="flex gap-2">
          <Select value={selectedLogFile} onChange={(e) => setSelectedLogFile(e.target.value)}>
            <option value="/var/log/syslog">系统日志 (syslog)</option>
            <option value="/var/log/auth.log">认证日志 (auth.log)</option>
            <option value="/var/log/kern.log">内核日志 (kern.log)</option>
            <option value="/var/log/dmesg">启动日志 (dmesg)</option>
            <option value="/var/log/apache2/access.log">Apache访问日志</option>
            <option value="/var/log/nginx/access.log">Nginx访问日志</option>
          </Select>
          <Select value={tailLines.toString()} onChange={(e) => setTailLines(parseInt(e.target.value))}>
            <option value="50">50行</option>
            <option value="100">100行</option>
            <option value="500">500行</option>
            <option value="1000">1000行</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总日志数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{linuxLogsData?.total_logs || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">内核日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{linuxLogsData?.kernel_logs || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">系统日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{linuxLogsData?.system_logs || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">应用日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{linuxLogsData?.application_logs || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>日志内容</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">时间</th>
                  <th className="px-4 py-2 text-left">设施</th>
                  <th className="px-4 py-2 text-left">严重性</th>
                  <th className="px-4 py-2 text-left">进程</th>
                  <th className="px-4 py-2 text-left">PID</th>
                  <th className="px-4 py-2 text-left">消息</th>
                </tr>
              </thead>
              <tbody>
                {linuxLogsData?.logs?.map((log, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">{log.facility}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        log.severity === 'error' || log.severity === 'critical' ? 'bg-red-100 text-red-800' : 
                        log.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        log.severity === 'debug' ? 'bg-gray-100 text-gray-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {log.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2">{log.process}</td>
                    <td className="px-4 py-2">{log.pid}</td>
                    <td className="px-4 py-2 max-w-md">{log.message}</td>
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
