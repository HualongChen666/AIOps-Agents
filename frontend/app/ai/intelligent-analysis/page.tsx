'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface AnalysisReport {
  id: string;
  name: string;
  type: 'performance' | 'security' | 'capacity' | 'cost';
  status: 'pending' | 'running' | 'completed' | 'failed';
  insights: string[];
  recommendations: string[];
  metrics: Record<string, number>;
  created_at: string;
}

interface AnalysisConfig {
  id: string;
  name: string;
  analysis_type: string;
  data_sources: string[];
  schedule: string;
  enabled: boolean;
}

export default function IntelligentAnalysisPage() {
  const [reports, setReports] = useState<AnalysisReport[]>([]);
  const [configs, setConfigs] = useState<AnalysisConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<AnalysisReport | null>(null);
  const [newAnalysis, setNewAnalysis] = useState({
    name: '',
    type: 'performance' as const,
    data_sources: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [reportsRes, configsRes] = await Promise.all([
        api.get('/api/ai/intelligent-analysis/reports'),
        api.get('/api/ai/intelligent-analysis/configs')
      ]);
      setReports(reportsRes.data.reports || []);
      setConfigs(configsRes.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    try {
      await api.post('/api/ai/intelligent-analysis/analyze', {
        name: newAnalysis.name,
        type: newAnalysis.type,
        data_sources: newAnalysis.data_sources.split(',').map(s => s.trim())
      });
      setNewAnalysis({ name: '', type: 'performance', data_sources: '' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '运行分析失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">智能分析</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 运行新分析 */}
      <Card>
        <CardHeader>
          <CardTitle>运行智能分析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="分析名称"
              value={newAnalysis.name}
              onChange={(e) => setNewAnalysis({ ...newAnalysis, name: e.target.value })}
            />
            <select
              className="border rounded px-3 py-2"
              value={newAnalysis.type}
              onChange={(e) => setNewAnalysis({ ...newAnalysis, type: e.target.value as any })}
            >
              <option value="performance">性能分析</option>
              <option value="security">安全分析</option>
              <option value="capacity">容量分析</option>
              <option value="cost">成本分析</option>
            </select>
            <Input
              placeholder="数据源 (逗号分隔)"
              value={newAnalysis.data_sources}
              onChange={(e) => setNewAnalysis({ ...newAnalysis, data_sources: e.target.value })}
              className="md:col-span-2"
            />
          </div>
          <Button onClick={handleRunAnalysis} className="mt-4">运行分析</Button>
        </CardContent>
      </Card>

      {/* 分析报告 */}
      <Card>
        <CardHeader>
          <CardTitle>分析报告</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {reports.map((report) => (
              <div
                key={report.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedReport?.id === report.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedReport(report)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{report.name}</h3>
                    <Badge variant="outline">{report.type}</Badge>
                    <Badge variant={
                      report.status === 'completed' ? 'default' :
                      report.status === 'running' ? 'secondary' :
                      report.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {report.status}
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(report.created_at).toLocaleString()}
                  </span>
                </div>
                {report.insights.length > 0 && (
                  <div className="text-sm text-gray-600">
                    洞察: {report.insights.length} 条
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 报告详情 */}
      {selectedReport && (
        <Card>
          <CardHeader>
            <CardTitle>报告详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">洞察</h4>
                <ul className="list-disc list-inside space-y-1">
                  {selectedReport.insights.map((insight, idx) => (
                    <li key={idx} className="text-gray-700">{insight}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-semibold mb-2">推荐操作</h4>
                <ul className="list-disc list-inside space-y-1">
                  {selectedReport.recommendations.map((rec, idx) => (
                    <li key={idx} className="text-gray-700">{rec}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-semibold mb-2">指标</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(selectedReport.metrics).map(([key, value]) => (
                    <div key={key} className="border rounded p-2">
                      <div className="text-sm text-gray-600">{key}</div>
                      <div className="font-semibold">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 分析配置 */}
      <Card>
        <CardHeader>
          <CardTitle>分析配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {configs.map((config) => (
              <div key={config.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{config.name}</h3>
                    <Badge variant="outline">{config.analysis_type}</Badge>
                    <Badge variant={config.enabled ? 'default' : 'secondary'}>
                      {config.enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                </div>
                <div className="text-sm text-gray-600">
                  数据源: {config.data_sources.join(', ')}
                </div>
                <div className="text-sm text-gray-600">
                  调度: {config.schedule}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
