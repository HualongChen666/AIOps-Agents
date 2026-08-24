'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ConversionRule {
  id?: string;
  name?: string;
  source_format?: string;
  target_format?: string;
  status?: string;
  conversions_count?: number;
  last_conversion?: string;
  [key: string]: any;
}

interface MetricsConverterData {
  total_rules?: number;
  active_rules?: number;
  total_conversions?: number;
  supported_formats?: string[];
  rules?: ConversionRule[];
  [key: string]: any;
}

export default function MetricsConverterPage() {
  const [sourceFormat, setSourceFormat] = useState('');
  const [targetFormat, setTargetFormat] = useState('');
  const [metricsData, setMetricsData] = useState('');
  const [isConverting, setIsConverting] = useState(false);
  const [conversionResult, setConversionResult] = useState('');

  const { data: converterData, isLoading, error, refetch } = useQuery<MetricsConverterData>({
    queryKey: ['monitoring-metrics-converter'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/metrics-converter');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const handleConvert = async () => {
    setIsConverting(true);
    try {
      const resp = await api.post('/api/v1/monitoring/metrics-converter/convert', {
        source_format: sourceFormat,
        target_format: targetFormat,
        metrics_data: metricsData
      });
      setConversionResult(JSON.stringify(resp.data, null, 2));
    } catch (err) {
      console.error('Conversion failed:', err);
      setConversionResult('转换失败');
    } finally {
      setIsConverting(false);
    }
  };

  const handleRuleAction = async (ruleId: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/metrics-converter/rule-action', {
        rule_id: ruleId,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform rule action:', err);
    }
  };

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">指标转换器</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总规则数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{converterData?.total_rules || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃规则</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{converterData?.active_rules || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总转换次数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{converterData?.total_conversions?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">支持格式</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{converterData?.supported_formats?.length || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>指标转换</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">源格式</label>
                <Select value={sourceFormat} onChange={(e) => setSourceFormat(e.target.value)}>
                  <option value="">选择格式</option>
                  {converterData?.supported_formats?.map(format => (
                    <option key={format} value={format}>{format}</option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">目标格式</label>
                <Select value={targetFormat} onChange={(e) => setTargetFormat(e.target.value)}>
                  <option value="">选择格式</option>
                  {converterData?.supported_formats?.map(format => (
                    <option key={format} value={format}>{format}</option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">指标数据 (JSON)</label>
              <textarea
                value={metricsData}
                onChange={(e) => setMetricsData(e.target.value)}
                placeholder='{"metric_name": "cpu_usage", "value": 75.5}'
                className="w-full h-32 p-3 border rounded font-mono text-sm"
              />
            </div>
            <Button onClick={handleConvert} disabled={isConverting}>
              {isConverting ? '转换中...' : '转换'}
            </Button>
            {conversionResult && (
              <div>
                <label className="block text-sm font-medium mb-2">转换结果</label>
                <pre className="w-full h-32 p-3 bg-gray-50 rounded overflow-auto text-sm">
                  {conversionResult}
                </pre>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>转换规则列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">名称</th>
                  <th className="px-4 py-2 text-left">源格式</th>
                  <th className="px-4 py-2 text-left">目标格式</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">转换次数</th>
                  <th className="px-4 py-2 text-left">最后转换</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {converterData?.rules?.map((rule, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{rule.name}</td>
                    <td className="px-4 py-2">{rule.source_format}</td>
                    <td className="px-4 py-2">{rule.target_format}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        rule.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {rule.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{rule.conversions_count}</td>
                    <td className="px-4 py-2">
                      {rule.last_conversion ? new Date(rule.last_conversion).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => rule.id && handleRuleAction(rule.id, rule.status === 'active' ? 'disable' : 'enable')}
                      >
                        {rule.status === 'active' ? '禁用' : '启用'}
                      </Button>
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
