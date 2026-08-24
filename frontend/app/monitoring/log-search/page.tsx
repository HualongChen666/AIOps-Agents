'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LogEntry {
  id?: string;
  timestamp?: string;
  level?: string;
  service?: string;
  message?: string;
  source?: string;
  [key: string]: any;
}

interface LogSearchData {
  total_results?: number;
  search_time_ms?: number;
  logs?: LogEntry[];
  query?: string;
  [key: string]: any;
}

export default function LogSearchPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [selectedService, setSelectedService] = useState('all');
  const [isSearching, setIsSearching] = useState(false);

  const { data: searchResults, refetch } = useQuery<LogSearchData>({
    queryKey: ['monitoring-log-search', searchQuery, timeRange, selectedLevel, selectedService],
    queryFn: async () => {
      if (!searchQuery.trim()) return { total_results: 0, logs: [] };
      const params: any = { 
        query: searchQuery,
        time_range: timeRange 
      };
      if (selectedLevel !== 'all') params.level = selectedLevel;
      if (selectedService !== 'all') params.service = selectedService;
      const resp = await api.get('/api/v1/monitoring/log-search', { params });
      return resp.data;
    },
    enabled: searchQuery.length > 0,
    refetchInterval: false,
  });

  const handleSearch = async () => {
    setIsSearching(true);
    await refetch();
    setIsSearching(false);
  };

  const handleExport = async () => {
    try {
      const params: any = { 
        query: searchQuery,
        time_range: timeRange,
        export: true
      };
      if (selectedLevel !== 'all') params.level = selectedLevel;
      if (selectedService !== 'all') params.service = selectedService;
      const resp = await api.get('/api/v1/monitoring/log-search/export', { 
        params,
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'logs-export.json');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Failed to export logs:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">日志搜索</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>搜索条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="输入搜索关键词..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} disabled={isSearching}>
                {isSearching ? '搜索中...' : '搜索'}
              </Button>
            </div>
            <div className="flex gap-2">
              <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
                <option value="5m">5分钟</option>
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
                <option value="30d">30天</option>
              </Select>
              <Select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)}>
                <option value="all">所有级别</option>
                <option value="debug">DEBUG</option>
                <option value="info">INFO</option>
                <option value="warning">WARNING</option>
                <option value="error">ERROR</option>
                <option value="critical">CRITICAL</option>
              </Select>
              <Select value={selectedService} onChange={(e) => setSelectedService(e.target.value)}>
                <option value="all">所有服务</option>
                <option value="api">API服务</option>
                <option value="worker">Worker服务</option>
                <option value="database">数据库</option>
                <option value="cache">缓存</option>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {searchResults && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">搜索结果</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{searchResults.total_results || 0}</div>
                <div className="text-sm text-gray-500">条日志</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">搜索耗时</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{searchResults.search_time_ms?.toFixed(2) || '-'} ms</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>日志结果</CardTitle>
                <Button size="sm" variant="outline" onClick={handleExport}>
                  导出结果
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left">时间</th>
                      <th className="px-4 py-2 text-left">级别</th>
                      <th className="px-4 py-2 text-left">服务</th>
                      <th className="px-4 py-2 text-left">来源</th>
                      <th className="px-4 py-2 text-left">消息</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResults.logs?.map((log, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-4 py-2">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            log.level === 'error' || log.level === 'critical' ? 'bg-red-100 text-red-800' : 
                            log.level === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                            log.level === 'debug' ? 'bg-gray-100 text-gray-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {log.level}
                          </span>
                        </td>
                        <td className="px-4 py-2">{log.service}</td>
                        <td className="px-4 py-2">{log.source}</td>
                        <td className="px-4 py-2 max-w-md">{log.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
