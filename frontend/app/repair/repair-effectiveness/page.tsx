'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface RepairEffectiveness {
  id: string;
  repairId: string;
  repairType: string;
  targetResource: string;
  successRate: number;
  avgRepairTime: number;
  totalRepairs: number;
  successfulRepairs: number;
  failedRepairs: number;
  lastEvaluated: string;
  trend: 'improving' | 'stable' | 'declining';
}

export default function RepairEffectivenessPage() {
  const [effectiveness, setEffectiveness] = useState<RepairEffectiveness[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterTrend, setFilterTrend] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadEffectiveness = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/effectiveness');
      const items = resp.data?.items || [];
      setEffectiveness(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          repairId: item.repair_id || '',
          repairType: item.repair_type || '',
          targetResource: item.target_resource || '',
          successRate: item.success_rate || 0,
          avgRepairTime: item.avg_repair_time || 0,
          totalRepairs: item.total_repairs || 0,
          successfulRepairs: item.successful_repairs || 0,
          failedRepairs: item.failed_repairs || 0,
          lastEvaluated: item.last_evaluated || new Date().toISOString(),
          trend: (item.trend || 'stable') as RepairEffectiveness['trend'],
        }))
      );
    } catch (err: any) {
      console.error('加载修复效果评估失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEffectiveness();
  }, []);

  const handleEvaluate = async (effectivenessId: string) => {
    try {
      await api.post(`/api/v1/repair/effectiveness/${effectivenessId}/evaluate`);
      await loadEffectiveness();
    } catch (err: any) {
      console.error('执行评估失败:', err);
      setError(err.message || '执行失败');
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return 'bg-green-100 text-green-800';
      case 'stable': return 'bg-blue-100 text-blue-800';
      case 'declining': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getSuccessRateColor = (rate: number) => {
    if (rate >= 90) return 'text-green-600';
    if (rate >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const filteredEffectiveness = effectiveness.filter((item) => {
    const matchesTrend = filterTrend === 'all' || item.trend === filterTrend;
    const matchesSearch = item.repairType.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.targetResource.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesTrend && matchesSearch;
  });

  const overallSuccessRate = effectiveness.length > 0
    ? (effectiveness.reduce((sum, item) => sum + item.successRate, 0) / effectiveness.length).toFixed(1)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">修复效果评估</h1>
        <Button onClick={loadEffectiveness} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getSuccessRateColor(parseFloat(overallSuccessRate))}`}>
              {overallSuccessRate}%
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总修复次数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {effectiveness.reduce((sum, item) => sum + item.totalRepairs, 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">平均修复时间</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {effectiveness.length > 0
                ? (effectiveness.reduce((sum, item) => sum + item.avgRepairTime, 0) / effectiveness.length).toFixed(1)
                : 0}s
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">趋势改善</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {effectiveness.filter(e => e.trend === 'improving').length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap">
            <Input
              placeholder="搜索修复类型或目标资源..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-md"
            />
            <Select value={filterTrend} onValueChange={setFilterTrend}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="趋势筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部趋势</SelectItem>
                <SelectItem value="improving">改善</SelectItem>
                <SelectItem value="stable">稳定</SelectItem>
                <SelectItem value="declining">下降</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>修复效果评估</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredEffectiveness.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>修复ID</TableHead>
                  <TableHead>修复类型</TableHead>
                  <TableHead>目标资源</TableHead>
                  <TableHead>成功率</TableHead>
                  <TableHead>平均修复时间</TableHead>
                  <TableHead>总修复次数</TableHead>
                  <TableHead>成功/失败</TableHead>
                  <TableHead>趋势</TableHead>
                  <TableHead>最后评估</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEffectiveness.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-sm">{item.id}</TableCell>
                    <TableCell className="font-mono text-sm">{item.repairId}</TableCell>
                    <TableCell className="font-medium">{item.repairType}</TableCell>
                    <TableCell>{item.targetResource}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${item.successRate}%` }}
                          />
                        </div>
                        <span className={`text-sm font-medium ${getSuccessRateColor(item.successRate)}`}>
                          {item.successRate.toFixed(1)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {item.avgRepairTime.toFixed(1)}s
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">{item.totalRepairs}</TableCell>
                    <TableCell>
                      <span className="text-green-600">{item.successfulRepairs}</span>
                      <span className="text-gray-400">/</span>
                      <span className="text-red-600">{item.failedRepairs}</span>
                    </TableCell>
                    <TableCell>
                      <Badge className={getTrendColor(item.trend)}>
                        {item.trend === 'improving' ? '改善' :
                         item.trend === 'stable' ? '稳定' : '下降'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(item.lastEvaluated).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button size="sm" onClick={() => handleEvaluate(item.id)}>
                        重新评估
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
