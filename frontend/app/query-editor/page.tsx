'use client'

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface QueryTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  query: string;
  parameters: string[];
}

interface QueryHistory {
  id: string;
  query: string;
  timestamp: Date;
  duration: number;
  resultCount: number;
}

export default function QueryEditorPage() {
  const [query, setQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<QueryTemplate | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const templates: QueryTemplate[] = [
    {
      id: 'TPL-001',
      name: 'CPU使用率查询',
      description: '查询指定时间范围内的CPU使用率',
      category: '性能',
      query: `SELECT 
  timestamp,
  service_name,
  cpu_usage_percent
FROM metrics
WHERE metric_name = 'cpu_usage'
  AND timestamp >= NOW() - INTERVAL '1 hour'
  AND service_name = '{{service_name}}'
ORDER BY timestamp DESC
LIMIT 100;`,
      parameters: ['service_name'],
    },
    {
      id: 'TPL-002',
      name: '告警统计查询',
      description: '统计过去24小时的告警数量',
      category: '告警',
      query: `SELECT 
  severity,
  COUNT(*) as alert_count,
  AVG(resolution_time) as avg_resolution_time
FROM alerts
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY severity
ORDER BY alert_count DESC;`,
      parameters: [],
    },
    {
      id: 'TPL-003',
      name: '慢查询分析',
      description: '分析执行时间超过阈值的SQL查询',
      category: '数据库',
      query: `SELECT 
  query_hash,
  query_text,
  COUNT(*) as execution_count,
  AVG(execution_time) as avg_time,
  MAX(execution_time) as max_time
FROM slow_queries
WHERE execution_time > {{threshold}}
  AND timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY query_hash, query_text
ORDER BY avg_time DESC
LIMIT 20;`,
      parameters: ['threshold'],
    },
    {
      id: 'TPL-004',
      name: '错误日志查询',
      description: '查询指定服务的错误日志',
      category: '日志',
      query: `SELECT 
  timestamp,
  level,
  message,
  service_name
FROM logs
WHERE level = 'ERROR'
  AND service_name = '{{service_name}}'
  AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 100;`,
      parameters: ['service_name'],
    },
    {
      id: 'TPL-005',
      name: '流量统计',
      description: '统计服务的请求流量',
      category: '流量',
      query: `SELECT 
  time_bucket('5 minutes', timestamp) as bucket,
  service_name,
  COUNT(*) as request_count,
  AVG(response_time) as avg_response_time,
  SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
FROM http_requests
WHERE timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY bucket, service_name
ORDER BY bucket DESC;`,
      parameters: [],
    },
  ];

  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>([
    {
      id: 'HIST-001',
      query: 'SELECT * FROM metrics WHERE metric_name = "cpu_usage" LIMIT 10',
      timestamp: new Date(Date.now() - 3600000),
      duration: 125,
      resultCount: 10,
    },
    {
      id: 'HIST-002',
      query: 'SELECT COUNT(*) FROM alerts WHERE severity = "critical"',
      timestamp: new Date(Date.now() - 7200000),
      duration: 89,
      resultCount: 1,
    },
  ]);

  const suggestions = [
    { label: 'SELECT', type: 'keyword' },
    { label: 'FROM', type: 'keyword' },
    { label: 'WHERE', type: 'keyword' },
    { label: 'JOIN', type: 'keyword' },
    { label: 'GROUP BY', type: 'keyword' },
    { label: 'ORDER BY', type: 'keyword' },
    { label: 'LIMIT', type: 'keyword' },
    { label: 'metrics', type: 'table' },
    { label: 'alerts', type: 'table' },
    { label: 'logs', type: 'table' },
    { label: 'services', type: 'table' },
    { label: 'timestamp', type: 'column' },
    { label: 'service_name', type: 'column' },
    { label: 'cpu_usage_percent', type: 'column' },
  ];

  const handleTemplateSelect = (template: QueryTemplate) => {
    setSelectedTemplate(template);
    setQuery(template.query);
    textareaRef.current?.focus();
  };

  const handleExecute = async () => {
    if (!query.trim()) return;
    setIsExecuting(true);
    setShowResults(false);
    setLastResult(null);
    const start = Date.now();

    try {
      const response = await api.post('/api/ai/analyze', {
        query,
        include_metrics: true,
        platform: 'windows',
      });
      const duration = Date.now() - start;
      setShowResults(true);
      setLastResult(response.data);

      const newHistory: QueryHistory = {
        id: `HIST-${Date.now()}`,
        query,
        timestamp: new Date(),
        duration,
        resultCount: response.data?.analysis?.suggested_actions?.length ?? 1,
      };
      setQueryHistory((prev) => [newHistory, ...prev].slice(0, 10));
    } catch {
      const duration = Date.now() - start;
      const newHistory: QueryHistory = {
        id: `HIST-${Date.now()}`,
        query,
        timestamp: new Date(),
        duration,
        resultCount: 0,
      };
      setQueryHistory((prev) => [newHistory, ...prev].slice(0, 10));
    } finally {
      setIsExecuting(false);
    }
  };

  const handleFormat = () => {
    // 简单的SQL格式化
    let formatted = query
      .replace(/\s+/g, ' ')
      .replace(/\bSELECT\b/gi, '\nSELECT')
      .replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE')
      .replace(/\bAND\b/gi, '\n  AND')
      .replace(/\bOR\b/gi, '\n  OR')
      .replace(/\bJOIN\b/gi, '\nJOIN')
      .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
      .replace(/\bORDER BY\b/gi, '\nORDER BY')
      .replace(/\bLIMIT\b/gi, '\nLIMIT')
      .trim();
    setQuery(formatted);
  };

  const handleClear = () => {
    setQuery('');
    setSelectedTemplate(null);
    setShowResults(false);
  };

  const handleHistorySelect = (history: QueryHistory) => {
    setQuery(history.query);
    setSelectedTemplate(null);
  };

  const getKeywordColor = (word: string) => {
    const keywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'JOIN', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING', 'UNION', 'INSERT', 'UPDATE', 'DELETE'];
    return keywords.includes(word.toUpperCase()) ? 'text-purple-600 font-bold' : '';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">查询编辑器</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleFormat}>
            格式化
          </Button>
          <Button variant="outline" onClick={handleClear}>
            清空
          </Button>
          <Button onClick={handleExecute} disabled={!query.trim() || isExecuting}>
            {isExecuting ? '执行中...' : '执行查询'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 查询模板 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>查询模板</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${selectedTemplate?.id === template.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  onClick={() => handleTemplateSelect(template)}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-sm">{template.name}</h4>
                    <Badge variant="outline" className="text-xs">
                      {template.category}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500">{template.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 查询编辑器 */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>SQL编辑器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="输入SQL查询语句或选择模板..."
                  className="w-full h-64 p-4 font-mono text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  spellCheck={false}
                />
                {query && (
                  <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                    {query.length} 字符
                  </div>
                )}
              </div>

              {/* 自动补全建议 */}
              {query && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-sm text-gray-500">自动补全:</span>
                  {suggestions.slice(0, 8).map((suggestion, index) => (
                    <Badge
                      key={index}
                      variant="outline"
                      className="cursor-pointer hover:bg-blue-50"
                      onClick={() => setQuery(query + ' ' + suggestion.label)}
                    >
                      {suggestion.label}
                    </Badge>
                  ))}
                </div>
              )}

              {/* 查询结果 */}
              {showResults && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                    <h4 className="font-medium text-sm">查询结果</h4>
                  </div>
                  <div className="p-4">
                    <div className="text-sm text-gray-600 mb-2">
                      查询执行成功，返回 {queryHistory[0]?.resultCount || 0} 条记录
                    </div>
                    <div className="bg-gray-50 rounded p-4 font-mono text-xs">
                      <pre>
                        {lastResult
                          ? JSON.stringify(
                            {
                              metrics_context: lastResult.metrics_context,
                              analysis: lastResult.analysis,
                            },
                            null,
                            2
                          )
                          : ''}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 查询历史 */}
      <Card>
        <CardHeader>
          <CardTitle>查询历史</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {queryHistory.map((history) => (
              <div
                key={history.id}
                className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                onClick={() => handleHistorySelect(history)}
              >
                <div className="flex items-center justify-between mb-1">
                  <code className="text-sm font-mono text-gray-700 truncate flex-1">
                    {history.query}
                  </code>
                  <div className="flex items-center gap-4 text-xs text-gray-500 ml-4">
                    <span>{history.duration}ms</span>
                    <span>{history.resultCount} 条</span>
                    <span>{history.timestamp.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 语法说明 */}
      <Card>
        <CardHeader>
          <CardTitle>语法说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">关键词</h4>
              <div className="flex flex-wrap gap-1">
                {['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'LIMIT'].map((keyword) => (
                  <Badge key={keyword} variant="outline" className="text-purple-600">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">常用表</h4>
              <div className="flex flex-wrap gap-1">
                {['metrics', 'alerts', 'logs', 'services', 'http_requests'].map((table) => (
                  <Badge key={table} variant="outline" className="text-blue-600">
                    {table}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">常用函数</h4>
              <div className="flex flex-wrap gap-1">
                {['COUNT()', 'SUM()', 'AVG()', 'MAX()', 'MIN()', 'NOW()', 'time_bucket()'].map((func) => (
                  <Badge key={func} variant="outline" className="text-green-600">
                    {func}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
