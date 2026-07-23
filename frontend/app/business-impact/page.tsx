'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface BusinessService {
  id: string;
  name: string;
  category: string;
  impactScore: number;
  status: 'healthy' | 'degraded' | 'down';
  affectedUsers: number;
  conversionRate: number;
  conversionRateChange: number;
  revenueImpact: number;
  lastUpdated: string;
}

interface UserExperienceMetric {
  id: string;
  name: string;
  value: number;
  change: number;
  status: 'good' | 'warning' | 'critical';
}

export default function BusinessImpactPage() {
  const [services, setServices] = useState<BusinessService[]>([
    {
      id: 'SVC-001',
      name: '电商服务',
      category: '核心业务',
      impactScore: 8.5,
      status: 'degraded',
      affectedUsers: 12000,
      conversionRate: 2.5,
      conversionRateChange: -15,
      revenueImpact: 50000,
      lastUpdated: new Date().toISOString(),
    },
    {
      id: 'SVC-002',
      name: '支付网关',
      category: '核心业务',
      impactScore: 9.2,
      status: 'down',
      affectedUsers: 8500,
      conversionRate: 0,
      conversionRateChange: -100,
      revenueImpact: 120000,
      lastUpdated: new Date(Date.now() - 300000).toISOString(),
    },
    {
      id: 'SVC-003',
      name: '用户中心',
      category: '支撑服务',
      impactScore: 4.5,
      status: 'healthy',
      affectedUsers: 0,
      conversionRate: 3.2,
      conversionRateChange: 5,
      revenueImpact: 0,
      lastUpdated: new Date(Date.now() - 600000).toISOString(),
    },
    {
      id: 'SVC-004',
      name: '搜索服务',
      category: '增值服务',
      impactScore: 6.8,
      status: 'degraded',
      affectedUsers: 3200,
      conversionRate: 1.8,
      conversionRateChange: -8,
      revenueImpact: 15000,
      lastUpdated: new Date(Date.now() - 900000).toISOString(),
    },
  ]);

  const [uxMetrics, setUxMetrics] = useState<UserExperienceMetric[]>([
    {
      id: 'UX-001',
      name: '页面加载时间',
      value: 3.2,
      change: 25,
      status: 'critical',
    },
    {
      id: 'UX-002',
      name: 'API响应时间',
      value: 450,
      change: 18,
      status: 'warning',
    },
    {
      id: 'UX-003',
      name: '错误率',
      value: 2.1,
      change: -5,
      status: 'good',
    },
    {
      id: 'UX-004',
      name: '用户满意度',
      value: 4.2,
      change: -12,
      status: 'warning',
    },
  ]);

  const getImpactColor = (score: number) => {
    if (score >= 8) return 'bg-red-100 text-red-800';
    if (score >= 5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'down':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getMetricStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">业务影响分析</h1>
        <div className="flex gap-2">
          <Button variant="outline">服务地图</Button>
          <Button>用户体验报告</Button>
        </div>
      </div>

      {/* 业务影响概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">受影响用户</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">23,700</p>
            <p className="text-sm text-gray-500">当前受影响</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">转化率下降</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">-23%</p>
            <p className="text-sm text-gray-500">较昨日</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">收入影响</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">¥185,000</p>
            <p className="text-sm text-gray-500">预计损失</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">服务健康度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">72%</p>
            <p className="text-sm text-gray-500">整体评分</p>
          </CardContent>
        </Card>
      </div>

      {/* 业务服务映射 */}
      <Card>
        <CardHeader>
          <CardTitle>业务服务映射</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {services.map((service) => (
              <div key={service.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium">{service.name}</h3>
                    <Badge variant="outline">{service.category}</Badge>
                    <Badge className={getStatusColor(service.status)}>
                      {service.status === 'healthy' ? '健康' : service.status === 'degraded' ? '降级' : '宕机'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">影响评分:</span>
                    <Badge className={getImpactColor(service.impactScore)}>
                      {service.impactScore}/10
                    </Badge>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">受影响用户:</span>
                    <span className="ml-2 font-medium">{service.affectedUsers.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">转化率:</span>
                    <span className="ml-2 font-medium">{service.conversionRate}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500">转化率变化:</span>
                    <span className={`ml-2 font-medium ${service.conversionRateChange < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {service.conversionRateChange > 0 ? '+' : ''}{service.conversionRateChange}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">收入影响:</span>
                    <span className="ml-2 font-medium text-red-600">¥{service.revenueImpact.toLocaleString()}</span>
                  </div>
                </div>
                <div className="mt-3 w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${service.impactScore >= 8 ? 'bg-red-500' : service.impactScore >= 5 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${service.impactScore * 10}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 用户体验指标 */}
      <Card>
        <CardHeader>
          <CardTitle>用户体验指标</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {uxMetrics.map((metric) => (
              <div key={metric.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">{metric.name}</h3>
                  <Badge className={getMetricStatusColor(metric.status)}>
                    {metric.status === 'good' ? '良好' : metric.status === 'warning' ? '警告' : '严重'}
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold">{metric.value}</span>
                  <span className={`text-sm ${metric.change < 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {metric.change > 0 ? '+' : ''}{metric.change}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 转化率追踪 */}
      <Card>
        <CardHeader>
          <CardTitle>转化率追踪</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 mb-4">
            <div className="flex gap-4">
              <Input placeholder="搜索服务..." className="max-w-xs" />
              <Select>
                <option value="">所有类别</option>
                <option value="core">核心业务</option>
                <option value="support">支撑服务</option>
                <option value="value">增值服务</option>
              </Select>
              <Select>
                <option value="">所有状态</option>
                <option value="healthy">健康</option>
                <option value="degraded">降级</option>
                <option value="down">宕机</option>
              </Select>
              <Button>搜索</Button>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>服务名称</TableHead>
                <TableHead>类别</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>当前转化率</TableHead>
                <TableHead>变化</TableHead>
                <TableHead>受影响用户</TableHead>
                <TableHead>收入影响</TableHead>
                <TableHead>最后更新</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {services.map((service) => (
                <TableRow key={service.id}>
                  <TableCell className="font-medium">{service.name}</TableCell>
                  <TableCell>{service.category}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(service.status)}>
                      {service.status === 'healthy' ? '健康' : service.status === 'degraded' ? '降级' : '宕机'}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{service.conversionRate}%</TableCell>
                  <TableCell className={service.conversionRateChange < 0 ? 'text-red-600' : 'text-green-600'}>
                    {service.conversionRateChange > 0 ? '+' : ''}{service.conversionRateChange}%
                  </TableCell>
                  <TableCell>{service.affectedUsers.toLocaleString()}</TableCell>
                  <TableCell className="text-red-600">¥{service.revenueImpact.toLocaleString()}</TableCell>
                  <TableCell className="text-sm">{new Date(service.lastUpdated).toLocaleString()}</TableCell>
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

      {/* 影响分析报告 */}
      <Card>
        <CardHeader>
          <CardTitle>影响分析报告</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <h3 className="font-medium text-red-800 mb-2">关键影响</h3>
              <ul className="text-sm text-red-700 space-y-1">
                <li>• 支付网关宕机导致转化率下降100%，预计收入损失¥120,000</li>
                <li>• 电商服务降级影响12,000用户，转化率下降15%</li>
                <li>• 搜索服务响应时间增加25%，影响3,200用户</li>
              </ul>
            </div>
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h3 className="font-medium text-yellow-800 mb-2">建议行动</h3>
              <ul className="text-sm text-yellow-700 space-y-1">
                <li>• 立即恢复支付网关服务，优先级最高</li>
                <li>• 优化电商服务性能，减少降级影响</li>
                <li>• 监控搜索服务性能，考虑扩容</li>
              </ul>
            </div>
            <div className="flex justify-end">
              <Button>生成完整报告</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
