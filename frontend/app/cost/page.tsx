'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface CostData {
  service: string;
  currentCost: number;
  previousCost: number;
  change: number;
  unit: string;
}

interface OptimizationSuggestion {
  id: string;
  title: string;
  description: string;
  potentialSavings: number;
  effort: 'low' | 'medium' | 'high';
}

interface CostAnomaly {
  id: string;
  service: string;
  type: 'spike' | 'trend' | 'budget_exceeded';
  severity: 'low' | 'medium' | 'high';
  description: string;
  detectedAt: string;
  value: number;
  threshold: number;
}

interface CostAllocation {
  id: string;
  department: string;
  project: string;
  allocatedCost: number;
  actualCost: number;
  variance: number;
}

interface BudgetAlert {
  id: string;
  name: string;
  budget: number;
  spent: number;
  threshold: number;
  status: 'normal' | 'warning' | 'critical';
  period: string;
}

export default function CostPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [costData, setCostData] = useState<CostData[]>([
    { service: 'web-service', currentCost: 1200, previousCost: 1000, change: 20, unit: '¥/月' },
    { service: 'api-gateway', currentCost: 800, previousCost: 850, change: -5.9, unit: '¥/月' },
    { service: 'database', currentCost: 2500, previousCost: 2200, change: 13.6, unit: '¥/月' },
    { service: 'cache-service', currentCost: 400, previousCost: 400, change: 0, unit: '¥/月' },
    { service: 'storage', currentCost: 600, previousCost: 550, change: 9.1, unit: '¥/月' },
  ]);

  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([
    {
      id: 'OPT-001',
      title: '使用预留实例',
      description: 'web-service运行稳定，建议购买预留实例可节省30%成本',
      potentialSavings: 360,
      effort: 'low',
    },
    {
      id: 'OPT-002',
      title: '清理未使用资源',
      description: '发现3个未使用的EBS卷，建议删除以节省存储成本',
      potentialSavings: 150,
      effort: 'low',
    },
    {
      id: 'OPT-003',
      title: '优化数据库配置',
      description: '数据库实例规格过高，建议降级至适合的规格',
      potentialSavings: 500,
      effort: 'medium',
    },
  ]);

  const [costAnomalies, setCostAnomalies] = useState<CostAnomaly[]>([
    {
      id: 'ANM-001',
      service: 'database',
      type: 'spike',
      severity: 'high',
      description: '数据库成本突然增加45%，超出阈值',
      detectedAt: new Date().toISOString(),
      value: 2500,
      threshold: 2000,
    },
    {
      id: 'ANM-002',
      service: 'web-service',
      type: 'trend',
      severity: 'medium',
      description: 'web-service成本持续上升，呈增长趋势',
      detectedAt: new Date(Date.now() - 3600000).toISOString(),
      value: 1200,
      threshold: 1000,
    },
  ]);

  const [costAllocations, setCostAllocations] = useState<CostAllocation[]>([
    {
      id: 'ALL-001',
      department: '研发部',
      project: 'AIOps平台',
      allocatedCost: 10000,
      actualCost: 8500,
      variance: -1500,
    },
    {
      id: 'ALL-002',
      department: '运维部',
      project: '基础设施',
      allocatedCost: 8000,
      actualCost: 9200,
      variance: 1200,
    },
    {
      id: 'ALL-003',
      department: '产品部',
      project: '业务系统',
      allocatedCost: 15000,
      actualCost: 14800,
      variance: -200,
    },
  ]);

  const [budgetAlerts, setBudgetAlerts] = useState<BudgetAlert[]>([
    {
      id: 'BG-001',
      name: '生产环境预算',
      budget: 20000,
      spent: 17500,
      threshold: 85,
      status: 'warning',
      period: '2026年6月',
    },
    {
      id: 'BG-002',
      name: '开发环境预算',
      budget: 5000,
      spent: 5200,
      threshold: 100,
      status: 'critical',
      period: '2026年6月',
    },
    {
      id: 'BG-003',
      name: '测试环境预算',
      budget: 3000,
      spent: 1800,
      threshold: 90,
      status: 'normal',
      period: '2026年6月',
    },
  ]);

  const totalCost = costData.reduce((sum, item) => sum + item.currentCost, 0);
  const totalSavings = suggestions.reduce((sum, item) => sum + item.potentialSavings, 0);

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-red-600';
    if (change < 0) return 'text-green-600';
    return 'text-gray-600';
  };

  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
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

  const getAnomalyTypeColor = (type: string) => {
    switch (type) {
      case 'spike':
        return 'bg-red-100 text-red-800';
      case 'trend':
        return 'bg-orange-100 text-orange-800';
      case 'budget_exceeded':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getBudgetStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'normal':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">成本监控</h1>
        <div className="flex gap-2">
          <Select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
          >
            <option value="day">日</option>
            <option value="week">周</option>
            <option value="month">月</option>
            <option value="year">年</option>
          </Select>
          <Button>刷新数据</Button>
        </div>
      </div>

      {/* 成本概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总成本</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">¥{totalCost}</p>
            <p className="text-sm text-gray-500 mt-1">本月累计</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">环比变化</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">+8.5%</p>
            <p className="text-sm text-gray-500 mt-1">较上月</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">潜在节省</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">¥{totalSavings}</p>
            <p className="text-sm text-gray-500 mt-1">优化建议</p>
          </CardContent>
        </Card>
      </div>

      {/* 成本趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>成本趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">成本趋势图 (使用ECharts渲染)</p>
          </div>
        </CardContent>
      </Card>

      {/* 服务成本明细 */}
      <Card>
        <CardHeader>
          <CardTitle>服务成本明细</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>服务</TableHead>
                <TableHead>当前成本</TableHead>
                <TableHead>上期成本</TableHead>
                <TableHead>变化</TableHead>
                <TableHead>占比</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {costData.map((item) => (
                <TableRow key={item.service}>
                  <TableCell className="font-medium">{item.service}</TableCell>
                  <TableCell>¥{item.currentCost}</TableCell>
                  <TableCell>¥{item.previousCost}</TableCell>
                  <TableCell className={getChangeColor(item.change)}>
                    {item.change > 0 ? '+' : ''}{item.change.toFixed(1)}%
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600"
                          style={{ width: `${(item.currentCost / totalCost) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">
                        {((item.currentCost / totalCost) * 100).toFixed(1)}%
                      </span>
                    </div>
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

      {/* 优化建议 */}
      <Card>
        <CardHeader>
          <CardTitle>成本优化建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {suggestions.map((suggestion) => (
              <div key={suggestion.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium text-gray-900">{suggestion.title}</h3>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getEffortColor(suggestion.effort)}`}>
                        {suggestion.effort === 'low' ? '低投入' : suggestion.effort === 'medium' ? '中投入' : '高投入'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{suggestion.description}</p>
                    <p className="text-sm font-medium text-green-600">
                      预计节省: ¥{suggestion.potentialSavings}/月
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button size="sm">
                      应用
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 成本预算设置 */}
      <Card>
        <CardHeader>
          <CardTitle>成本预算设置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">月度预算</label>
              <Select>
                <option value="5000">¥5,000</option>
                <option value="10000">¥10,000</option>
                <option value="20000">¥20,000</option>
                <option value="50000">¥50,000</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">告警阈值</label>
              <Select>
                <option value="80">80%</option>
                <option value="90">90%</option>
                <option value="95">95%</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">预算周期</label>
              <Select>
                <option value="monthly">月度</option>
                <option value="quarterly">季度</option>
                <option value="yearly">年度</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">自动告警</label>
              <Select>
                <option value="enabled">启用</option>
                <option value="disabled">禁用</option>
              </Select>
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <Button>保存配置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 成本异常检测 */}
      <Card>
        <CardHeader>
          <CardTitle>成本异常检测</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {costAnomalies.map((anomaly) => (
              <div key={anomaly.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium text-gray-900">{anomaly.service}</h3>
                      <Badge className={getAnomalyTypeColor(anomaly.type)}>
                        {anomaly.type === 'spike' ? '突增' : anomaly.type === 'trend' ? '趋势' : '预算超支'}
                      </Badge>
                      <Badge className={getSeverityColor(anomaly.severity)}>
                        {anomaly.severity === 'high' ? '严重' : anomaly.severity === 'medium' ? '中等' : '轻微'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{anomaly.description}</p>
                    <div className="flex gap-4 text-sm text-gray-500">
                      <span>检测时间: {new Date(anomaly.detectedAt).toLocaleString()}</span>
                      <span>当前值: ¥{anomaly.value}</span>
                      <span>阈值: ¥{anomaly.threshold}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button size="sm">
                      处理
                    </Button>
                  </div>
                </div>
              </div>
            ))}
            {costAnomalies.length === 0 && (
              <p className="text-center text-gray-500 py-8">暂无成本异常</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 成本分配 */}
      <Card>
        <CardHeader>
          <CardTitle>成本分配</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-end mb-4">
            <Button>添加分配规则</Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>部门</TableHead>
                <TableHead>项目</TableHead>
                <TableHead>分配预算</TableHead>
                <TableHead>实际成本</TableHead>
                <TableHead>差异</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {costAllocations.map((allocation) => (
                <TableRow key={allocation.id}>
                  <TableCell className="font-medium">{allocation.department}</TableCell>
                  <TableCell>{allocation.project}</TableCell>
                  <TableCell>¥{allocation.allocatedCost}</TableCell>
                  <TableCell>¥{allocation.actualCost}</TableCell>
                  <TableCell className={allocation.variance > 0 ? 'text-red-600' : 'text-green-600'}>
                    {allocation.variance > 0 ? '+' : ''}¥{allocation.variance}
                  </TableCell>
                  <TableCell>
                    <Badge className={allocation.variance > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}>
                      {allocation.variance > 0 ? '超支' : '节约'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        编辑
                      </Button>
                      <Button variant="outline" size="sm">
                        删除
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 预算告警 */}
      <Card>
        <CardHeader>
          <CardTitle>预算告警</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-end mb-4">
            <Button>添加预算</Button>
          </div>
          <div className="space-y-4">
            {budgetAlerts.map((alert) => (
              <div key={alert.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium text-gray-900">{alert.name}</h3>
                      <Badge className={getBudgetStatusColor(alert.status)}>
                        {alert.status === 'critical' ? '严重' : alert.status === 'warning' ? '警告' : '正常'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">周期: {alert.period}</p>
                    <div className="flex items-center gap-4 mb-2">
                      <div className="flex-1">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-gray-600">预算使用</span>
                          <span className="font-medium">
                            ¥{alert.spent} / ¥{alert.budget} ({((alert.spent / alert.budget) * 100).toFixed(1)}%)
                          </span>
                        </div>
                        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              alert.status === 'critical' ? 'bg-red-500' : alert.status === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                            }`}
                            style={{ width: `${Math.min((alert.spent / alert.budget) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-500">
                      告警阈值: {alert.threshold}% | 剩余预算: ¥{alert.budget - alert.spent}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button variant="outline" size="sm">
                      编辑
                    </Button>
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
