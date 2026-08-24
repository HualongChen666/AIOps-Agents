'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface HardwareRepair {
  id: string;
  hostname: string;
  hardwareType: 'disk' | 'memory' | 'cpu' | 'network' | 'power' | 'cooling';
  deviceId: string;
  issueType: 'failure' | 'degraded' | 'overheating' | 'error' | 'warning';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detected' | 'analyzing' | 'repairing' | 'completed' | 'failed';
  detectedAt: string;
  repairAction: string;
  result?: string;
}

export default function HardwareRepairPage() {
  const [repairs, setRepairs] = useState<HardwareRepair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterHardwareType, setFilterHardwareType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadRepairs = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/hardware');
      const items = resp.data?.items || [];
      setRepairs(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          hostname: item.hostname || '',
          hardwareType: (item.hardware_type || 'disk') as HardwareRepair['hardwareType'],
          deviceId: item.device_id || '',
          issueType: (item.issue_type || 'failure') as HardwareRepair['issueType'],
          severity: (item.severity || 'low') as HardwareRepair['severity'],
          status: (item.status || 'detected') as HardwareRepair['status'],
          detectedAt: item.detected_at || item.timestamp || new Date().toISOString(),
          repairAction: item.repair_action || item.action || '',
          result: item.result,
        }))
      );
    } catch (err: any) {
      console.error('加载硬件修复失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepairs();
  }, []);

  const handleRepair = async (repairId: string) => {
    try {
      await api.post(`/api/v1/repair/hardware/${repairId}/repair`);
      await loadRepairs();
    } catch (err: any) {
      console.error('执行修复失败:', err);
      setError(err.message || '执行失败');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'detected': return 'bg-blue-100 text-blue-800';
      case 'analyzing': return 'bg-purple-100 text-purple-800';
      case 'repairing': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getHardwareTypeLabel = (type: string) => {
    switch (type) {
      case 'disk': return '磁盘';
      case 'memory': return '内存';
      case 'cpu': return 'CPU';
      case 'network': return '网络';
      case 'power': return '电源';
      case 'cooling': return '散热';
      default: return type;
    }
  };

  const filteredRepairs = repairs.filter((repair) => {
    const matchesStatus = filterStatus === 'all' || repair.status === filterStatus;
    const matchesHardwareType = filterHardwareType === 'all' || repair.hardwareType === filterHardwareType;
    const matchesSearch = repair.hostname.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         repair.deviceId.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesHardwareType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">硬件修复</h1>
        <Button onClick={loadRepairs} disabled={loading}>
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
            <CardTitle className="text-sm font-medium text-gray-600">已检测</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'detected').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">修复中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'repairing').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'completed').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'failed').length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap">
            <Input
              placeholder="搜索主机名或设备ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-md"
            />
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="状态筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="detected">已检测</SelectItem>
                <SelectItem value="analyzing">分析中</SelectItem>
                <SelectItem value="repairing">修复中</SelectItem>
                <SelectItem value="completed">已完成</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterHardwareType} onValueChange={setFilterHardwareType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="硬件类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="disk">磁盘</SelectItem>
                <SelectItem value="memory">内存</SelectItem>
                <SelectItem value="cpu">CPU</SelectItem>
                <SelectItem value="network">网络</SelectItem>
                <SelectItem value="power">电源</SelectItem>
                <SelectItem value="cooling">散热</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>硬件修复任务</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredRepairs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>主机名</TableHead>
                  <TableHead>硬件类型</TableHead>
                  <TableHead>设备ID</TableHead>
                  <TableHead>问题类型</TableHead>
                  <TableHead>严重程度</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>修复动作</TableHead>
                  <TableHead>检测时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRepairs.map((repair) => (
                  <TableRow key={repair.id}>
                    <TableCell className="font-mono text-sm">{repair.id}</TableCell>
                    <TableCell className="font-medium">{repair.hostname}</TableCell>
                    <TableCell>{getHardwareTypeLabel(repair.hardwareType)}</TableCell>
                    <TableCell className="font-mono text-sm">{repair.deviceId}</TableCell>
                    <TableCell>{repair.issueType}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(repair.severity)}>
                        {repair.severity === 'low' ? '低' :
                         repair.severity === 'medium' ? '中' :
                         repair.severity === 'high' ? '高' : '严重'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(repair.status)}>
                        {repair.status === 'detected' ? '已检测' :
                         repair.status === 'analyzing' ? '分析中' :
                         repair.status === 'repairing' ? '修复中' :
                         repair.status === 'completed' ? '已完成' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate">{repair.repairAction}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(repair.detectedAt).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {repair.status === 'detected' && (
                          <Button size="sm" onClick={() => handleRepair(repair.id)}>修复</Button>
                        )}
                        {repair.status === 'completed' && (
                          <Button variant="ghost" size="sm">查看日志</Button>
                        )}
                      </div>
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
