'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface SLO {
  id: string;
  name: string;
  service: string;
  target: number;
  current: number;
  errorBudget: number;
  period: string;
  status: 'healthy' | 'warning' | 'critical';
}

interface SLAReport {
  id: string;
  service: string;
  period: string;
  availability: number;
  slaTarget: number;
  compliance: 'compliant' | 'non-compliant';
  incidents: number;
}

export default function SLOSLAPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('7d');
  const [selectedSLO, setSelectedSLO] = useState<SLO | null>(null);

  const [slos, setSlos] = useState<SLO[]>([]);
  const [slaReports] = useState<SLAReport[]>([]);

  useEffect(() => {
    const loadSlos = async () => {
      try {
        const { data } = await api.get('/api/v1/slo/');
        setSlos(
          (data.slos || []).map((item: any) => ({
            id: item.id,
            name: item.name,
            service: item.service,
            target: item.target,
            current: item.current,
            errorBudget: item.errorBudget,
            period: item.window,
            status: item.status,
          }))
        );
      } catch (err) {
        console.error('Failed to load SLOs', err);
      }
    };
    loadSlos();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getComplianceColor = (compliance: string) => {
    switch (compliance) {
      case 'compliant':
        return 'bg-green-100 text-green-800';
      case 'non-compliant':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO/SLA管理</h1>
        <Button>创建SLO</Button>
      </div>

      {/* SLO概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {slos.map((slo) => (
          <Card
            key={slo.id}
            className={`cursor-pointer transition hover:shadow-md ${selectedSLO?.id === slo.id ? 'border-blue-500 ring-2 ring-blue-200' : ''
              }`}
            onClick={() => setSelectedSLO(slo)}
          >
            <CardHeader>
              <div className="flex items-center justify-between mb-2">
                <CardTitle className="text-lg">{slo.name}</CardTitle>
                <Badge className={getStatusColor(slo.status)}>
                  {slo.status === 'healthy' ? '健康' : slo.status === 'warning' ? '警告' : '严重'}
                </Badge>
              </div>
              <p className="text-sm text-gray-500">{slo.service}</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>当前值</span>
                    <span className="font-medium">{slo.current}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${slo.status === 'healthy' ? 'bg-green-500' : slo.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                      style={{ width: `${slo.current}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>目标: {slo.target}%</span>
                  </div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">错误预算</span>
                  <span className="font-medium">{slo.errorBudget}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* SLO详情 */}
      {selectedSLO && (
        <Card>
          <CardHeader>
            <CardTitle>{selectedSLO.name} - 详细信息</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium mb-3">错误预算烧毁率</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>最近7天</span>
                    <span className="text-red-600">-12%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>最近30天</span>
                    <span className="text-yellow-600">-5%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>预测(7天)</span>
                    <span className="text-green-600">-3%</span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-3">历史趋势</h4>
                <div className="h-32 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-400 text-sm">历史趋势图表</p>
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-4 pt-4 border-t">
              <Button variant="outline" size="sm">
                编辑SLO
              </Button>
              <Button variant="outline" size="sm">
                错误预算策略
              </Button>
              <Button variant="outline" size="sm">
                导出报告
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* SLA合规报告 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>SLA合规报告</CardTitle>
            <div className="flex gap-2">
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="border border-gray-300 rounded px-3 py-1 text-sm"
              >
                <option value="7d">最近7天</option>
                <option value="30d">最近30天</option>
                <option value="90d">最近90天</option>
              </select>
              <Button variant="outline" size="sm">
                生成报告
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {slaReports.map((report) => (
              <div key={report.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="font-medium">{report.service}</h4>
                    <p className="text-sm text-gray-500">周期: {report.period}</p>
                  </div>
                  <Badge className={getComplianceColor(report.compliance)}>
                    {report.compliance === 'compliant' ? '合规' : '不合规'}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">可用性</p>
                    <p className="font-medium">{report.availability}%</p>
                  </div>
                  <div>
                    <p className="text-gray-500">SLA目标</p>
                    <p className="font-medium">{report.slaTarget}%</p>
                  </div>
                  <div>
                    <p className="text-gray-500">事件数</p>
                    <p className="font-medium">{report.incidents}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 烧毁率预警 */}
      <Card>
        <CardHeader>
          <CardTitle>烧毁率预警</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-red-800">Database错误率 - 高风险</h4>
                <Badge className="bg-red-100 text-red-800">紧急</Badge>
              </div>
              <p className="text-sm text-red-700 mb-2">
                当前烧毁率: 15%/天，预计5天内耗尽错误预算
              </p>
              <Button variant="outline" size="sm" className="text-red-600 border-red-300">
                查看详情
              </Button>
            </div>
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-yellow-800">Web Service响应时间 - 中风险</h4>
                <Badge className="bg-yellow-100 text-yellow-800">警告</Badge>
              </div>
              <p className="text-sm text-yellow-700 mb-2">
                当前烧毁率: 5%/天，预计15天内耗尽错误预算
              </p>
              <Button variant="outline" size="sm" className="text-yellow-600 border-yellow-300">
                查看详情
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
