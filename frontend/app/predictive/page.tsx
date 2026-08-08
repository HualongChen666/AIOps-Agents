'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface DeviceHealth {
  id: string;
  name: string;
  type: string;
  healthScore: number;
  predictedFailure: string;
  status: 'healthy' | 'warning' | 'critical';
}

interface MaintenanceTask {
  id: string;
  device: string;
  type: 'preventive' | 'corrective' | 'predictive';
  scheduledDate: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in-progress' | 'completed';
  estimatedDuration: string;
  description: string;
}

interface FailurePrediction {
  deviceId: string;
  deviceName: string;
  failureType: string;
  probability: number;
  timeframe: string;
  confidence: number;
  recommendedActions: string[];
}

export default function PredictivePage() {
  const [selectedTimeRange, setSelectedTimeRange] = useState('30d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deviceHealth, setDeviceHealth] = useState<DeviceHealth[]>([]);
  const [maintenanceTasks, setMaintenanceTasks] = useState<MaintenanceTask[]>([]);
  const [failurePredictions, setFailurePredictions] = useState<FailurePrediction[]>([]);
  const [recommendations, setRecommendations] = useState<{ id: string; title: string; description: string; action: string; priority: string }[]>([]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'warning':
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'critical':
      case 'in-progress':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
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

  useEffect(() => {
    async function loadPredictiveData() {
      const projectedDate = (days: number) => {
        const d = new Date();
        d.setDate(d.getDate() + days);
        return d.toISOString().split('T')[0];
      };

      const buildDevice = (id: string, name: string, type: string, usage: number): DeviceHealth => {
        const healthScore = Math.max(0, Math.min(100, Math.round(100 - usage)));
        let status: DeviceHealth['status'] = 'healthy';
        let failDays = 90;
        if (healthScore < 50) {
          status = 'critical';
          failDays = 7;
        } else if (healthScore < 70) {
          status = 'warning';
          failDays = 30;
        }
        return {
          id,
          name,
          type,
          healthScore,
          predictedFailure: projectedDate(failDays),
          status,
        };
      };

      const [historyResult, aiResult] = await Promise.allSettled([
        api.get('/api/v1/metrics/history'),
        api.post('/api/ai/analyze', {
          query: '请分析当前系统健康状态并给出预测性维护建议',
          include_metrics: true,
          include_rich_context: true,
          platform: 'windows',
        }),
      ]);

      const recRes = await api.get('/api/v1/metrics/predictions').catch(() => null);
      if (recRes?.data?.data) {
        setRecommendations(recRes.data.data);
      }

      if (historyResult.status === 'fulfilled') {
        const historyData = historyResult.value.data || {};
        const cpuArr = historyData.cpu || [];
        const memoryArr = historyData.memory || [];
        const netArr = historyData.net_in || [];

        const devices: DeviceHealth[] = [];
        if (cpuArr.length) devices.push(buildDevice('DEV-CPU', 'CPU', 'CPU', cpuArr[cpuArr.length - 1]));
        if (memoryArr.length) devices.push(buildDevice('DEV-MEM', 'Memory', '内存', memoryArr[memoryArr.length - 1]));
        if (netArr.length) devices.push(buildDevice('DEV-NET', 'Network', '网络', netArr[netArr.length - 1]));
        setDeviceHealth(devices);
      }

      if (aiResult.status === 'fulfilled') {
        const analysis = aiResult.value.data?.analysis || {};
        const candidates = Array.isArray(analysis.candidates) ? analysis.candidates : [];

        const predictions: FailurePrediction[] = candidates.map((c: any, i: number) => {
          const actions = String(analysis.recommended_action || '')
            .split(/[；;，,\n]/)
            .map((s: string) => s.trim())
            .filter(Boolean);
          if (analysis.multi_root_cause_note) {
            actions.unshift(String(analysis.multi_root_cause_note));
          }
          return {
            deviceId: `RC-${i + 1}`,
            deviceName: String(c.root_cause || '未知组件'),
            failureType: String(c.root_cause || '未知故障'),
            probability: Math.round((c.confidence || 0) * 100),
            timeframe: c.is_verifiable ? '已可验证' : '待验证',
            confidence: Math.round(((analysis.data_assessment?.reliability_score ?? 0.8) * 100)),
            recommendedActions: actions.length ? actions : ['关注并监控相关指标'],
          };
        });
        setFailurePredictions(predictions);

        const tasks: MaintenanceTask[] = predictions.map((p, i) => ({
          id: `MT-${i + 1}`,
          device: p.deviceName,
          type: 'predictive' as MaintenanceTask['type'],
          scheduledDate: projectedDate(p.probability > 70 ? 7 : p.probability > 40 ? 14 : 30),
          priority: (p.probability > 70 ? 'high' : p.probability > 40 ? 'medium' : 'low') as MaintenanceTask['priority'],
          status: 'pending' as MaintenanceTask['status'],
          estimatedDuration: '2小时',
          description: p.failureType,
        }));
        setMaintenanceTasks(tasks);
      }

      if (historyResult.status === 'rejected' && aiResult.status === 'rejected') {
        setError('预测数据加载失败，请稍后重试');
      } else {
        setError(null);
      }

      setLoading(false);
    }

    loadPredictiveData();
  }, []);

  if (error) {
    return (
      <div className="p-6 text-red-600">
        加载预测数据失败: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">预测性维护</h1>
        <div className="flex gap-2">
          <Select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
          >
            <option value="7d">7天</option>
            <option value="30d">30天</option>
            <option value="90d">90天</option>
          </Select>
          <Button>刷新预测</Button>
        </div>
      </div>

      {/* 设备健康概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">健康设备</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {deviceHealth.filter(d => d.status === 'healthy').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">总计 {deviceHealth.length} 台</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告设备</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">
              {deviceHealth.filter(d => d.status === 'warning').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">需要关注</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">严重设备</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {deviceHealth.filter(d => d.status === 'critical').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">立即处理</p>
          </CardContent>
        </Card>
      </div>

      {/* 设备健康预测 */}
      <Card>
        <CardHeader>
          <CardTitle>设备健康预测</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
            {loading ? (
              <p className="text-gray-500">加载预测数据中...</p>
            ) : (
              <p className="text-gray-500">设备健康趋势图</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 设备健康列表 */}
      <Card>
        <CardHeader>
          <CardTitle>设备健康状态</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>设备ID</TableHead>
                <TableHead>设备名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>健康评分</TableHead>
                <TableHead>预测故障时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {deviceHealth.map((device) => (
                <TableRow key={device.id}>
                  <TableCell className="font-mono text-sm">{device.id}</TableCell>
                  <TableCell className="font-medium">{device.name}</TableCell>
                  <TableCell>{device.type}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${device.healthScore > 70 ? 'bg-green-500' : device.healthScore > 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          style={{ width: `${device.healthScore}%` }}
                        />
                      </div>
                      <span className="text-sm">{device.healthScore}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">{device.predictedFailure}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(device.status)}>
                      {device.status === 'healthy' ? '健康' : device.status === 'warning' ? '警告' : '严重'}
                    </Badge>
                  </TableCell>
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

      {/* 故障概率预测 */}
      <Card>
        <CardHeader>
          <CardTitle>故障概率预测</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {failurePredictions.map((prediction) => (
              <div key={prediction.deviceId} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium text-gray-900">{prediction.deviceName}</h3>
                      <Badge className={prediction.probability > 70 ? 'bg-red-100 text-red-800' : prediction.probability > 40 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}>
                        {prediction.failureType}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                      <span>故障概率: <span className="font-bold">{prediction.probability}%</span></span>
                      <span>时间范围: {prediction.timeframe}</span>
                      <span>置信度: {prediction.confidence}%</span>
                    </div>
                    <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden mb-3">
                      <div
                        className={`h-full transition-all ${prediction.probability > 70 ? 'bg-red-500' : prediction.probability > 40 ? 'bg-yellow-500' : 'bg-green-500'}`}
                        style={{ width: `${prediction.probability}%` }}
                      />
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    查看详情
                  </Button>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">推荐行动:</h4>
                  <ul className="space-y-1">
                    {prediction.recommendedActions.map((action, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-blue-500">•</span>
                        <span>{action}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 维护计划 */}
      <Card>
        <CardHeader>
          <CardTitle>维护计划</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务ID</TableHead>
                <TableHead>设备</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>计划日期</TableHead>
                <TableHead>预计时长</TableHead>
                <TableHead>优先级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {maintenanceTasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="font-mono text-sm">{task.id}</TableCell>
                  <TableCell className="font-medium">{task.device}</TableCell>
                  <TableCell>
                    {task.type === 'preventive' ? '预防性' : task.type === 'corrective' ? '纠正性' : '预测性'}
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">{task.scheduledDate}</TableCell>
                  <TableCell className="text-sm text-gray-500">{task.estimatedDuration}</TableCell>
                  <TableCell>
                    <Badge className={getPriorityColor(task.priority)}>
                      {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(task.status)}>
                      {task.status === 'pending' ? '待处理' : task.status === 'in-progress' ? '进行中' : '已完成'}
                    </Badge>
                  </TableCell>
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

      {/* 维护优化建议 */}
      <Card>
        <CardHeader>
          <CardTitle>维护计划优化</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.length === 0 ? (
              <p className="text-sm text-gray-500 md:col-span-2">暂无预测性维护建议</p>
            ) : (
              recommendations.map((rec) => (
                <div key={rec.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{rec.title}</h4>
                    <Badge className={getPriorityColor(rec.priority)}>
                      {rec.priority === 'high' ? '高' : rec.priority === 'medium' ? '中' : '低'}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{rec.description}</p>
                  <Button variant="outline" size="sm">
                    {rec.action || '查看详情'}
                  </Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
