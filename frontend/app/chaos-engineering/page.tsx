'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface ChaosExperiment {
  id: string;
  name: string;
  type: 'cpu-overload' | 'network-latency' | 'disk-failure' | 'service-restart';
  target: string;
  status: 'scheduled' | 'running' | 'completed' | 'failed';
  duration: number;
  scheduledTime: Date;
  impact: 'low' | 'medium' | 'high';
}

interface ExperimentResult {
  id: string;
  experimentId: string;
  startTime: Date;
  endTime: Date;
  duration: number;
  affectedServices: string[];
  metrics: {
    cpu: number;
    memory: number;
    latency: number;
    errorRate: number;
  };
  recoveryTime: number;
  status: 'success' | 'partial' | 'failed';
}

interface FaultTemplate {
  id: string;
  name: string;
  type: string;
  description: string;
  parameters: string[];
}

export default function ChaosEngineeringPage() {
  const [selectedTab, setSelectedTab] = useState('experiments');
  const [selectedExperiment, setSelectedExperiment] = useState<ChaosExperiment | null>(null);
  const [enabled, setEnabled] = useState(false);

  const [experiments, setExperiments] = useState<ChaosExperiment[]>([]);

  const [experimentResults, setExperimentResults] = useState<ExperimentResult[]>([]);

  const [faultTemplates, setFaultTemplates] = useState<FaultTemplate[]>([
    {
      id: 'TPL-001',
      name: 'CPU过载',
      type: 'cpu-overload',
      description: '模拟CPU使用率过高场景',
      parameters: ['target', 'duration', 'load-percent'],
    },
    {
      id: 'TPL-002',
      name: '网络延迟',
      type: 'network-latency',
      description: '模拟网络延迟增加',
      parameters: ['target', 'duration', 'latency-ms'],
    },
    {
      id: 'TPL-003',
      name: '磁盘故障',
      type: 'disk-failure',
      description: '模拟磁盘读写失败',
      parameters: ['target', 'duration', 'failure-type'],
    },
    {
      id: 'TPL-004',
      name: '服务重启',
      type: 'service-restart',
      description: '模拟服务意外重启',
      parameters: ['target', 'restart-delay'],
    },
  ]);

  const mapBackendExperimentType = (backendType: string): string => {
    switch (backendType) {
      case 'latency_injection':
      case 'network_partition':
        return 'network-latency';
      case 'resource_limitation':
        return 'cpu-overload';
      case 'fault_injection':
        return 'disk-failure';
      case 'service_failure':
        return 'service-restart';
      default:
        return 'network-latency';
    }
  };

  const mapBackendStatus = (backendStatus: string): ChaosExperiment['status'] => {
    switch (backendStatus) {
      case 'running':
        return 'running';
      case 'completed':
        return 'completed';
      case 'failed':
        return 'failed';
      default:
        return 'scheduled';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'cpu-overload':
        return 'CPU过载';
      case 'network-latency':
        return '网络延迟';
      case 'disk-failure':
        return '磁盘故障';
      case 'service-restart':
        return '服务重启';
      default:
        return type;
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const [statusRes, experimentsRes] = await Promise.all([
          api.get('/api/v1/chaos/status'),
          api.get('/api/v1/chaos/experiments?limit=20'),
        ]);

        const statusData = statusRes.data?.data ?? {};
        setEnabled(Boolean(statusData.enabled));

        const expList = experimentsRes.data?.data?.experiments ?? [];
        const mappedExperiments: ChaosExperiment[] = expList.map((item: any, idx: number) => {
          const type = mapBackendExperimentType(item.experiment);
          const impact: ChaosExperiment['impact'] =
            type === 'network-latency' || type === 'disk-failure' ? 'high' : 'medium';
          return {
            id: `EXP-${String(idx + 1).padStart(3, '0')}`,
            name: getTypeLabel(type),
            type: type as ChaosExperiment['type'],
            target: item.target || 'unknown',
            status: mapBackendStatus(item.status),
            duration: Math.round(item.duration_seconds || 0),
            scheduledTime: new Date(item.start_time || Date.now()),
            impact,
          };
        });
        setExperiments(mappedExperiments);

        const mappedResults: ExperimentResult[] = expList.map((item: any, idx: number) => {
          const resultStatus: ExperimentResult['status'] = item.success
            ? 'success'
            : item.status === 'partial'
              ? 'partial'
              : 'failed';
          return {
            id: `RES-${String(idx + 1).padStart(3, '0')}`,
            experimentId: `EXP-${String(idx + 1).padStart(3, '0')}`,
            startTime: new Date(item.start_time || Date.now()),
            endTime: item.end_time ? new Date(item.end_time) : new Date(item.start_time || Date.now()),
            duration: Math.round(item.duration_seconds || 0),
            affectedServices: [],
            metrics: {
              cpu: 0,
              memory: 0,
              latency: 0,
              errorRate: 0,
            },
            recoveryTime: 0,
            status: resultStatus,
          };
        });
        setExperimentResults(mappedResults);
      } catch (error) {
        // api interceptor already shows error toast
      }
    })();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'scheduled':
        return 'bg-yellow-100 text-yellow-800';
      case 'partial':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
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
        <h1 className="text-3xl font-bold text-gray-900">混沌工程</h1>
        <div className="flex items-center gap-2">
          <Badge className={enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
            {enabled ? '已启用' : '已禁用'}
          </Badge>
          <Button>创建实验</Button>
        </div>
      </div>

      {/* 混沌实验概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中实验</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">
              {experiments.filter((e) => e.status === 'running').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已完成实验</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {experiments.filter((e) => e.status === 'completed').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">失败实验</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {experiments.filter((e) => e.status === 'failed').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均恢复时间</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-600">45s</p>
          </CardContent>
        </Card>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 border-b">
        <Button
          variant={selectedTab === 'experiments' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('experiments')}
        >
          实验管理
        </Button>
        <Button
          variant={selectedTab === 'results' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('results')}
        >
          实验结果
        </Button>
        <Button
          variant={selectedTab === 'templates' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('templates')}
        >
          故障模板
        </Button>
        <Button
          variant={selectedTab === 'dashboard' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('dashboard')}
        >
          仪表盘
        </Button>
      </div>

      {/* 实验管理 */}
      {selectedTab === 'experiments' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>故障注入实验管理</CardTitle>
              <div className="flex gap-2">
                <select className="border border-gray-300 rounded px-3 py-1 text-sm">
                  <option>全部状态</option>
                  <option>运行中</option>
                  <option>已完成</option>
                  <option>已失败</option>
                  <option>已计划</option>
                </select>
                <Button variant="outline">导出</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {experiments.map((experiment) => (
                <div
                  key={experiment.id}
                  className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${selectedExperiment?.id === experiment.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  onClick={() => setSelectedExperiment(experiment)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge className={getStatusColor(experiment.status)}>
                        {experiment.status === 'running' ? '运行中' : experiment.status === 'completed' ? '已完成' : experiment.status === 'failed' ? '失败' : '已计划'}
                      </Badge>
                      <span className="font-medium">{experiment.name}</span>
                    </div>
                    <Badge className={getImpactColor(experiment.impact)}>
                      {experiment.impact === 'high' ? '高影响' : experiment.impact === 'medium' ? '中影响' : '低影响'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">类型: </span>
                      <span>{getTypeLabel(experiment.type)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">目标: </span>
                      <span>{experiment.target}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">持续时间: </span>
                      <span>{experiment.duration}s</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    计划时间: {experiment.scheduledTime.toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 实验结果 */}
      {selectedTab === 'results' && (
        <Card>
          <CardHeader>
            <CardTitle>实验结果分析</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {experimentResults.map((result) => (
                <div key={result.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="font-medium">实验 #{result.experimentId}</h4>
                      <p className="text-sm text-gray-500">
                        {result.startTime.toLocaleString()} - {result.endTime.toLocaleString()}
                      </p>
                    </div>
                    <Badge className={getStatusColor(result.status)}>
                      {result.status === 'success' ? '成功' : result.status === 'partial' ? '部分成功' : '失败'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <p className="text-sm text-gray-500">受影响服务</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {result.affectedServices.map((service) => (
                          <Badge key={service} variant="outline" className="text-xs">
                            {service}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">恢复时间</p>
                      <p className="font-medium">{result.recoveryTime}s</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-4 text-sm p-3 bg-gray-50 rounded">
                    <div>
                      <p className="text-gray-500">CPU峰值</p>
                      <p className="font-medium">{result.metrics.cpu}%</p>
                    </div>
                    <div>
                      <p className="text-gray-500">内存峰值</p>
                      <p className="font-medium">{result.metrics.memory}%</p>
                    </div>
                    <div>
                      <p className="text-gray-500">延迟峰值</p>
                      <p className="font-medium">{result.metrics.latency}ms</p>
                    </div>
                    <div>
                      <p className="text-gray-500">错误率</p>
                      <p className="font-medium">{result.metrics.errorRate}%</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button variant="outline" size="sm">
                      导出报告
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 故障模板 */}
      {selectedTab === 'templates' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>故障场景模板库</CardTitle>
              <Button>创建模板</Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {faultTemplates.map((template) => (
                <div key={template.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{template.name}</h4>
                    <Badge variant="outline">{template.type}</Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                  <div className="space-y-1">
                    <p className="text-xs text-gray-500">参数:</p>
                    <div className="flex flex-wrap gap-1">
                      {template.parameters.map((param) => (
                        <Badge key={param} variant="secondary" className="text-xs">
                          {param}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Button variant="outline" size="sm" className="flex-1">
                      使用模板
                    </Button>
                    <Button variant="outline" size="sm">
                      编辑
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 仪表盘 */}
      {selectedTab === 'dashboard' && (
        <Card>
          <CardHeader>
            <CardTitle>混沌实验仪表盘</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h4 className="font-medium mb-3">实验执行监控</h4>
                <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-400">实时实验执行监控图表</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-3">故障影响分布</h4>
                  <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                    <p className="text-gray-400">故障影响分布图表</p>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-3">恢复时间趋势</h4>
                  <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                    <p className="text-gray-400">恢复时间趋势图表</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
