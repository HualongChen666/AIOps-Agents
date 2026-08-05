'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface SLO {
  id: string;
  name: string;
  service: string;
  metric: string;
  target: number;
  current: number;
  window: string;
  errorBudget: number;
  burnRate: number;
  status: 'healthy' | 'warning' | 'critical';
}

interface SLAReport {
  id: string;
  period: string;
  service: string;
  availability: number;
  target: number;
  compliance: boolean;
}

export default function SLOPage() {
  const [slos, setSlos] = useState<SLO[]>([]);

  const fetchSlos = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';
      const res = await fetch('/api/v1/slo/', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSlos(data.slos || []);
      } else {
        console.error('Failed to load SLOs', res.status);
      }
    } catch (err) {
      console.error('Error loading SLOs', err);
    }
  };

  useEffect(() => {
    fetchSlos();
  }, []);

  const [slaReports, setSlaReports] = useState<SLAReport[]>([
    {
      id: 'SLA-001',
      period: '2024-05',
      service: 'api-gateway',
      availability: 99.92,
      target: 99.95,
      compliance: false,
    },
    {
      id: 'SLA-002',
      period: '2024-04',
      service: 'api-gateway',
      availability: 99.97,
      target: 99.95,
      compliance: true,
    },
    {
      id: 'SLA-003',
      period: '2024-03',
      service: 'api-gateway',
      availability: 99.94,
      target: 99.95,
      compliance: false,
    },
  ]);

  const [selectedSLO, setSelectedSLO] = useState<SLO | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newSLO, setNewSLO] = useState({
    name: '',
    service: '',
    metric: '',
    target: 99.9,
    window: '30d',
  });

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

  const getBurnRateColor = (burnRate: number) => {
    if (burnRate < 1) return 'text-green-600';
    if (burnRate < 2) return 'text-yellow-600';
    return 'text-red-600';
  };

  const handleCreateSLO = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';
      const res = await fetch('/api/v1/slo/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newSLO.name,
          service: newSLO.service,
          metric: newSLO.metric,
          target: newSLO.target,
          window: newSLO.window,
        }),
      });
      if (res.ok) {
        setShowCreateDialog(false);
        setNewSLO({ name: '', service: '', metric: '', target: 99.9, window: '30d' });
        await fetchSlos();
      } else {
        console.error('Failed to create SLO', res.status);
      }
    } catch (err) {
      console.error('Error creating SLO', err);
    }
  };

  const handleDeleteSLO = async (id: string) => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';
      const res = await fetch(`/api/v1/slo/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await fetchSlos();
      } else {
        console.error('Failed to delete SLO', res.status);
      }
    } catch (err) {
      console.error('Error deleting SLO', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO/SLA管理</h1>
        <div className="flex gap-2">
          <Button variant="outline">SLA报告</Button>
          <Button onClick={() => setShowCreateDialog(true)}>创建SLO</Button>
        </div>
      </div>

      {/* SLO仪表盘 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {slos.map((slo) => (
          <Card key={slo.id}>
            <CardHeader>
              <CardTitle className="text-sm flex items-center justify-between">
                <span>{slo.name}</span>
                <Badge className={getStatusColor(slo.status)}>
                  {slo.status === 'healthy' ? '健康' : slo.status === 'warning' ? '警告' : '严重'}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">{slo.current.toFixed(2)}%</span>
                  <span className="text-sm text-gray-500">/ 目标 {slo.target}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${slo.current >= slo.target ? 'bg-green-500' : 'bg-red-500'}`}
                    style={{ width: `${(slo.current / slo.target) * 100}%` }}
                  />
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">错误预算</span>
                  <span className="font-medium">{slo.errorBudget}% 剩余</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">烧毁率</span>
                  <span className={`font-medium ${getBurnRateColor(slo.burnRate)}`}>
                    {slo.burnRate.toFixed(1)}x
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => setSelectedSLO(slo)}
                >
                  查看详情
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* SLO列表 */}
      <Card>
        <CardHeader>
          <CardTitle>SLO列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>指标</TableHead>
                <TableHead>目标</TableHead>
                <TableHead>当前值</TableHead>
                <TableHead>窗口</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slos.map((slo) => (
                <TableRow key={slo.id}>
                  <TableCell className="font-mono text-sm">{slo.id}</TableCell>
                  <TableCell className="font-medium">{slo.name}</TableCell>
                  <TableCell>{slo.service}</TableCell>
                  <TableCell>{slo.metric}</TableCell>
                  <TableCell>{slo.target}%</TableCell>
                  <TableCell className={slo.current >= slo.target ? 'text-green-600' : 'text-red-600'}>
                    {slo.current.toFixed(2)}%
                  </TableCell>
                  <TableCell>{slo.window}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(slo.status)}>
                      {slo.status === 'healthy' ? '健康' : slo.status === 'warning' ? '警告' : '严重'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => setSelectedSLO(slo)}>
                        编辑
                      </Button>
                      <Button variant="destructive" size="sm" onClick={() => handleDeleteSLO(slo.id)}>
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

      {/* SLA合规报告 */}
      <Card>
        <CardHeader>
          <CardTitle>SLA合规报告</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>报告ID</TableHead>
                <TableHead>周期</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>可用性</TableHead>
                <TableHead>目标</TableHead>
                <TableHead>合规状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slaReports.map((report) => (
                <TableRow key={report.id}>
                  <TableCell className="font-mono text-sm">{report.id}</TableCell>
                  <TableCell>{report.period}</TableCell>
                  <TableCell>{report.service}</TableCell>
                  <TableCell className="font-medium">{report.availability.toFixed(2)}%</TableCell>
                  <TableCell>{report.target}%</TableCell>
                  <TableCell>
                    <Badge className={report.compliance ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                      {report.compliance ? '合规' : '不合规'}
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

      {/* 错误预算策略 */}
      <Card>
        <CardHeader>
          <CardTitle>错误预算策略</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">烧毁率预警阈值</h3>
                <Badge className="bg-blue-100 text-blue-800">已启用</Badge>
              </div>
              <div className="text-sm text-gray-600 mb-3">
                当烧毁率超过阈值时自动触发告警
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">警告阈值</label>
                  <Input defaultValue="1.0" type="number" step="0.1" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">严重阈值</label>
                  <Input defaultValue="2.0" type="number" step="0.1" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">紧急阈值</label>
                  <Input defaultValue="3.0" type="number" step="0.1" />
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <Button>保存策略</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 创建SLO弹窗 */}
      {showCreateDialog && (
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建SLO</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SLO名称</label>
                <Input
                  value={newSLO.name}
                  onChange={(e) => setNewSLO({ ...newSLO, name: e.target.value })}
                  placeholder="例如：API可用性"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
                <Input
                  value={newSLO.service}
                  onChange={(e) => setNewSLO({ ...newSLO, service: e.target.value })}
                  placeholder="例如：api-gateway"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">指标</label>
                <Select
                  value={newSLO.metric}
                  onChange={(e) => setNewSLO({ ...newSLO, metric: e.target.value })}
                >
                  <option value="">选择指标</option>
                  <option value="availability">可用性</option>
                  <option value="latency">响应时间</option>
                  <option value="error_rate">错误率</option>
                  <option value="throughput">吞吐量</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">目标值 (%)</label>
                <Input
                  value={newSLO.target}
                  onChange={(e) => setNewSLO({ ...newSLO, target: Number(e.target.value) })}
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">时间窗口</label>
                <Select
                  value={newSLO.window}
                  onChange={(e) => setNewSLO({ ...newSLO, window: e.target.value })}
                >
                  <option value="1h">1小时</option>
                  <option value="24h">24小时</option>
                  <option value="7d">7天</option>
                  <option value="30d">30天</option>
                  <option value="90d">90天</option>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setShowCreateDialog(false)}>
                取消
              </Button>
              <Button onClick={handleCreateSLO}>创建</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* SLO详情弹窗 */}
      {selectedSLO && (
        <Dialog open={!!selectedSLO} onOpenChange={() => setSelectedSLO(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>SLO详情 - {selectedSLO.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">服务</label>
                <p className="mt-1 text-sm text-gray-900">{selectedSLO.service}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">指标</label>
                <p className="mt-1 text-sm text-gray-900">{selectedSLO.metric}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">目标值</label>
                <p className="mt-1 text-sm text-gray-900">{selectedSLO.target}%</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">当前值</label>
                <p className={`mt-1 text-sm font-medium ${selectedSLO.current >= selectedSLO.target ? 'text-green-600' : 'text-red-600'}`}>
                  {selectedSLO.current.toFixed(2)}%
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">时间窗口</label>
                <p className="mt-1 text-sm text-gray-900">{selectedSLO.window}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">错误预算</label>
                <div className="mt-1">
                  <Progress value={selectedSLO.errorBudget} className="h-2" />
                  <p className="text-sm text-gray-600 mt-1">{selectedSLO.errorBudget}% 剩余</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">烧毁率</label>
                <p className={`mt-1 text-sm font-medium ${getBurnRateColor(selectedSLO.burnRate)}`}>
                  {selectedSLO.burnRate.toFixed(1)}x
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedSLO(null)}>
                关闭
              </Button>
              <Button>编辑SLO</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
