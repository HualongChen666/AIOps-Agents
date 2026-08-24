'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface ApprovalRequest {
  id: string;
  repairId: string;
  repairType: string;
  targetResource: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requestedBy: string;
  requestedAt: string;
  approver?: string;
  approvedAt?: string;
  rejectionReason?: string;
}

export default function HitlApprovalPage() {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [approvalComment, setApprovalComment] = useState('');

  const loadRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/hitl-approval');
      const items = resp.data?.items || [];
      setRequests(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          repairId: item.repair_id || '',
          repairType: item.repair_type || '',
          targetResource: item.target_resource || '',
          description: item.description || '',
          riskLevel: (item.risk_level || 'low') as ApprovalRequest['riskLevel'],
          status: (item.status || 'pending') as ApprovalRequest['status'],
          requestedBy: item.requested_by || 'System',
          requestedAt: item.requested_at || new Date().toISOString(),
          approver: item.approver,
          approvedAt: item.approved_at,
          rejectionReason: item.rejection_reason,
        }))
      );
    } catch (err: any) {
      console.error('加载人工审批失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const handleApprove = async () => {
    if (!selectedRequest) return;
    try {
      await api.post(`/api/v1/repair/hitl-approval/${selectedRequest.id}/approve`, {
        comment: approvalComment
      });
      setSelectedRequest(null);
      setApprovalComment('');
      await loadRequests();
    } catch (err: any) {
      console.error('批准失败:', err);
      setError(err.message || '批准失败');
    }
  };

  const handleReject = async () => {
    if (!selectedRequest) return;
    try {
      await api.post(`/api/v1/repair/hitl-approval/${selectedRequest.id}/reject`, {
        reason: approvalComment || '人工驳回'
      });
      setSelectedRequest(null);
      setApprovalComment('');
      await loadRequests();
    } catch (err: any) {
      console.error('驳回失败:', err);
      setError(err.message || '驳回失败');
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-blue-100 text-blue-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'expired': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredRequests = requests.filter((request) => {
    return filterStatus === 'all' || request.status === filterStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">人工审批</h1>
        <Button onClick={loadRequests} disabled={loading}>
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
            <CardTitle className="text-sm font-medium text-gray-600">待审批</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{requests.filter(r => r.status === 'pending').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已批准</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{requests.filter(r => r.status === 'approved').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已拒绝</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{requests.filter(r => r.status === 'rejected').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已过期</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{requests.filter(r => r.status === 'expired').length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="状态筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="pending">待审批</SelectItem>
              <SelectItem value="approved">已批准</SelectItem>
              <SelectItem value="rejected">已拒绝</SelectItem>
              <SelectItem value="expired">已过期</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>审批请求</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredRequests.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>修复ID</TableHead>
                  <TableHead>修复类型</TableHead>
                  <TableHead>目标资源</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>请求人</TableHead>
                  <TableHead>请求时间</TableHead>
                  <TableHead>审批人</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRequests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell className="font-mono text-sm">{request.id}</TableCell>
                    <TableCell className="font-mono text-sm">{request.repairId}</TableCell>
                    <TableCell>{request.repairType}</TableCell>
                    <TableCell className="font-medium">{request.targetResource}</TableCell>
                    <TableCell className="max-w-xs truncate">{request.description}</TableCell>
                    <TableCell>
                      <Badge className={getRiskColor(request.riskLevel)}>
                        {request.riskLevel === 'low' ? '低' :
                         request.riskLevel === 'medium' ? '中' :
                         request.riskLevel === 'high' ? '高' : '严重'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(request.status)}>
                        {request.status === 'pending' ? '待审批' :
                         request.status === 'approved' ? '已批准' :
                         request.status === 'rejected' ? '已拒绝' : '已过期'}
                      </Badge>
                    </TableCell>
                    <TableCell>{request.requestedBy}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(request.requestedAt).toLocaleString()}
                    </TableCell>
                    <TableCell>{request.approver || '-'}</TableCell>
                    <TableCell>
                      {request.status === 'pending' && (
                        <Button
                          size="sm"
                          onClick={() => setSelectedRequest(request)}
                        >
                          审批
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selectedRequest && (
        <Dialog open={!!selectedRequest} onOpenChange={() => setSelectedRequest(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>审批修复请求 - {selectedRequest.id}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">修复类型</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRequest.repairType}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">目标资源</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRequest.targetResource}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">描述</label>
                <p className="mt-1 text-sm text-gray-900">{selectedRequest.description}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">风险等级</label>
                <Badge className={getRiskColor(selectedRequest.riskLevel)}>
                  {selectedRequest.riskLevel === 'low' ? '低' :
                   selectedRequest.riskLevel === 'medium' ? '中' :
                   selectedRequest.riskLevel === 'high' ? '高' : '严重'}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">请求人</label>
                <p className="mt-1 text-sm text-gray-900">{selectedRequest.requestedBy}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">审批意见</label>
                <Textarea
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  placeholder="请输入审批意见..."
                  rows={3}
                />
              </div>
              {selectedRequest.riskLevel === 'critical' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800 font-medium">⚠️ 严重风险操作</p>
                  <p className="text-sm text-red-700">此操作可能对系统产生重大影响，请谨慎审批。</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedRequest(null)}>
                取消
              </Button>
              <Button variant="destructive" onClick={handleReject}>
                拒绝
              </Button>
              <Button onClick={handleApprove}>
                批准
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
