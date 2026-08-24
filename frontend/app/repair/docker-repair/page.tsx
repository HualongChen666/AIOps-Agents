'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface DockerRepair {
  id: string;
  containerId: string;
  containerName: string;
  image: string;
  issueType: 'crash' | 'restart' | 'network' | 'volume' | 'resource';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detected' | 'analyzing' | 'repairing' | 'completed' | 'failed';
  detectedAt: string;
  repairAction: string;
  result?: string;
}

export default function DockerRepairPage() {
  const [repairs, setRepairs] = useState<DockerRepair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterIssueType, setFilterIssueType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadRepairs = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/docker');
      const items = resp.data?.items || [];
      setRepairs(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          containerId: item.container_id || '',
          containerName: item.container_name || '',
          image: item.image || '',
          issueType: (item.issue_type || 'crash') as DockerRepair['issueType'],
          severity: (item.severity || 'low') as DockerRepair['severity'],
          status: (item.status || 'detected') as DockerRepair['status'],
          detectedAt: item.detected_at || item.timestamp || new Date().toISOString(),
          repairAction: item.repair_action || item.action || '',
          result: item.result,
        }))
      );
    } catch (err: any) {
      console.error('加载Docker修复失败:', err);
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
      await api.post(`/api/v1/repair/docker/${repairId}/repair`);
      await loadRepairs();
    } catch (err: any) {
      console.error('执行修复失败:', err);
      setError(err.message || '执行失败');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'detected':
        return 'bg-blue-100 text-blue-800';
      case 'analyzing':
        return 'bg-purple-100 text-purple-800';
      case 'repairing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getIssueTypeLabel = (type: string) => {
    switch (type) {
      case 'crash': return '崩溃';
      case 'restart': return '重启';
      case 'network': return '网络';
      case 'volume': return '卷';
      case 'resource': return '资源';
      default: return type;
    }
  };

  const filteredRepairs = repairs.filter((repair) => {
    const matchesStatus = filterStatus === 'all' || repair.status === filterStatus;
    const matchesIssueType = filterIssueType === 'all' || repair.issueType === filterIssueType;
    const matchesSearch = repair.containerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         repair.containerId.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesIssueType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Docker修复</h1>
        <Button onClick={loadRepairs} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 统计卡片 */}
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

      {/* 筛选和搜索 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap">
            <Input
              placeholder="搜索容器名称或ID..."
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
            <Select value={filterIssueType} onValueChange={setFilterIssueType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="问题类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="crash">崩溃</SelectItem>
                <SelectItem value="restart">重启</SelectItem>
                <SelectItem value="network">网络</SelectItem>
                <SelectItem value="volume">卷</SelectItem>
                <SelectItem value="resource">资源</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 修复列表 */}
      <Card>
        <CardHeader>
          <CardTitle>Docker容器修复任务</CardTitle>
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
                  <TableHead>容器名称</TableHead>
                  <TableHead>容器ID</TableHead>
                  <TableHead>镜像</TableHead>
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
                    <TableCell className="font-medium">{repair.containerName}</TableCell>
                    <TableCell className="font-mono text-sm">{repair.containerId.substring(0, 12)}</TableCell>
                    <TableCell className="max-w-xs truncate">{repair.image}</TableCell>
                    <TableCell>{getIssueTypeLabel(repair.issueType)}</TableCell>
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
                          <Button
                            size="sm"
                            onClick={() => handleRepair(repair.id)}
                          >
                            修复
                          </Button>
                        )}
                        {repair.status === 'completed' && (
                          <Button variant="ghost" size="sm">
                            查看日志
                          </Button>
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
