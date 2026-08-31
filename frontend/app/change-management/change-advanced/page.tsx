'use client'

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { 
  TrendingUp, 
  BarChart3, 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Filter,
  Search,
  Calendar,
  User,
  FileText,
  Activity,
  Shield
} from 'lucide-react';

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
  tenant_id: string;
}

interface ChangeStatistics {
  total: number;
  by_status: Record<string, number>;
  by_risk: Record<string, number>;
  by_service: Record<string, number>;
  success_rate: number;
  avg_duration: number;
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

export default function ChangeAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'analytics' | 'templates'>('overview');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedRisk, setSelectedRisk] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [selectedRequest, setSelectedRequest] = useState<ChangeRequest | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // 🔧 使用防抖搜索
  const debouncedSearch = useDebounce(searchQuery, 300);

  // 🔧 获取变更请求列表
  const { data: changeRequests = [], isLoading, error, refetch } = useQuery<ChangeRequest[]>({
    queryKey: ['change-requests-advanced', selectedStatus, selectedRisk, debouncedSearch],
    queryFn: async () => {
      const resp = await api.get('/api/v1/change-management/requests');
      return resp.data as ChangeRequest[];
    },
    refetchInterval: 30000,
  });

  // 🔧 P1 Integration: 使用增强的加载状态
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(isLoading);

  // 🔧 P1 Integration: 使用 toast 通知
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 处理错误
  useEffect(() => {
    if (error) {
      showError('加载变更请求失败');
      setPageError(error as Error);
    }
  }, [error, showError, setPageError]);

  // 🔧 计算统计数据
  const statistics: ChangeStatistics = {
    total: changeRequests.length,
    by_status: changeRequests.reduce((acc, cr) => {
      acc[cr.status] = (acc[cr.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
    by_risk: changeRequests.reduce((acc, cr) => {
      acc[cr.risk_level] = (acc[cr.risk_level] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
    by_service: changeRequests.reduce((acc, cr) => {
      cr.affected_services.forEach(service => {
        acc[service] = (acc[service] || 0) + 1;
      });
      return acc;
    }, {} as Record<string, number>),
    success_rate: changeRequests.length > 0 
      ? (changeRequests.filter(cr => cr.status === 'implemented').length / changeRequests.length) * 100 
      : 0,
    avg_duration: 0, // 需要从审计日志计算
  };

  // 🔧 过滤变更请求
  const filteredRequests = changeRequests.filter((cr) => {
    if (selectedStatus !== 'all' && cr.status !== selectedStatus) return false;
    if (selectedRisk !== 'all' && cr.risk_level !== selectedRisk) return false;
    if (debouncedSearch && !cr.title.toLowerCase().includes(debouncedSearch.toLowerCase()) && 
        !cr.id.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    if (dateRange.start && cr.schedule < dateRange.start) return false;
    if (dateRange.end && cr.schedule > dateRange.end) return false;
    return true;
  });

  // 🔧 P1 Integration: 加载状态
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // 🔧 P1 Integration: 错误状态
  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载变更请求数据，请稍后重试"
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const tabs = [
    { key: 'overview' as const, label: '概览', icon: BarChart3 },
    { key: 'history' as const, label: '历史记录', icon: Clock },
    { key: 'analytics' as const, label: '统计分析', icon: TrendingUp },
    { key: 'templates' as const, label: '变更模板', icon: FileText },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-[var(--accent-blue)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">高级变更管理</h1>
            <p className="text-sm text-gray-500">变更请求的高级分析和历史记录</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} variant="outline">
            刷新
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
                  activeTab === tab.key
                    ? 'bg-[var(--accent-blue)] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {activeTab === 'overview' && (
        <>
          {/* 统计卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  总变更数
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-[var(--accent-blue)]">{statistics.total}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  成功率
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-green-600">{statistics.success_rate.toFixed(1)}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  高风险变更
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-red-600">{statistics.by_risk.high || 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  待审批
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-yellow-600">
                  {(statistics.by_status.pending || 0) + (statistics.by_status.review || 0)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 状态分布 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">状态分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(statistics.by_status).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between">
                      <Badge className={getStatusColor(status)}>
                        {STATUS_LABEL[status] || status}
                      </Badge>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">风险分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(statistics.by_risk).map(([risk, count]) => (
                    <div key={risk} className="flex items-center justify-between">
                      <Badge className={getRiskColor(risk)}>
                        {RISK_LABEL[risk] || risk}
                      </Badge>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {activeTab === 'history' && (
        <>
          {/* 筛选器 */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                  >
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
                  <Select
                    value={selectedRisk}
                    onChange={(e) => setSelectedRisk(e.target.value)}
                  >
                    <option value="all">全部风险</option>
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="搜索标题或ID"
                      className="pl-10"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">日期范围</label>
                  <div className="flex gap-2">
                    <Input
                      type="date"
                      value={dateRange.start}
                      onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                    />
                    <Input
                      type="date"
                      value={dateRange.end}
                      onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 历史记录列表 */}
          <Card>
            <CardHeader>
              <CardTitle>变更历史记录 ({filteredRequests.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {filteredRequests.length === 0 ? (
                <EmptyState
                  title="没有变更记录"
                  description="当前没有符合条件的变更记录"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>标题</TableHead>
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
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <User className="h-4 w-4 text-gray-400" />
                            {cr.requester}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            {cr.schedule || '—'}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedRequest(cr);
                              setDetailDialogOpen(true);
                            }}
                          >
                            查看详情
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {activeTab === 'analytics' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">服务影响分析</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(statistics.by_service)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 10)
                  .map(([service, count]) => (
                    <div key={service} className="flex items-center justify-between">
                      <span className="text-sm">{service}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-[var(--accent-blue)] h-2 rounded-full"
                            style={{ width: `${(count / statistics.total) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{count}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">变更趋势</CardTitle>
            </CardHeader>
            <CardContent>
              <EmptyState
                title="趋势分析"
                description="变更趋势图表功能开发中"
              />
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'templates' && (
        <Card>
          <CardHeader>
            <CardTitle>变更模板</CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="变更模板"
              description="变更模板管理功能开发中"
            />
          </CardContent>
        </Card>
      )}

      {/* 详情对话框 */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>变更详情 - {selectedRequest?.title}</DialogTitle>
          </DialogHeader>
          {selectedRequest && (
            <div className="space-y-4">
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
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setDetailDialogOpen(false)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
