'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

interface AuditEntry {
  timestamp: string;
  actor: string;
  action: string;
  message: string;
}

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
  audit_log: AuditEntry[];
}

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  pending: '待审批',
  review: '审核中',
  approved: '已批准',
  implemented: '已完成',
  rolled_back: '已回滚',
  rejected: '已拒绝',
};

const RISK_LABEL: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
};

function getStatusColor(status: string) {
  switch (status) {
    case 'draft':
      return 'bg-slate-100 text-slate-800';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800';
    case 'review':
      return 'bg-blue-100 text-blue-800';
    case 'approved':
      return 'bg-green-100 text-green-800';
    case 'implemented':
      return 'bg-gray-100 text-gray-800';
    case 'rolled_back':
      return 'bg-orange-100 text-orange-800';
    case 'rejected':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

function getRiskColor(risk: string) {
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
}

function renderServices(services: string[]) {
  if (!services || services.length === 0) return '—';
  const visible = services.slice(0, 2).join(', ');
  return services.length > 2 ? `${visible} +${services.length - 2}` : visible;
}

export default function ChangeManagementPage() {
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);
  const [selectedRequest, setSelectedRequest] = useState<ChangeRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    title: '',
    description: '',
    requester: '',
    risk_level: 'low' as 'low' | 'medium' | 'high',
    schedule: '',
    affected_services: '',
    implementation_plan: '',
    rollback_plan: '',
  });

  const loadRequests = () => {
    setLoading(true);
    api
      .get('/api/v1/change-management/requests')
      .then((res) => setChangeRequests(res.data as ChangeRequest[]))
      .catch((err) => console.error('加载变更请求失败', err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const openCreateDialog = () => {
    setForm({
      title: '',
      description: '',
      requester: '',
      risk_level: 'low',
      schedule: '',
      affected_services: '',
      implementation_plan: '',
      rollback_plan: '',
    });
    setDialogOpen(true);
  };

  const createRequest = async () => {
    if (!form.title.trim() || !form.requester.trim()) return;
    setCreating(true);
    try {
      const res = await api.post('/api/v1/change-management/requests', {
        title: form.title.trim(),
        description: form.description.trim(),
        requester: form.requester.trim(),
        risk_level: form.risk_level,
        schedule: form.schedule.trim(),
        affected_services: form.affected_services
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        implementation_plan: form.implementation_plan.trim(),
        rollback_plan: form.rollback_plan.trim(),
      });
      setChangeRequests((prev) => [...prev, res.data as ChangeRequest]);
      setDialogOpen(false);
    } catch (err) {
      console.error('创建变更请求失败', err);
    } finally {
      setCreating(false);
    }
  };

  const filteredRequests = changeRequests.filter(
    (cr) => selectedStatus === 'all' || cr.status === selectedStatus
  );

  const pendingCount = changeRequests.filter((cr) =>
    ['pending', 'review'].includes(cr.status)
  ).length;
  const approvedCount = changeRequests.filter((cr) => cr.status === 'approved').length;
  const implementedCount = changeRequests.filter((cr) => cr.status === 'implemented').length;
  const highRiskCount = changeRequests.filter((cr) => cr.risk_level === 'high').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">变更管理</h1>
        <Button onClick={openCreateDialog}>创建变更请求</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">待审批/审核</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{pendingCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已批准</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{approvedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{implementedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高风险</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{highRiskCount}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>变更请求</CardTitle>
            <Select value={selectedStatus} onChange={(e) => setSelectedStatus(e.target.value)}>
              <option value="all">全部状态</option>
              <option value="draft">草稿</option>
              <option value="pending">待审批</option>
              <option value="review">审核中</option>
              <option value="approved">已批准</option>
              <option value="implemented">已完成</option>
              <option value="rolled_back">已回滚</option>
              <option value="rejected">已拒绝</option>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-gray-500">加载中...</p>}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>影响服务</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>风险</TableHead>
                <TableHead>申请人</TableHead>
                <TableHead>计划日期</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRequests.map((cr) => (
                <TableRow key={cr.id}>
                  <TableCell className="font-mono text-sm">{cr.id}</TableCell>
                  <TableCell className="font-medium">{cr.title}</TableCell>
                  <TableCell className="text-sm text-gray-600">{renderServices(cr.affected_services)}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(cr.status)}>
                      {STATUS_LABEL[cr.status] || cr.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getRiskColor(cr.risk_level)}>
                      {RISK_LABEL[cr.risk_level] || cr.risk_level}
                    </Badge>
                  </TableCell>
                  <TableCell>{cr.requester}</TableCell>
                  <TableCell className="text-sm text-gray-500">{cr.schedule || '—'}</TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm" onClick={() => setSelectedRequest(cr)}>
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {selectedRequest && (
        <Card>
          <CardHeader>
            <CardTitle>变更详情 - {selectedRequest.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500">ID</span>
                <p className="font-mono">{selectedRequest.id}</p>
              </div>
              <div>
                <span className="text-gray-500">状态</span>
                <p>
                  <Badge className={getStatusColor(selectedRequest.status)}>
                    {STATUS_LABEL[selectedRequest.status] || selectedRequest.status}
                  </Badge>
                </p>
              </div>
              <div>
                <span className="text-gray-500">风险</span>
                <p>
                  <Badge className={getRiskColor(selectedRequest.risk_level)}>
                    {RISK_LABEL[selectedRequest.risk_level] || selectedRequest.risk_level}
                  </Badge>
                </p>
              </div>
              <div>
                <span className="text-gray-500">计划日期</span>
                <p>{selectedRequest.schedule || '—'}</p>
              </div>
            </div>
            <div className="text-sm space-y-1">
              <p><span className="text-gray-500">申请人:</span> {selectedRequest.requester}</p>
              <p><span className="text-gray-500">审批人:</span> {selectedRequest.approver || '—'}</p>
              <p><span className="text-gray-500">受影响服务:</span> {selectedRequest.affected_services.join(', ') || '—'}</p>
            </div>
            <div className="text-sm">
              <h4 className="font-semibold mb-1">描述</h4>
              <p className="whitespace-pre-wrap">{selectedRequest.description || '无'}</p>
            </div>
            <div className="text-sm">
              <h4 className="font-semibold mb-1">实施方案</h4>
              <p className="whitespace-pre-wrap">{selectedRequest.implementation_plan || '无'}</p>
            </div>
            <div className="text-sm">
              <h4 className="font-semibold mb-1">回滚方案</h4>
              <p className="whitespace-pre-wrap">{selectedRequest.rollback_plan || '无'}</p>
            </div>
            <div className="text-sm">
              <h4 className="font-semibold mb-1">审计日志</h4>
              <ul className="list-disc pl-5 space-y-1">
                {selectedRequest.audit_log.map((entry, idx) => (
                  <li key={idx}>
                    {entry.timestamp} - {entry.actor} [{entry.action}]: {entry.message}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>创建变更请求</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
              <Input
                value={form.title}
                onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                placeholder="变更标题"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">申请人</label>
                <Input
                  value={form.requester}
                  onChange={(e) => setForm((p) => ({ ...p, requester: e.target.value }))}
                  placeholder="申请人"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
                <Select value={form.risk_level} onChange={(e) => setForm((p) => ({ ...p, risk_level: e.target.value as any }))}>
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </Select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">计划日期</label>
              <Input
                value={form.schedule}
                onChange={(e) => setForm((p) => ({ ...p, schedule: e.target.value }))}
                placeholder="例如 2026-07-05 02:00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">受影响服务 (逗号分隔)</label>
              <Input
                value={form.affected_services}
                onChange={(e) => setForm((p) => ({ ...p, affected_services: e.target.value }))}
                placeholder="api-gateway, database"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                placeholder="变更内容说明"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">实施方案</label>
              <Textarea
                value={form.implementation_plan}
                onChange={(e) => setForm((p) => ({ ...p, implementation_plan: e.target.value }))}
                placeholder="具体实施步骤"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">回滚方案</label>
              <Textarea
                value={form.rollback_plan}
                onChange={(e) => setForm((p) => ({ ...p, rollback_plan: e.target.value }))}
                placeholder="异常时的回滚步骤"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={createRequest} disabled={!form.title.trim() || !form.requester.trim() || creating}>
              {creating ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
