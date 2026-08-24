'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface RepairVerification {
  id: string;
  repairId: string;
  repairType: string;
  targetResource: string;
  verificationType: 'health-check' | 'functional' | 'performance' | 'security';
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped';
  startTime: string;
  endTime?: string;
  duration?: number;
  checksPassed: number;
  checksTotal: number;
  details?: string;
}

export default function RepairVerificationPage() {
  const [verifications, setVerifications] = useState<RepairVerification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterVerificationType, setFilterVerificationType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadVerifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/verification');
      const items = resp.data?.items || [];
      setVerifications(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          repairId: item.repair_id || '',
          repairType: item.repair_type || '',
          targetResource: item.target_resource || '',
          verificationType: (item.verification_type || 'health-check') as RepairVerification['verificationType'],
          status: (item.status || 'pending') as RepairVerification['status'],
          startTime: item.start_time || new Date().toISOString(),
          endTime: item.end_time,
          duration: item.duration,
          checksPassed: item.checks_passed || 0,
          checksTotal: item.checks_total || 0,
          details: item.details,
        }))
      );
    } catch (err: any) {
      console.error('加载修复验证失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVerifications();
  }, []);

  const handleVerify = async (verificationId: string) => {
    try {
      await api.post(`/api/v1/repair/verification/${verificationId}/verify`);
      await loadVerifications();
    } catch (err: any) {
      console.error('执行验证失败:', err);
      setError(err.message || '执行失败');
    }
  };

  const handleRerun = async (verificationId: string) => {
    try {
      await api.post(`/api/v1/repair/verification/${verificationId}/rerun`);
      await loadVerifications();
    } catch (err: any) {
      console.error('重新运行失败:', err);
      setError(err.message || '重新运行失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-gray-100 text-gray-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'passed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'skipped': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getVerificationTypeLabel = (type: string) => {
    switch (type) {
      case 'health-check': return '健康检查';
      case 'functional': return '功能测试';
      case 'performance': return '性能测试';
      case 'security': return '安全检查';
      default: return type;
    }
  };

  const filteredVerifications = verifications.filter((verification) => {
    const matchesStatus = filterStatus === 'all' || verification.status === filterStatus;
    const matchesType = filterVerificationType === 'all' || verification.verificationType === filterVerificationType;
    const matchesSearch = verification.targetResource.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         verification.repairId.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">修复验证</h1>
        <Button onClick={loadVerifications} disabled={loading}>
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
            <CardTitle className="text-sm font-medium text-gray-600">待验证</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{verifications.filter(v => v.status === 'pending').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">验证中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{verifications.filter(v => v.status === 'running').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">通过</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{verifications.filter(v => v.status === 'passed').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{verifications.filter(v => v.status === 'failed').length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap">
            <Input
              placeholder="搜索修复ID或目标资源..."
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
                <SelectItem value="pending">待验证</SelectItem>
                <SelectItem value="running">验证中</SelectItem>
                <SelectItem value="passed">通过</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
                <SelectItem value="skipped">跳过</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterVerificationType} onValueChange={setFilterVerificationType}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="验证类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="health-check">健康检查</SelectItem>
                <SelectItem value="functional">功能测试</SelectItem>
                <SelectItem value="performance">性能测试</SelectItem>
                <SelectItem value="security">安全检查</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>修复验证任务</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredVerifications.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>修复ID</TableHead>
                  <TableHead>修复类型</TableHead>
                  <TableHead>目标资源</TableHead>
                  <TableHead>验证类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>检查进度</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>持续时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredVerifications.map((verification) => (
                  <TableRow key={verification.id}>
                    <TableCell className="font-mono text-sm">{verification.id}</TableCell>
                    <TableCell className="font-mono text-sm">{verification.repairId}</TableCell>
                    <TableCell>{verification.repairType}</TableCell>
                    <TableCell className="font-medium">{verification.targetResource}</TableCell>
                    <TableCell>{getVerificationTypeLabel(verification.verificationType)}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(verification.status)}>
                        {verification.status === 'pending' ? '待验证' :
                         verification.status === 'running' ? '验证中' :
                         verification.status === 'passed' ? '通过' :
                         verification.status === 'failed' ? '失败' : '跳过'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${(verification.checksPassed / verification.checksTotal) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm">{verification.checksPassed}/{verification.checksTotal}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(verification.startTime).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {verification.duration ? `${verification.duration}s` : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {verification.status === 'pending' && (
                          <Button size="sm" onClick={() => handleVerify(verification.id)}>验证</Button>
                        )}
                        {verification.status === 'failed' && (
                          <Button size="sm" onClick={() => handleRerun(verification.id)}>重试</Button>
                        )}
                        {verification.status === 'passed' && (
                          <Button variant="ghost" size="sm">查看详情</Button>
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
