'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface ChangeRequest {
  id: string;
  title: string;
  description: string;
  requester: string;
  approver: string;
  status: string;
  risk_level: 'low' | 'medium' | 'high';
  schedule: string;
  affected_services: string[];
  implementation_plan: string;
  rollback_plan: string;
}

interface ChangeRequestForm {
  title: string;
  description: string;
  requester: string;
  approver: string;
  risk_level: string;
  schedule: string;
  affected_services: string;
  implementation_plan: string;
  rollback_plan: string;
}

const emptyForm: ChangeRequestForm = {
  title: '',
  description: '',
  requester: '',
  approver: '',
  risk_level: 'low',
  schedule: '',
  affected_services: '',
  implementation_plan: '',
  rollback_plan: '',
};

export default function BuilderPage() {
  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newRequest, setNewRequest] = useState<ChangeRequestForm>(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const res = await api.get<ChangeRequest[]>('/api/v1/change-management/requests');
      setRequests(res.data || []);
    } catch {
      // api interceptor shows toast
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
      case 'implemented':
        return 'bg-green-100 text-green-800';
      case 'pending':
      case 'review':
        return 'bg-yellow-100 text-yellow-800';
      case 'rejected':
      case 'rolled_back':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreate = async () => {
    setSubmitting(true);
    try {
      const payload = {
        ...newRequest,
        affected_services: newRequest.affected_services
          .split(/[,，]/)
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await api.post('/api/v1/change-management/requests', payload);
      await fetchRequests();
      setShowCreateDialog(false);
      setNewRequest(emptyForm);
    } finally {
      setSubmitting(false);
    }
  };

  const canCreate = newRequest.title.trim() && newRequest.requester.trim();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">变更请求管理</h1>
        <Button onClick={() => setShowCreateDialog(true)}>新建变更请求</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>变更请求列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>申请人</TableHead>
                <TableHead>风险等级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>计划时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-gray-500">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : requests.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-gray-500">
                    暂无变更请求
                  </TableCell>
                </TableRow>
              ) : (
                requests.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell className="font-mono text-sm">{req.id}</TableCell>
                    <TableCell className="font-medium">{req.title}</TableCell>
                    <TableCell>{req.requester}</TableCell>
                    <TableCell>
                      <Badge className={getRiskColor(req.risk_level)}>
                        {req.risk_level === 'high' ? '高' : req.risk_level === 'medium' ? '中' : '低'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(req.status)}>{req.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{req.schedule || '-'}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm">
                        详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {showCreateDialog && (
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>新建变更请求</DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                <Input
                  value={newRequest.title}
                  onChange={(e) => setNewRequest({ ...newRequest, title: e.target.value })}
                  placeholder="输入变更标题"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">申请人</label>
                <Input
                  value={newRequest.requester}
                  onChange={(e) => setNewRequest({ ...newRequest, requester: e.target.value })}
                  placeholder="申请人姓名"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">审批人</label>
                <Input
                  value={newRequest.approver}
                  onChange={(e) => setNewRequest({ ...newRequest, approver: e.target.value })}
                  placeholder="审批人姓名"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
                <Select
                  value={newRequest.risk_level}
                  onChange={(e) => setNewRequest({ ...newRequest, risk_level: e.target.value })}
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">计划执行时间</label>
                <Input
                  value={newRequest.schedule}
                  onChange={(e) => setNewRequest({ ...newRequest, schedule: e.target.value })}
                  placeholder="例如：2024-12-31 02:00"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">受影响服务</label>
                <Input
                  value={newRequest.affected_services}
                  onChange={(e) => setNewRequest({ ...newRequest, affected_services: e.target.value })}
                  placeholder="多个服务请用逗号分隔"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <Textarea
                  value={newRequest.description}
                  onChange={(e) => setNewRequest({ ...newRequest, description: e.target.value })}
                  placeholder="变更背景和目的"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">实施方案</label>
                <Textarea
                  value={newRequest.implementation_plan}
                  onChange={(e) => setNewRequest({ ...newRequest, implementation_plan: e.target.value })}
                  placeholder="变更实施步骤"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">回滚方案</label>
                <Textarea
                  value={newRequest.rollback_plan}
                  onChange={(e) => setNewRequest({ ...newRequest, rollback_plan: e.target.value })}
                  placeholder="变更回滚步骤"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setShowCreateDialog(false)}>
                取消
              </Button>
              <Button onClick={handleCreate} disabled={!canCreate || submitting}>
                创建
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
