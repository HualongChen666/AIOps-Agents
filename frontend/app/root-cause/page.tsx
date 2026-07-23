'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';

interface RootCauseNode {
  id: string;
  type: 'service' | 'metric' | 'alert';
  name: string;
  status: 'normal' | 'warning' | 'critical';
  probability: number;
}

interface RootCausePath {
  nodes: string[];
  probability: number;
  impact: number;
}

interface RootCauseReport {
  id: string;
  alertId: string;
  possibleCauses: {
    service: string;
    probability: number;
    description: string;
    evidence: string[];
  }[];
  impactAnalysis: {
    affectedServices: string[];
    userImpact: string;
    businessImpact: string;
  };
  relatedMetrics: {
    name: string;
    value: number;
    trend: 'up' | 'down' | 'stable';
  }[];
}

export default function RootCausePage() {
  const [selectedAlert, setSelectedAlert] = useState<string>('ALT-001');
  const [rootCauseReport, setRootCauseReport] = useState<RootCauseReport | null>(null);

  const [alerts] = useState([
    { id: 'ALT-001', title: 'CPU使用率过高', service: 'web-service' },
    { id: 'ALT-002', title: '内存不足', service: 'api-gateway' },
    { id: 'ALT-003', title: '响应时间过长', service: 'database' },
  ]);

  const [rootCauseNodes] = useState<RootCauseNode[]>([
    { id: 'N1', type: 'alert', name: 'CPU告警', status: 'critical', probability: 100 },
    { id: 'N2', type: 'service', name: 'web-service', status: 'warning', probability: 85 },
    { id: 'N3', type: 'metric', name: 'CPU使用率', status: 'critical', probability: 80 },
    { id: 'N4', type: 'service', name: 'api-gateway', status: 'normal', probability: 30 },
    { id: 'N5', type: 'metric', name: '内存使用率', status: 'normal', probability: 20 },
  ]);

  const [rootCausePaths] = useState<RootCausePath[]>([
    {
      nodes: ['CPU告警', 'web-service', 'CPU使用率'],
      probability: 85,
      impact: 75,
    },
    {
      nodes: ['CPU告警', 'api-gateway', '内存使用率'],
      probability: 30,
      impact: 20,
    },
  ]);

  const handleAnalyze = () => {
    setRootCauseReport({
      id: 'RCR-001',
      alertId: selectedAlert,
      possibleCauses: [
        {
          service: 'web-service',
          probability: 85,
          description: 'web-service CPU使用率持续过高',
          evidence: ['CPU使用率 > 90% 持续5分钟', '响应时间增加30%', '错误率上升'],
        },
        {
          service: 'api-gateway',
          probability: 30,
          description: 'api-gateway负载传递导致上游服务压力',
          evidence: ['请求量增加20%', '连接池接近满载'],
        },
      ],
      impactAnalysis: {
        affectedServices: ['web-service', 'api-gateway', 'database'],
        userImpact: '用户请求响应时间增加，部分请求超时',
        businessImpact: '影响在线交易处理，预计损失约$5000/小时',
      },
      relatedMetrics: [
        { name: 'CPU使用率', value: 92, trend: 'up' },
        { name: '内存使用率', value: 78, trend: 'up' },
        { name: '响应时间', value: 450, trend: 'up' },
        { name: '错误率', value: 5.2, trend: 'up' },
      ],
    });
  };

  const getStatusColor = (status: string) => {
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

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      case 'stable':
        return '➡️';
      default:
        return '➡️';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">根因分析</h1>
      </div>

      {/* 告警选择 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">选择告警</label>
              <Select value={selectedAlert} onChange={(e) => setSelectedAlert(e.target.value)}>
                {alerts.map((alert) => (
                  <option key={alert.id} value={alert.id}>
                    {alert.title} ({alert.service})
                  </option>
                ))}
              </Select>
            </div>
            <Button onClick={handleAnalyze}>开始分析</Button>
          </div>
        </CardContent>
      </Card>

      {/* 根因图谱 */}
      <Card>
        <CardHeader>
          <CardTitle>根因图谱</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">根因图谱可视化 (使用D3.js/Cytoscape.js渲染)</p>
          </div>
          <div className="mt-4 flex gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
              <span>告警节点</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span>服务节点</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span>指标节点</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-1 bg-orange-500" />
              <span>根因路径</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 根因路径 */}
      <Card>
        <CardHeader>
          <CardTitle>根因路径</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {rootCausePaths.map((path, index) => (
              <div key={index} className="p-4 border border-orange-200 bg-orange-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">路径 {index + 1}</span>
                    <Badge className="bg-orange-100 text-orange-800">
                      概率: {path.probability}%
                    </Badge>
                    <Badge className="bg-purple-100 text-purple-800">
                      影响度: {path.impact}%
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  {path.nodes.map((node, i) => (
                    <span key={i}>
                      <span className="px-2 py-1 bg-white border border-gray-300 rounded">{node}</span>
                      {i < path.nodes.length - 1 && <span className="text-gray-400 mx-1">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 根因分析报告 */}
      {rootCauseReport && (
        <Card>
          <CardHeader>
            <CardTitle>根因分析报告</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* 可能根因 */}
              <div>
                <h4 className="font-medium mb-3">可能根因 (按概率排序)</h4>
                <div className="space-y-3">
                  {rootCauseReport.possibleCauses.map((cause, index) => (
                    <div key={index} className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{cause.service}</span>
                          <Badge className={cause.probability >= 80 ? 'bg-red-100 text-red-800' : cause.probability >= 50 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}>
                            概率: {cause.probability}%
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{cause.description}</p>
                      <div className="space-y-1">
                        <p className="text-xs text-gray-500">证据:</p>
                        {cause.evidence.map((evidence, i) => (
                          <p key={i} className="text-sm text-gray-700 ml-2">• {evidence}</p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 影响范围分析 */}
              <div>
                <h4 className="font-medium mb-3">影响范围分析</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">受影响服务</p>
                    <div className="flex flex-wrap gap-1">
                      {rootCauseReport.impactAnalysis.affectedServices.map((service) => (
                        <Badge key={service} variant="outline" className="text-xs">
                          {service}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">用户影响</p>
                    <p className="text-sm">{rootCauseReport.impactAnalysis.userImpact}</p>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg md:col-span-2">
                    <p className="text-sm text-gray-500 mb-1">业务影响</p>
                    <p className="text-sm">{rootCauseReport.impactAnalysis.businessImpact}</p>
                  </div>
                </div>
              </div>

              {/* 相关指标趋势 */}
              <div>
                <h4 className="font-medium mb-3">相关指标趋势</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {rootCauseReport.relatedMetrics.map((metric) => (
                    <div key={metric.name} className="p-4 border border-gray-200 rounded-lg">
                      <p className="text-sm text-gray-500 mb-1">{metric.name}</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold">{metric.value}</span>
                        <span className="text-lg">{getTrendIcon(metric.trend)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button>导出报告</Button>
                <Button variant="outline">查看详情</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
