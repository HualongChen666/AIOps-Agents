'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ApprovalRequest {
  id: string;
  changeId: string;
  changeTitle: string;
  changeDescription: string;
  requester: string;
  type: 'routine' | 'emergency' | 'standard';
  priority: 'low' | 'medium' | 'high' | 'critical';
  riskLevel: 'low' | 'medium' | 'high';
  scheduledStart?: string;
  scheduledEnd?: string;
  status: 'pending' | 'approved' | 'rejected';
  approver?: string;
  comment?: string;
  approvedAt?: string;
  createdAt: string;
}

export default function ChangeApprovalPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [action, setAction] = useState<'approve' | 'reject'>('approve');
  const [comment, setComment] = useState('');

  const loadApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<ApprovalRequest[]>('/api/v1/change-approval');
      setApprovals(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载审批请求失败');
      console.error('加载审批请求失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleView = (approval: ApprovalRequest) => {
    setSelectedApproval(approval);
  };

  const handleApprove = (approval: ApprovalRequest) => {
    setSelectedApproval(approval);
    setAction('approve');
    setComment('');
    setDialogOpen(true);
  };

  const handleReject = (approval: ApprovalRequest) => {
    setSelectedApproval(approval);
    setAction('reject');
    setComment('');
    setDialogOpen(true);
  };

  const handleSubmitDecision = async () => {
    if (!selectedApproval) return;
    try {
      await api.post(`/api/v1/change-approval/${selectedApproval.id}/${action}`, { comment });
      setDialogOpen(false);
      setSelectedApproval(null);
      await loadApprovals();
    } catch (err: any) {
      setError(err.response?.data?.message || '提交决策失败');
      console.error('提交决策失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: 'outline',
      approved: 'default',
      rejected: 'destructive',
    };
    const labels: Record<string, string> = {
      pending: '待审批',
      approved: '已批准',
      rejected: '已拒绝',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const getTypeBadge = (type: string) => {
    const variants: Record<string, any> = {
      routine: 'secondary',
      emergency: 'destructive',
      standard: 'default',
    };
    const labels: Record<string, string> = {
      routine: '常规',
      emergency: '紧急',
      standard: '标准',
    };
    return <Badge variant={variants[type] || 'outline'}>{labels[type] || type}</Badge>;
  };

  const getPriorityBadge = (priority: string) => {
    const variants: Record<string, any> = {
      low: 'secondary',
      medium: 'outline',
      high: 'default',
      critical: 'destructive',
    };
    const labels: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
      critical: '紧急',
    };
    return <Badge variant={variants[priority] || 'outline'}>{labels[priority] || priority}</Badge>;
  };

  const pendingApprovals = approvals.filter(a => a.status === 'pending');
  const processedApprovals = approvals.filter(a => a.status !== 'pending');

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">变更审批</h1>
        <p className="text-gray-600 mt-1">审批和管理变更请求</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">待审批</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{pendingApprovals.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已批准</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">
              {approvals.filter(a => a.status === 'approved').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已拒绝</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">
              {approvals.filter(a => a.status === 'rejected').length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>待审批请求</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : pendingApprovals.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无待审批请求</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>变更标题</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>请求人</TableHead>
                  <TableHead>计划时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingApprovals.map((approval) => (
                  <TableRow key={approval.id}>
                    <TableCell className="font-mono text-sm">{approval.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{approval.changeTitle}</TableCell>
                    <TableCell>{getTypeBadge(approval.type)}</TableCell>
                    <TableCell>{getPriorityBadge(approval.priority)}</TableCell>
                    <TableCell>
                      <Badge variant={approval.riskLevel === 'high' ? 'destructive' : 'outline'}>
                        {approval.riskLevel === 'low' ? '低' : approval.riskLevel === 'medium' ? '中' : '高'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-600">{approval.requester}</TableCell>
                    <TableCell className="text-gray-600">
                      {approval.scheduledStart ? new Date(approval.scheduledStart).toLocaleString('zh-CN') : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleView(approval)}
                        >
                          查看
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleApprove(approval)}
                        >
                          批准
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleReject(approval)}
                        >
                          拒绝
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>已处理请求</CardTitle>
        </CardHeader>
        <CardContent>
          {processedApprovals.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无已处理请求</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>变更标题</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>审批人</TableHead>
                  <TableHead>审批时间</TableHead>
                  <TableHead>评论</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {processedApprovals.map((approval) => (
                  <TableRow key={approval.id}>
                    <TableCell className="font-mono text-sm">{approval.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{approval.changeTitle}</TableCell>
                    <TableCell>{getStatusBadge(approval.status)}</TableCell>
                    <TableCell className="text-gray-600">{approval.approver || '-'}</TableCell>
                    <TableCell className="text-gray-600">
                      {approval.approvedAt ? new Date(approval.approvedAt).toLocaleString('zh-CN') : '-'}
                    </TableCell>
                    <TableCell className="text-gray-600 max-w-xs truncate">
                      {approval.comment || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {action === 'approve' ? '批准变更' : '拒绝变更'}
            </DialogTitle>
          </DialogHeader>
          {selectedApproval && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">变更标题</h3>
                <p className="font-medium">{selectedApproval.changeTitle}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">变更描述</h3>
                <p className="text-gray-600">{selectedApproval.changeDescription}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">类型</h3>
                  {getTypeBadge(selectedApproval.type)}
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">优先级</h3>
                  {getPriorityBadge(selectedApproval.priority)}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">风险等级</h3>
                <Badge variant={selectedApproval.riskLevel === 'high' ? 'destructive' : 'outline'}>
                  {selectedApproval.riskLevel === 'low' ? '低' : selectedApproval.riskLevel === 'medium' ? '中' : '高'}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">审批意见</label>
                <Textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="输入审批意见"
                  rows={3}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmitDecision}
              variant={action === 'approve' ? 'default' : 'destructive'}
            >
              {action === 'approve' ? '批准' : '拒绝'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
