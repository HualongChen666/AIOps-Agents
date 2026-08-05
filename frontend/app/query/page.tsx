'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api';

interface QueryTemplate {
  id: string;
  name: string;
  description: string;
  query: string;
}

interface QueryHistory {
  id: string;
  query: string;
  executedAt: string;
  duration: number;
}

export default function QueryPage() {
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);

  const [templates, setTemplates] = useState<QueryTemplate[]>([
    {
      id: 'TPL-001',
      name: 'CPU使用率查询',
      description: '查询最近1小时的CPU使用率',
      query: 'SELECT avg(cpu_usage) FROM metrics WHERE time > now() - 1h GROUP BY service',
    },
    {
      id: 'TPL-002',
      name: '告警统计',
      description: '按严重级别统计告警数量',
      query: 'SELECT severity, count(*) FROM alerts WHERE time > now() - 24h GROUP BY severity',
    },
    {
      id: 'TPL-003',
      name: '服务响应时间',
      description: '查询各服务的平均响应时间',
      query: 'SELECT service, avg(response_time) FROM traces WHERE time > now() - 1h GROUP BY service',
    },
  ]);

  const [history, setHistory] = useState<QueryHistory[]>([
    {
      id: 'HIS-001',
      query: 'SELECT avg(cpu_usage) FROM metrics WHERE time > now() - 1h',
      executedAt: new Date().toISOString(),
      duration: 245,
    },
    {
      id: 'HIS-002',
      query: 'SELECT count(*) FROM alerts WHERE severity = "critical"',
      executedAt: new Date(Date.now() - 3600000).toISOString(),
      duration: 180,
    },
  ]);

  const executeQuery = async () => {
    setIsExecuting(true);
    try {
      const { data } = await api.post('/api/ai/analyze', {
        query,
        include_metrics: true,
        platform: 'windows',
      });
      const analysisText =
        typeof data.analysis === 'string'
          ? data.analysis
          : JSON.stringify(data.analysis, null, 2);
      setResult(`分析结果:\n${analysisText}\n\n指标上下文:\n${data.metrics_context || ''}`);
    } catch (err) {
      setResult('查询失败，请稍后重试');
    } finally {
      setIsExecuting(false);
    }
  };

  const applyTemplate = (template: QueryTemplate) => {
    setQuery(template.query);
    setSelectedTemplate(template.id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">查询编辑器</h1>
        <div className="flex gap-2">
          <Select
            value={selectedTemplate}
            onChange={(e) => {
              setSelectedTemplate(e.target.value);
              const template = templates.find(t => t.id === e.target.value);
              if (template) setQuery(template.query);
            }}
          >
            <option value="">选择模板</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </Select>
          <Button onClick={executeQuery} disabled={isExecuting}>
            {isExecuting ? '执行中...' : '执行查询'}
          </Button>
        </div>
      </div>

      {/* 查询编辑器 */}
      <Card>
        <CardHeader>
          <CardTitle>查询编辑器</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入查询语句..."
            rows={8}
            className="font-mono text-sm"
          />
          <div className="mt-4 flex justify-between items-center">
            <div className="text-sm text-gray-500">
              支持语法: SQL, PromQL, LogQL
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">
                格式化
              </Button>
              <Button variant="outline" size="sm">
                保存为模板
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 查询结果 */}
      <Card>
        <CardHeader>
          <CardTitle>查询结果</CardTitle>
        </CardHeader>
        <CardContent>
          {result ? (
            <div className="p-4 bg-gray-50 rounded-lg font-mono text-sm">
              {result}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              执行查询后显示结果
            </div>
          )}
        </CardContent>
      </Card>

      {/* 查询模板 */}
      <Card>
        <CardHeader>
          <CardTitle>查询模板</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {templates.map((template) => (
              <div
                key={template.id}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                onClick={() => applyTemplate(template)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{template.name}</h3>
                    <p className="text-sm text-gray-500">{template.description}</p>
                  </div>
                  <Button variant="outline" size="sm">
                    应用
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 查询历史 */}
      <Card>
        <CardHeader>
          <CardTitle>查询历史</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {history.map((item) => (
              <div
                key={item.id}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                onClick={() => setQuery(item.query)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 font-mono text-sm truncate">
                    {item.query}
                  </div>
                  <div className="ml-4 text-sm text-gray-500">
                    {new Date(item.executedAt).toLocaleString()} · {item.duration}ms
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
