'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface K8sRepair {
  id: string;
  namespace: string;
  resourceType: 'deployment' | 'statefulset' | 'daemonset' | 'service' | 'ingress' | 'configmap' | 'secret';
  resourceName: string;
  issueType: 'crash' | 'restart' | 'image' | 'config' | 'resource' | 'network';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detected' | 'analyzing' | 'repairing' | 'completed' | 'failed';
  detectedAt: string;
  repairAction: string;
  result?: string;
}

export default function K8sRepairPage() {
  const [repairs, setRepairs] = useState<K8sRepair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterResourceType, setFilterResourceType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadRepairs = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/k8s');
      const items = resp.data?.items || [];
      setRepairs(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          namespace: item.namespace || 'default',
          resourceType: (item.resource_type || 'deployment') as K8sRepair['resourceType'],
          resourceName: item.resource_name || '',
          issueType: (item.issue_type || 'crash') as K8sRepair['issueType'],
          severity: (item.severity || 'low') as K8sRepair['severity'],
          status: (item.status || 'detected') as K8sRepair['status'],
          detectedAt: item.detected_at || item.timestamp || new Date().toISOString(),
          repairAction: item.repair_action || item.action || '',
          result: item.result,
        }))
      );
    } catch (err: any) {
      console.error('加载Kubernetes修复失败:', err);
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
      await api.post(`/api/v1/repair/k8s/${repairId}/repair`);
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
      case 'image': return '镜像';
      case 'config': return '配置';
      case 'resource': return '资源';
      case 'network': return '网络';
      default: return type;
    }
  };

  const filteredRepairs = repairs.filter((repair) => {
    const matchesStatus = filterStatus === 'all' || repair.status === filterStatus;
    const matchesResourceType = filterResourceType === 'all' || repair.resourceType === filterResourceType;
    const matchesSearch = repair.resourceName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         repair.namespace.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesResourceType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Kubernetes修复</h1>
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
              placeholder="搜索资源名称或命名空间..."
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
            <Select value={filterResourceType} onValueChange={setFilterResourceType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="资源类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="deployment">Deployment</SelectItem>
                <SelectItem value="statefulset">StatefulSet</SelectItem>
                <SelectItem value="daemonset">DaemonSet</SelectItem>
                <SelectItem value="service">Service</SelectItem>
                <SelectItem value="ingress">Ingress</SelectItem>
                <SelectItem value="configmap">ConfigMap</SelectItem>
                <SelectItem value="secret">Secret</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 修复列表 */}
      <Card>
        <CardHeader>
          <CardTitle>Kubernetes资源修复任务</CardTitle>
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
                  <TableHead>命名空间</TableHead>
                  <TableHead>资源类型</TableHead>
                  <TableHead>资源名称</TableHead>
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
                    <TableCell>{repair.namespace}</TableCell>
                    <TableCell>{repair.resourceType}</TableCell>
                    <TableCell className="font-medium">{repair.resourceName}</TableCell>
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
