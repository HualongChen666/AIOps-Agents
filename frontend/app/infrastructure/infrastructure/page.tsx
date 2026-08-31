'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface KafkaStatus {
  connected: boolean;
  total_messages: number;
  topics: string[];
}

interface FlinkJob {
  job_name: string;
  job_type: string;
  status: string;
}

interface ConfigItem {
  key: string;
  value: any;
  version: number;
}

interface HealthCheck {
  kafka: boolean;
  flink: boolean;
  storage: boolean;
  config_center: boolean;
  monitoring: boolean;
  data_flow: boolean;
}

interface DataFlowStats {
  total_processed: number;
  total_analyzed: number;
  total_errors: number;
  avg_processing_time_ms: number;
  error_rate: number;
  analysis_rate: number;
}

export default function InfrastructurePage() {
  const [kafkaStatus, setKafkaStatus] = useState<KafkaStatus | null>(null);
  const [flinkJobs, setFlinkJobs] = useState<FlinkJob[]>([]);
  const [configs, setConfigs] = useState<ConfigItem[]>([]);
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [dataFlowStats, setDataFlowStats] = useState<DataFlowStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [kafkaRes, flinkRes, configRes, healthRes, dataFlowRes] = await Promise.all([
        api.get('/api/v1/infrastructure/kafka/status'),
        api.get('/api/v1/infrastructure/flink/jobs'),
        api.get('/api/v1/infrastructure/config'),
        api.get('/api/v1/infrastructure/health'),
        api.get('/api/v1/infrastructure/data-flow/stats')
      ]);
      setKafkaStatus(kafkaRes.data);
      setFlinkJobs(flinkRes.data.jobs || []);
      setConfigs(Object.entries(configRes.data.configs || {}).map(([key, value]: [string, any]) => ({
        key,
        value,
        version: 1
      })));
      setHealth(healthRes.data);
      setDataFlowStats(dataFlowRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleStartDataFlow = async () => {
    try {
      setError(null);
      await api.post('/api/v1/infrastructure/data-flow/start');
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '启动数据流失败');
    }
  };

  const handleStopDataFlow = async () => {
    try {
      setError(null);
      await api.post('/api/v1/infrastructure/data-flow/stop');
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '停止数据流失败');
    }
  };

  const handleRecordMetric = async () => {
    try {
      setError(null);
      await api.post('/api/v1/infrastructure/monitoring/metrics');
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '记录指标失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">基础设施管理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 健康状态 */}
      <Card>
        <CardHeader>
          <CardTitle>基础设施健康状态</CardTitle>
        </CardHeader>
        <CardContent>
          {health && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">Kafka</div>
                <Badge variant={health.kafka ? 'default' : 'destructive'}>
                  {health.kafka ? '健康' : '异常'}
                </Badge>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">Flink</div>
                <Badge variant={health.flink ? 'default' : 'destructive'}>
                  {health.flink ? '健康' : '异常'}
                </Badge>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">存储</div>
                <Badge variant={health.storage ? 'default' : 'destructive'}>
                  {health.storage ? '健康' : '异常'}
                </Badge>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">配置中心</div>
                <Badge variant={health.config_center ? 'default' : 'destructive'}>
                  {health.config_center ? '健康' : '异常'}
                </Badge>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">监控</div>
                <Badge variant={health.monitoring ? 'default' : 'destructive'}>
                  {health.monitoring ? '健康' : '异常'}
                </Badge>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500 mb-1">数据流</div>
                <Badge variant={health.data_flow ? 'default' : 'destructive'}>
                  {health.data_flow ? '健康' : '异常'}
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Kafka 状态 */}
      <Card>
        <CardHeader>
          <CardTitle>Kafka 状态</CardTitle>
        </CardHeader>
        <CardContent>
          {kafkaStatus && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-500">连接状态</div>
                  <Badge variant={kafkaStatus.connected ? 'default' : 'destructive'}>
                    {kafkaStatus.connected ? '已连接' : '未连接'}
                  </Badge>
                </div>
                <div>
                  <div className="text-sm text-gray-500">消息总数</div>
                  <div className="text-2xl font-semibold">{kafkaStatus.total_messages}</div>
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-2">主题列表</div>
                <div className="flex flex-wrap gap-2">
                  {kafkaStatus.topics.map((topic) => (
                    <Badge key={topic} variant="outline">{topic}</Badge>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Flink 作业 */}
      <Card>
        <CardHeader>
          <CardTitle>Flink 作业 ({flinkJobs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {flinkJobs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无运行中的作业</div>
          ) : (
            <div className="space-y-2">
              {flinkJobs.map((job) => (
                <div key={job.job_name} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{job.job_name}</div>
                      <div className="text-sm text-gray-500">{job.job_type}</div>
                    </div>
                    <Badge variant={job.status === 'running' ? 'default' : 'secondary'}>
                      {job.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 数据流统计 */}
      <Card>
        <CardHeader>
          <CardTitle>数据流统计</CardTitle>
        </CardHeader>
        <CardContent>
          {dataFlowStats && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-gray-500">总处理数</div>
                <div className="text-2xl font-semibold">{dataFlowStats.total_processed}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">总分析数</div>
                <div className="text-2xl font-semibold">{dataFlowStats.total_analyzed}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">错误数</div>
                <div className="text-2xl font-semibold text-red-600">{dataFlowStats.total_errors}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">平均处理时间</div>
                <div className="text-2xl font-semibold">{dataFlowStats.avg_processing_time_ms.toFixed(2)}ms</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">错误率</div>
                <div className="text-2xl font-semibold">{(dataFlowStats.error_rate * 100).toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">分析率</div>
                <div className="text-2xl font-semibold">{(dataFlowStats.analysis_rate * 100).toFixed(2)}%</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 数据流控制 */}
      <Card>
        <CardHeader>
          <CardTitle>数据流控制</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Button onClick={handleStartDataFlow}>启动数据流</Button>
            <Button onClick={handleStopDataFlow} variant="outline">停止数据流</Button>
            <Button onClick={handleRecordMetric} variant="outline">记录指标</Button>
          </div>
        </CardContent>
      </Card>

      {/* 配置项 */}
      <Card>
        <CardHeader>
          <CardTitle>配置项 ({configs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {configs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无配置项</div>
          ) : (
            <div className="space-y-2">
              {configs.map((config) => (
                <div key={config.key} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{config.key}</div>
                      <div className="text-sm text-gray-500">
                        {typeof config.value === 'object' ? JSON.stringify(config.value) : String(config.value)}
                      </div>
                    </div>
                    <Badge variant="outline">v{config.version}</Badge>
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
