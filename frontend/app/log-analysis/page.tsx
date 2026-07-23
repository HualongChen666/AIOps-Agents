'use client'

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  service: string;
  message: string;
  parsedFields?: Record<string, string>;
}

interface LogPattern {
  id: string;
  pattern: string;
  count: number;
  severity: 'high' | 'medium' | 'low';
  description: string;
}

export default function LogAnalysisPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [isStreaming, setIsStreaming] = useState(false);
  const [patterns, setPatterns] = useState<LogPattern[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  // 管理实时日志流的定时器
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    let timeout: NodeJS.Timeout | null = null;

    if (isStreaming) {
      interval = setInterval(() => {
        const newLog: LogEntry = {
          id: `LOG-${Date.now()}`,
          timestamp: new Date(),
          level: ['INFO', 'WARN', 'ERROR', 'DEBUG'][Math.floor(Math.random() * 4)] as any,
          service: ['web-service', 'api-gateway', 'database', 'cache'][Math.floor(Math.random() * 4)],
          message: generateRandomLogMessage(),
        };
        setLogs((prev) => [...prev.slice(-99), newLog]);
      }, 1000);

      // 10秒后自动停止
      timeout = setTimeout(() => {
        if (interval) clearInterval(interval);
        setIsStreaming(false);
      }, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
      if (timeout) clearTimeout(timeout);
    };
  }, [isStreaming]);

  const handleStartStream = () => {
    setIsStreaming(true);
  };

  const handleStopStream = () => {
    setIsStreaming(false);
  };

  const handleAnalyzePatterns = () => {
    const detectedPatterns: LogPattern[] = [
      {
        id: 'PAT-001',
        pattern: 'Connection timeout',
        count: 15,
        severity: 'high',
        description: '检测到频繁的连接超时错误',
      },
      {
        id: 'PAT-002',
        pattern: 'Slow query',
        count: 8,
        severity: 'medium',
        description: '检测到慢查询模式',
      },
      {
        id: 'PAT-003',
        pattern: 'Memory warning',
        count: 5,
        severity: 'medium',
        description: '检测到内存警告模式',
      },
    ];
    setPatterns(detectedPatterns);
  };

  const generateRandomLogMessage = () => {
    const messages = [
      'Request processed successfully',
      'Connection established',
      'Query executed in 25ms',
      'Cache hit for key: user_123',
      'Connection timeout after 30s',
      'Slow query detected: SELECT * FROM users WHERE id = ?',
      'Memory usage at 85%',
      'Disk space warning: 90% full',
      'API rate limit exceeded',
      'Authentication failed for user test@example.com',
    ];
    return messages[Math.floor(Math.random() * messages.length)];
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'bg-red-100 text-red-800';
      case 'WARN':
        return 'bg-yellow-100 text-yellow-800';
      case 'INFO':
        return 'bg-blue-100 text-blue-800';
      case 'DEBUG':
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

  const filteredLogs = logs.filter((log) => {
    const matchesFilter = !filter || log.message.toLowerCase().includes(filter.toLowerCase()) || log.service.toLowerCase().includes(filter.toLowerCase());
    const matchesLevel = selectedLevel === 'ALL' || log.level === selectedLevel;
    return matchesFilter && matchesLevel;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">日志分析</h1>
        <div className="flex gap-2">
          {isStreaming ? (
            <Button variant="destructive" onClick={handleStopStream}>
              停止流
            </Button>
          ) : (
            <Button onClick={handleStartStream}>
              开始实时流
            </Button>
          )}
          <Button variant="outline" onClick={handleAnalyzePatterns}>
            识别模式
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 实时日志流 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>实时日志流</CardTitle>
              <div className="flex gap-2">
                <select
                  value={selectedLevel}
                  onChange={(e) => setSelectedLevel(e.target.value)}
                  className="px-3 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="ALL">全部级别</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARN">WARN</option>
                  <option value="INFO">INFO</option>
                  <option value="DEBUG">DEBUG</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <Input
                placeholder="搜索日志..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </div>
            <div className="h-96 overflow-y-auto bg-gray-900 rounded-lg p-4 font-mono text-sm">
              {filteredLogs.length === 0 ? (
                <div className="text-gray-400 text-center py-8">
                  点击"开始实时流"查看日志
                </div>
              ) : (
                <div className="space-y-1">
                  {filteredLogs.map((log) => (
                    <div key={log.id} className="text-gray-300 hover:bg-gray-800 p-1 rounded">
                      <span className="text-gray-500">[{log.timestamp.toLocaleTimeString()}]</span>
                      <span className={`ml-2 ${log.level === 'ERROR' ? 'text-red-400' : log.level === 'WARN' ? 'text-yellow-400' : log.level === 'INFO' ? 'text-blue-400' : 'text-gray-400'}`}>
                        {log.level}
                      </span>
                      <span className="ml-2 text-green-400">{log.service}</span>
                      <span className="ml-2">{log.message}</span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
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
            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">级别分布</h4>
                <div className="space-y-2">
                  {['ERROR', 'WARN', 'INFO', 'DEBUG'].map((level) => {
                    const count = logs.filter((l) => l.level === level).length;
                    const percentage = logs.length > 0 ? (count / logs.length) * 100 : 0;
                    return (
                      <div key={level}>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span>{level}</span>
                          <span>{count} ({percentage.toFixed(1)}%)</span>
                        </div>
                        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${level === 'ERROR' ? 'bg-red-500' : level === 'WARN' ? 'bg-yellow-500' : level === 'INFO' ? 'bg-blue-500' : 'bg-gray-500'}`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">服务分布</h4>
                <div className="space-y-2">
                  {['web-service', 'api-gateway', 'database', 'cache'].map((service) => {
                    const count = logs.filter((l) => l.service === service).length;
                    const percentage = logs.length > 0 ? (count / logs.length) * 100 : 0;
                    return (
                      <div key={service}>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span>{service}</span>
                          <span>{count} ({percentage.toFixed(1)}%)</span>
                        </div>
                        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500" style={{ width: `${percentage}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">总览</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">总日志数</span>
                    <span className="font-medium">{logs.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">错误数</span>
                    <span className="font-medium text-red-600">{logs.filter((l) => l.level === 'ERROR').length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">警告数</span>
                    <span className="font-medium text-yellow-600">{logs.filter((l) => l.level === 'WARN').length}</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 智能日志解析 */}
      <Card>
        <CardHeader>
          <CardTitle>智能日志解析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">自动字段提取</h4>
              <p className="text-sm text-gray-600 mb-3">
                自动从日志中提取时间戳、服务名、级别等结构化字段
              </p>
              <div className="bg-gray-50 rounded p-3 font-mono text-xs">
                <pre>{`{
  "timestamp": "2024-01-15T10:00:00Z",
  "level": "ERROR",
  "service": "web-service",
  "message": "Connection timeout",
  "trace_id": "abc-123-def",
  "user_id": "user_456"
}`}</pre>
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">异常检测</h4>
              <p className="text-sm text-gray-600 mb-3">
                使用ML模型检测日志中的异常模式和异常值
              </p>
              <div className="bg-gray-50 rounded p-3 font-mono text-xs">
                <pre>{`检测到异常:
- 错误率突增: 300%
- 响应时间异常: 5s (正常 < 500ms)
- 异常服务: api-gateway`}</pre>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 日志模式识别 */}
      <Card>
        <CardHeader>
          <CardTitle>日志模式识别</CardTitle>
        </CardHeader>
        <CardContent>
          {patterns.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              点击"识别模式"按钮分析日志模式
            </div>
          ) : (
            <div className="space-y-4">
              {patterns.map((pattern) => (
                <div key={pattern.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium">{pattern.pattern}</h4>
                        <Badge className={getSeverityColor(pattern.severity)}>
                          {pattern.severity === 'high' ? '高' : pattern.severity === 'medium' ? '中' : '低'}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600">{pattern.description}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold">{pattern.count}</p>
                      <p className="text-xs text-gray-500">出现次数</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button variant="outline" size="sm">
                      创建告警
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
