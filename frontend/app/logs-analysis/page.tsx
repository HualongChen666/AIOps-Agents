'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
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

function normalizeLevel(level?: string): LogEntry['level'] {
  const raw = (level || '').toString().toLowerCase();
  if (raw === 'error' || raw === 'err') return 'error';
  if (raw === 'warning' || raw === 'warn' || raw === 'wrn') return 'warning';
  if (raw === 'information' || raw === 'info' || raw === 'inf') return 'info';
  if (raw === 'debug' || raw === 'dbg') return 'debug';
  return 'info';
}

function mapBackendLog(item: any, index: number): LogEntry {
  const timestamp = item.time || item['@timestamp'] || item.timestamp || new Date().toISOString();
  return {
    id: `LOG-${timestamp}-${index}`,
    timestamp,
    level: normalizeLevel(item.level),
    service: item.source || item.host || item.service || 'log',
    message: item.message || '',
  };
}

export default function LogsAnalysisPage() {
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      try {
        const [systemRes, applicationRes, searchRes] = await Promise.all([
          api.get('/api/v1/logs/system/errors', { params: { newest: 50 } }).catch(() => ({ data: { logs: [] } })),
          api.get('/api/v1/logs/application/errors', { params: { newest: 50 } }).catch(() => ({ data: { logs: [] } })),
          api.get('/api/v1/logs/search', { params: { keyword: 'error', newest: 100 } }).catch(() => ({ data: { logs: [] } })),
        ]);

        const rawLogs = [
          ...(systemRes.data?.logs || []),
          ...(applicationRes.data?.logs || []),
        ];

        const searchRaw: any[] = searchRes.data?.logs || [];
        const counts = new Map<string, number>();
        const severityMap = new Map<string, Pattern['severity']>();

        searchRaw.forEach((item: any) => {
          const message = (item.message || '').toString().trim() || 'unknown';
          const level = normalizeLevel(item.level);
          counts.set(message, (counts.get(message) || 0) + 1);
          if (level === 'error') {
            severityMap.set(message, 'high');
          } else if (!severityMap.has(message)) {
            severityMap.set(message, level === 'warning' ? 'medium' : 'low');
          }
        });

        const detectedPatterns: Pattern[] = Array.from(counts.entries())
          .slice(0, 3)
          .map(([message, count], index) => ({
            id: `PAT-${index + 1}`,
            name: message.length > 40 ? `${message.slice(0, 40)}...` : message,
            count,
            severity: severityMap.get(message) || 'medium',
          }));

        if (!cancelled) {
          setLogs(rawLogs.map((item: any, index: number) => mapBackendLog(item, index)));
          setPatterns(detectedPatterns);
        }
      } catch {
        // api interceptor already shows error toast
      }
    };

    loadData();
    return () => { cancelled = true; };
  }, []);

  const filteredLogs = logs.filter(log => {
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.service.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesLevel && matchesSearch;
  });

  const totalLogs = logs.length;
  const errorCount = logs.filter(l => l.level === 'error').length;
  const warningCount = logs.filter(l => l.level === 'warning').length;

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
              <div className="text-2xl font-bold">{totalLogs.toLocaleString()}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">错误</div>
              <div className="text-2xl font-bold text-red-600">{errorCount}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">警告</div>
              <div className="text-2xl font-bold text-yellow-600">{warningCount}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">每秒速率</div>
              <div className="text-2xl font-bold">—</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
