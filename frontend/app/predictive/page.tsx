'use client'

import { useState } from 'react';
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
  const [deviceHealth, setDeviceHealth] = useState<DeviceHealth[]>([
    {
      id: 'DEV-001',
      name: 'web-server-01',
      type: '服务器',
      healthScore: 85,
      predictedFailure: '2024-03-15',
      status: 'healthy',
    },
    {
      id: 'DEV-002',
      name: 'database-primary',
      type: '数据库',
      healthScore: 65,
      predictedFailure: '2024-02-20',
      status: 'warning',
    },
    {
      id: 'DEV-003',
      name: 'storage-array-01',
      type: '存储',
      healthScore: 45,
      predictedFailure: '2024-02-10',
      status: 'critical',
    },
  ]);

  const [maintenanceTasks, setMaintenanceTasks] = useState<MaintenanceTask[]>([
    {
      id: 'MT-001',
      device: 'storage-array-01',
      type: 'predictive',
      scheduledDate: '2024-02-10',
      priority: 'high',
      status: 'pending',
      estimatedDuration: '4小时',
      description: '更换故障磁盘，重建RAID阵列',
    },
    {
      id: 'MT-002',
      device: 'database-primary',
      type: 'preventive',
      scheduledDate: '2024-02-20',
      priority: 'medium',
      status: 'pending',
      estimatedDuration: '2小时',
      description: '数据库索引优化和统计信息更新',
    },
    {
      id: 'MT-003',
      device: 'web-server-01',
      type: 'preventive',
      scheduledDate: '2024-03-01',
      priority: 'low',
      status: 'completed',
      estimatedDuration: '1小时',
      description: '系统补丁更新和安全加固',
    },
  ]);

  const [failurePredictions, setFailurePredictions] = useState<FailurePrediction[]>([
    {
      deviceId: 'DEV-003',
      deviceName: 'storage-array-01',
      failureType: '磁盘故障',
      probability: 85,
      timeframe: '7天内',
      confidence: 92,
      recommendedActions: [
        '立即备份关键数据',
        '准备备用磁盘',
        '安排维护窗口',
        '通知相关团队',
      ],
    },
    {
      deviceId: 'DEV-002',
      deviceName: 'database-primary',
      failureType: '性能下降',
      probability: 65,
      timeframe: '30天内',
      confidence: 78,
      recommendedActions: [
        '优化慢查询',
        '增加缓存层',
        '考虑读写分离',
        '监控磁盘IO',
      ],
    },
  ]);

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
            <p className="text-gray-500">设备健康趋势图 (使用ECharts渲染)</p>
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
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">资源优化</h4>
              <p className="text-sm text-gray-600 mb-3">
                建议将MT-001和MT-002合并到同一维护窗口，可节省约30%的维护时间
              </p>
              <Button variant="outline" size="sm">
                应用优化
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">成本优化</h4>
              <p className="text-sm text-gray-600 mb-3">
                预防性维护可降低故障修复成本约40%，建议增加预防性维护比例
              </p>
              <Button variant="outline" size="sm">
                查看详情
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">时间优化</h4>
              <p className="text-sm text-gray-600 mb-3">
                建议将低优先级任务安排在非业务高峰期，减少对业务影响
              </p>
              <Button variant="outline" size="sm">
                调整计划
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">人员优化</h4>
              <p className="text-sm text-gray-600 mb-3">
                根据技能匹配度，建议分配特定工程师处理数据库相关维护任务
              </p>
              <Button variant="outline" size="sm">
                分配人员
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
