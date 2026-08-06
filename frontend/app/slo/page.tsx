'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Select } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
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
  aggregation?: string;
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

const emptyForm = { name: '', service: '', metric: '', target: 99.9, window: '30d', alert_threshold: 99.0, aggregation: 'good_ratio' };

export default function SLOPage() {
  const [slos, setSlos] = useState<SLO[]>([]);
  const [reports, setReports] = useState<SLAReport[]>([]);
  const [period, setPeriod] = useState('30d');
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [selectedSLO, setSelectedSLO] = useState<SLO | null>(null);

  const loadSlos = async () => {
    try {
      const resp = await api.get<{ slos: SLO[] }>('/api/v1/slo/');
      setSlos(resp.data?.slos || []);
    } catch (err) {
      console.error('加载 SLO 失败', err);
    }
  };

  const loadReports = async (p: string) => {
    try {
      const resp = await api.get<{ reports: SLAReport[] }>(`/api/v1/slo/reports?period=${p}`);
      setReports(resp.data?.reports || []);
    } catch (err) {
      console.error('加载 SLA 报告失败', err);
    }
  };

  useEffect(() => {
    loadSlos();
    loadReports(period);
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setDialogOpen(true);
  };

  const openEdit = (slo: SLO) => {
    setEditingId(slo.id);
    setForm({
      name: slo.name,
      service: slo.service,
      metric: slo.metric,
      target: slo.target,
      window: slo.window,
      alert_threshold: Math.round((slo.target - (slo.target - 99.0)) * 100) / 100,
      aggregation: slo.aggregation || 'good_ratio',
    });
    setDialogOpen(true);
  };

  const saveSLO = async () => {
    const payload = {
      name: form.name,
      service: form.service,
      metric: form.metric,
      target: form.target,
      window: form.window,
      alert_threshold: form.alert_threshold,
      aggregation: form.aggregation,
    };
    try {
      if (editingId) {
        await api.put(`/api/v1/slo/${editingId}`, payload);
      } else {
        await api.post('/api/v1/slo/', payload);
      }
      setDialogOpen(false);
      await loadSlos();
      await loadReports(period);
    } catch (err) {
      console.error('保存 SLO 失败', err);
    }
  };

  const deleteSLO = async (id: string) => {
    if (!window.confirm(`确定删除 SLO ${id} 吗？`)) return;
    try {
      await api.delete(`/api/v1/slo/${id}`);
      if (selectedSLO?.id === id) setSelectedSLO(null);
      await loadSlos();
      await loadReports(period);
    } catch (err) {
      console.error('删除 SLO 失败', err);
    }
  };

  const refreshReports = async () => {
    setLoading(true);
    await loadReports(period);
    setLoading(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getBurnRateColor = (rate: number) => {
    if (rate < 1) return 'text-green-600';
    if (rate < 2) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <main className="p-6 space-y-6 bg-gray-100 min-h-screen">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">SLO/SLA 管理</h1>
        <Button onClick={openCreate}>创建 SLO</Button>
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-3">SLO 概览</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {slos.map((slo) => (
            <Card key={slo.id} className={selectedSLO?.id === slo.id ? 'ring-2 ring-blue-500' : ''}>
              <CardHeader>
                <CardTitle className="text-sm flex items-center justify-between">
                  <span>{slo.name}</span>
                  <Badge className={getStatusColor(slo.status)}>
                    {slo.status === 'healthy' ? '健康' : slo.status === 'warning' ? '警告' : '严重'}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold">{slo.current.toFixed(2)}%</span>
                  <span className="text-sm text-gray-500">/ 目标 {slo.target}%</span>
                </div>
                <Progress value={(slo.current / slo.target) * 100} />
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
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setSelectedSLO(slo)}>详情</Button>
                  <Button variant="outline" size="sm" onClick={() => openEdit(slo)}>编辑</Button>
                  <Button variant="outline" size="sm" onClick={() => deleteSLO(slo.id)}>删除</Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {slos.length === 0 && <p className="text-gray-500">暂无 SLO</p>}
        </div>
      </section>

      {selectedSLO && (
        <Card>
          <CardHeader><CardTitle>{selectedSLO.name} 详情</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-gray-500">服务</span><div>{selectedSLO.service}</div></div>
            <div><span className="text-gray-500">指标</span><div>{selectedSLO.metric}</div></div>
            <div><span className="text-gray-500">窗口</span><div>{selectedSLO.window}</div></div>
            <div><span className="text-gray-500">状态</span><div>{selectedSLO.status}</div></div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>SLO 列表</CardTitle>
            <div className="flex gap-2">
              <Select value={period} onChange={(e) => setPeriod(e.target.value)}>
                <option value="7d">最近 7 天</option>
                <option value="30d">最近 30 天</option>
                <option value="90d">最近 90 天</option>
              </Select>
              <Button variant="outline" size="sm" onClick={refreshReports} disabled={loading}>
                {loading ? '生成中...' : '生成 SLA 报告'}
              </Button>
            </div>
          </div>
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
                <TableHead>聚合</TableHead>
                <TableHead>状态</TableHead>
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
                  <TableCell>{slo.aggregation || 'good_ratio'}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(slo.status)}>
                      {slo.status === 'healthy' ? '健康' : slo.status === 'warning' ? '警告' : '严重'}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>SLA 合规报告</CardTitle></CardHeader>
        <CardContent>
          {reports.length === 0 ? (
            <p className="text-gray-500">暂无报告，请点“生成 SLA 报告”</p>
          ) : (
            <div className="space-y-3">
              {reports.map((r) => (
                <div key={r.id} className="p-4 border rounded-lg flex justify-between items-center">
                  <div>
                    <div className="font-medium">{r.service}</div>
                    <div className="text-sm text-gray-500">周期: {r.period} · 事件数: {r.incidents}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold">{r.availability}% / {r.slaTarget}%</div>
                    <Badge className={r.compliance === 'compliant' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                      {r.compliance === 'compliant' ? '合规' : '不合规'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? '编辑 SLO' : '创建 SLO'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">服务</label>
              <Input value={form.service} onChange={(e) => setForm({ ...form, service: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">指标</label>
              <Input value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })} placeholder="cpu / memory / availability" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">目标 (%)</label>
                <Input type="number" step="0.01" value={form.target} onChange={(e) => setForm({ ...form, target: parseFloat(e.target.value) })} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">窗口</label>
                <Select value={form.window} onChange={(e) => setForm({ ...form, window: e.target.value })}>
                  <option value="1h">1 小时</option>
                  <option value="24h">24 小时</option>
                  <option value="7d">7 天</option>
                  <option value="30d">30 天</option>
                  <option value="90d">90 天</option>
                </Select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">聚合方式</label>
              <Select value={form.aggregation} onChange={(e) => setForm({ ...form, aggregation: e.target.value })}>
                <option value="good_ratio">达标比例</option>
                <option value="uptime">运行时长</option>
                <option value="p99_lt">P99 小于目标</option>
                <option value="mean_lt">均值小于目标</option>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={saveSLO} disabled={!form.name || !form.service || !form.metric}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
