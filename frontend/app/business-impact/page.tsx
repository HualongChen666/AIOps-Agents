'use client'

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

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
  const [services, setServices] = useState<BusinessService[]>([]);
  const [uxMetrics, setUxMetrics] = useState<UserExperienceMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedService, setSelectedService] = useState<BusinessService | null>(null);
  const [assessLoading, setAssessLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        setLoading(true);
        const [servicesRes, uxRes] = await Promise.all([
          api.get('/api/v1/business-impact/services'),
          api.get('/api/v1/business-impact/ux-metrics'),
        ]);
        if (!cancelled) {
          setServices(servicesRes.data.data || []);
          setUxMetrics(uxRes.data.data || []);
        }
      } catch (error) {
        // Errors are handled by the api interceptor toast.
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const overview = useMemo(() => {
    const impacted = services.filter((s) => s.status !== 'healthy');
    const affectedUsers = impacted.reduce((sum, s) => sum + s.affectedUsers, 0);
    const revenueImpact = impacted.reduce((sum, s) => sum + s.revenueImpact, 0);
    const conversionChange =
      affectedUsers > 0
        ? impacted.reduce((sum, s) => sum + s.affectedUsers * s.conversionRateChange, 0) / affectedUsers
        : 0;
    const healthyCount = services.filter((s) => s.status === 'healthy').length;
    const healthScore = services.length > 0 ? Math.round((healthyCount / services.length) * 100) : 100;
    return { affectedUsers, revenueImpact, conversionChange, healthScore };
  }, [services]);

  const criticalServices = useMemo(() => {
    return [...services].sort((a, b) => b.impactScore - a.impactScore).slice(0, 3);
  }, [services]);

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

  const getStatusText = (status: string) => {
    if (status === 'healthy') return '健康';
    if (status === 'degraded') return '降级';
    return '宕机';
  };

  const handleViewDetails = async (name: string) => {
    setAssessLoading(true);
    try {
      const res = await api.get(`/api/v1/business-impact/assess/${encodeURIComponent(name)}`);
      const data = res.data?.data ?? res.data;
      if (data) {
        setSelectedService(data as BusinessService);
      }
    } catch {
      // errors handled by api.ts interceptor
    } finally {
      setAssessLoading(false);
    }
  };

  const renderKeyFindings = () => {
    return criticalServices.map((service) => {
      if (service.status === 'down') {
        return `${service.name}宕机导致转化率下降${Math.abs(service.conversionRateChange)}%，预计收入损失¥${service.revenueImpact.toLocaleString()}`;
      }
      if (service.status === 'degraded') {
        return `${service.name}降级影响${service.affectedUsers.toLocaleString()}用户，转化率下降${Math.abs(service.conversionRateChange)}%`;
      }
      return `${service.name}状态${getStatusText(service.status)}，影响评分${service.impactScore}`;
    });
  };

  const renderRecommendations = () => {
    return criticalServices.slice(0, 3).map((service) => {
      if (service.status === 'down') {
        return `立即恢复${service.name}服务，优先级最高`;
      }
      if (service.status === 'degraded') {
        return `优化${service.name}性能，减少降级影响`;
      }
      return `持续监控${service.name}指标，确保稳定运行`;
    });
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
            <p className="text-3xl font-bold text-red-600">
              {overview.affectedUsers.toLocaleString()}
            </p>
            <p className="text-sm text-gray-500">当前受影响</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">转化率下降</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">
              {overview.conversionChange > 0 ? '+' : ''}
              {overview.conversionChange.toFixed(1)}%
            </p>
            <p className="text-sm text-gray-500">较昨日</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">收入影响</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              ¥{overview.revenueImpact.toLocaleString()}
            </p>
            <p className="text-sm text-gray-500">预计损失</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">服务健康度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{overview.healthScore}%</p>
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
            {loading && <p className="text-sm text-gray-500">加载中...</p>}
            {services.map((service) => (
              <div key={service.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium">{service.name}</h3>
                    <Badge variant="outline">{service.category}</Badge>
                    <Badge className={getStatusColor(service.status)}>
                      {getStatusText(service.status)}
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
            {loading && <p className="text-sm text-gray-500">加载中...</p>}
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
                      {getStatusText(service.status)}
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
                    <Button variant="outline" size="sm" onClick={() => handleViewDetails(service.name)} disabled={assessLoading}>
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
                {renderKeyFindings().map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h3 className="font-medium text-yellow-800 mb-2">建议行动</h3>
              <ul className="text-sm text-yellow-700 space-y-1">
                {renderRecommendations().map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
            <div className="flex justify-end">
              <Button>生成完整报告</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedService && (
        <Card>
          <CardHeader>
            <CardTitle>{selectedService.name} 业务影响详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><span className="text-gray-500">类别</span><div>{selectedService.category}</div></div>
              <div><span className="text-gray-500">状态</span><div>{getStatusText(selectedService.status)}</div></div>
              <div><span className="text-gray-500">影响评分</span><div>{selectedService.impactScore}</div></div>
              <div><span className="text-gray-500">受影响用户</span><div>{selectedService.affectedUsers.toLocaleString()}</div></div>
              <div><span className="text-gray-500">转化率</span><div>{selectedService.conversionRate}%</div></div>
              <div><span className="text-gray-500">转化率变化</span><div>{selectedService.conversionRateChange}%</div></div>
              <div><span className="text-gray-500">收入影响</span><div>¥{selectedService.revenueImpact.toLocaleString()}</div></div>
              <div><span className="text-gray-500">最后更新</span><div>{new Date(selectedService.lastUpdated).toLocaleString()}</div></div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
