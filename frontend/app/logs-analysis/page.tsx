'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  service: string;
  message: string;
}

interface Pattern {
  id: string;
  name: string;
  count: number;
  severity: 'low' | 'medium' | 'high';
}

export default function LogsAnalysisPage() {
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);

  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'LOG-001',
      timestamp: new Date().toISOString(),
      level: 'info',
      service: 'web-service',
      message: 'Request received: GET /api/users',
    },
    {
      id: 'LOG-002',
      timestamp: new Date(Date.now() - 1000).toISOString(),
      level: 'warning',
      service: 'database',
      message: 'Slow query detected: SELECT * FROM users (duration: 2.5s)',
    },
    {
      id: 'LOG-003',
      timestamp: new Date(Date.now() - 2000).toISOString(),
      level: 'error',
      service: 'api-gateway',
      message: 'Connection timeout: Unable to connect to backend service',
    },
  ]);

  const [patterns, setPatterns] = useState<Pattern[]>([
    {
      id: 'PAT-001',
      name: '数据库慢查询',
      count: 45,
      severity: 'high',
    },
    {
      id: 'PAT-002',
      name: '连接超时',
      count: 23,
      severity: 'high',
    },
    {
      id: 'PAT-003',
      name: '内存警告',
      count: 12,
      severity: 'medium',
    },
  ]);

  const filteredLogs = logs.filter(log => {
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         log.service.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesSearch;
  });

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'info':
        return 'bg-blue-100 text-blue-800';
      case 'debug':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">日志分析</h1>
        <div className="flex gap-2">
          <Button
            variant={isStreaming ? 'default' : 'outline'}
            onClick={() => setIsStreaming(!isStreaming)}
          >
            {isStreaming ? '⏸ 暂停' : '▶ 开始'}
          </Button>
          <Button>导出日志</Button>
        </div>
      </div>

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)}>
              <option value="all">全部级别</option>
              <option value="error">错误</option>
              <option value="warning">警告</option>
              <option value="info">信息</option>
              <option value="debug">调试</option>
            </Select>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索日志..."
              className="flex-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* 模式识别 */}
      <Card>
        <CardHeader>
          <CardTitle>模式识别</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {patterns.map((pattern) => (
              <div key={pattern.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">{pattern.name}</h3>
                  <Badge className={getSeverityColor(pattern.severity)}>
                    {pattern.severity === 'high' ? '高' : pattern.severity === 'medium' ? '中' : '低'}
                  </Badge>
                </div>
                <p className="text-2xl font-bold">{pattern.count}</p>
                <p className="text-sm text-gray-500">过去1小时</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 实时日志流 */}
      <Card>
        <CardHeader>
          <CardTitle>实时日志流</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 overflow-y-auto bg-gray-900 rounded-lg p-4 font-mono text-sm">
            {filteredLogs.map((log) => (
              <div key={log.id} className="mb-2 text-gray-300">
                <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span className="mx-2">|</span>
                <Badge className={getLevelColor(log.level)} variant="outline">
                  {log.level.toUpperCase()}
                </Badge>
                <span className="mx-2">|</span>
                <span className="text-blue-400">{log.service}</span>
                <span className="mx-2">|</span>
                <span>{log.message}</span>
              </div>
            ))}
            {isStreaming && (
              <div className="text-gray-500 animate-pulse">
                等待新日志...
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 日志统计 */}
      <Card>
        <CardHeader>
          <CardTitle>日志统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">总日志数</div>
              <div className="text-2xl font-bold">12,345</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">错误</div>
              <div className="text-2xl font-bold text-red-600">234</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">警告</div>
              <div className="text-2xl font-bold text-yellow-600">567</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">每秒速率</div>
              <div className="text-2xl font-bold">45.2</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
