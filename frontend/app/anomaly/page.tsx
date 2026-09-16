'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface AnomalyData {
  metric: string;
  timestamp: string;
  value: number;
  predicted: number;
  lowerBound: number;
  upperBound: number;
  isAnomaly: boolean;
}

interface AnomalyRecord {
  id: string;
  timestamp: string;
  metric: string;
  actualValue: number;
  predictedValue: number;
  deviation: number;
  confidence: number;
}

interface ModelConfig {
  sampling: string;
  window: string;
  sensitivity: string;
  autoAlert: string;
}

const MODEL_CONFIG_KEY = 'anomaly-model-config';
const DEFAULT_MODEL_CONFIG: ModelConfig = {
  sampling: '1m',
  window: '24h',
  sensitivity: 'medium',
  autoAlert: 'enabled',
};

export default function AnomalyPage() {
  const [selectedModel, setSelectedModel] = useState('prophet');
  const [confidence, setConfidence] = useState(95);
  const [appliedModel, setAppliedModel] = useState('prophet');
  const [appliedConfidence, setAppliedConfidence] = useState(95);
  const [anomalyData, setAnomalyData] = useState<AnomalyData[]>([]);
  const [anomalyRecords, setAnomalyRecords] = useState<AnomalyRecord[]>([]);
  const [modelConfig, setModelConfig] = useState<ModelConfig>(DEFAULT_MODEL_CONFIG);
  const [configSaved, setConfigSaved] = useState(false);

  const loadAnomalyData = async () => {
    // Use the shared client so the HttpOnly session cookie is sent with the
    // request; no token is read or attached in JavaScript.
    try {
      const [recordsRes, statsRes] = await Promise.all([
        api.get<AnomalyRecord[]>('/api/v1/anomaly/records'),
        api.get<Record<string, number>>('/api/v1/anomaly/statistics'),
      ]);

      setAnomalyRecords(recordsRes.data);

      const stats = statsRes.data;
      const chartData: AnomalyData[] = Object.entries(stats)
        .filter(([key]) => key !== 'total')
        .map(([metric, count]) => ({
          metric,
          timestamp: new Date().toISOString(),
          value: Number(count),
          predicted: 0,
          lowerBound: 0,
          upperBound: 0,
          isAnomaly: Number(count) > 0,
        }));
      setAnomalyData(chartData);
    } catch (err) {
      console.error('Failed to load anomaly data:', err);
    }
  };

  useEffect(() => {
    loadAnomalyData();
  }, []);

  // Restore the persisted model configuration for this browser.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(MODEL_CONFIG_KEY);
      if (raw) setModelConfig({ ...DEFAULT_MODEL_CONFIG, ...JSON.parse(raw) });
    } catch {
      /* ignore malformed persisted config */
    }
  }, []);

  // "应用配置": switch the *applied* detection model / confidence threshold.
  // The threshold filters the record list below, so it has a real, visible
  // effect instead of being decorative.
  const handleApplyConfig = () => {
    setAppliedModel(selectedModel);
    setAppliedConfidence(confidence);
  };

  // "保存配置": persist the model configuration (real client-side persistence).
  const handleSaveConfig = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(MODEL_CONFIG_KEY, JSON.stringify(modelConfig));
    }
    setConfigSaved(true);
  };

  const visibleRecords = anomalyRecords.filter((r) => (r.confidence ?? 0) >= appliedConfidence);
  const maxAnomalyValue = Math.max(1, ...anomalyData.map((d) => d.value));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">异常检测</h1>
        <Button onClick={loadAnomalyData}>刷新数据</Button>
      </div>

      {/* 模型选择 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">检测模型</label>
              <Select
                aria-label="检测模型"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                <option value="prophet">Prophet</option>
                <option value="isolation-forest">Isolation Forest</option>
                <option value="ensemble">Ensemble</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">置信度阈值 (%)</label>
              <Select
                aria-label="置信度阈值 (%)"
                value={confidence.toString()}
                onChange={(e) => setConfidence(Number(e.target.value))}
              >
                <option value="90">90%</option>
                <option value="95">95%</option>
                <option value="99">99%</option>
              </Select>
            </div>
            <div className="flex items-end">
              <Button className="w-full" onClick={handleApplyConfig}>应用配置</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 时序图表 */}
      <Card>
        <CardHeader>
          <CardTitle>时序异常检测</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            data-testid="anomaly-chart"
            className="h-64 bg-gray-50 rounded-lg flex items-end gap-4 p-6 relative"
          >
            {anomalyData.length === 0 ? (
              <p className="text-gray-500 m-auto">暂无异常数据</p>
            ) : (
              anomalyData.map((point, index) => (
                <div key={`${point.metric}-${index}`} className="flex-1 flex flex-col items-center justify-end h-full">
                  <span className="text-xs font-medium mb-1">{point.value}</span>
                  <div
                    data-testid={`anomaly-bar-${point.metric}`}
                    className={`w-full rounded-t ${point.isAnomaly ? 'bg-red-500' : 'bg-blue-500'}`}
                    style={{ height: `${Math.round((point.value / maxAnomalyValue) * 80)}%` }}
                  />
                  <span className="text-xs text-gray-500 mt-1">{point.metric}</span>
                </div>
              ))
            )}
            <div className="absolute bottom-1 right-4 space-x-2">
              <Badge className="bg-blue-100 text-blue-800">异常数</Badge>
              <Badge className="bg-red-100 text-red-800">命中阈值</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 异常记录列表 */}
      <Card>
        <CardHeader>
          <CardTitle>异常记录</CardTitle>
          <span data-testid="applied-config" className="text-sm text-gray-500">
            已应用模型: {appliedModel} · 置信度阈值: {appliedConfidence}%
          </span>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>指标</TableHead>
                <TableHead>实际值</TableHead>
                <TableHead>预测值</TableHead>
                <TableHead>偏差</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleRecords.map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-mono text-sm">{record.id}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(record.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>{record.metric}</TableCell>
                  <TableCell className="font-medium">{record.actualValue}</TableCell>
                  <TableCell>{record.predictedValue}</TableCell>
                  <TableCell>
                    <Badge className={record.deviation > 20 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}>
                      {record.deviation > 0 ? '+' : ''}{(record.deviation ?? 0).toFixed(1)}%
                    </Badge>
                  </TableCell>
                  <TableCell>{record.confidence}%</TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 模型配置面板 */}
      <Card>
        <CardHeader>
          <CardTitle>模型配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">采样率</label>
              <Select
                aria-label="采样率"
                value={modelConfig.sampling}
                onChange={(e) => { setModelConfig({ ...modelConfig, sampling: e.target.value }); setConfigSaved(false); }}
              >
                <option value="1s">1秒</option>
                <option value="5s">5秒</option>
                <option value="1m">1分钟</option>
                <option value="5m">5分钟</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">历史数据窗口</label>
              <Select
                aria-label="历史数据窗口"
                value={modelConfig.window}
                onChange={(e) => { setModelConfig({ ...modelConfig, window: e.target.value }); setConfigSaved(false); }}
              >
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
                <option value="30d">30天</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">异常检测灵敏度</label>
              <Select
                aria-label="异常检测灵敏度"
                value={modelConfig.sensitivity}
                onChange={(e) => { setModelConfig({ ...modelConfig, sensitivity: e.target.value }); setConfigSaved(false); }}
              >
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">自动告警</label>
              <Select
                aria-label="自动告警"
                value={modelConfig.autoAlert}
                onChange={(e) => { setModelConfig({ ...modelConfig, autoAlert: e.target.value }); setConfigSaved(false); }}
              >
                <option value="enabled">启用</option>
                <option value="disabled">禁用</option>
              </Select>
            </div>
          </div>
          <div className="mt-6 flex justify-end items-center gap-3">
            {configSaved && <span data-testid="config-saved" className="text-sm text-green-600">配置已保存</span>}
            <Button onClick={handleSaveConfig}>保存配置</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
