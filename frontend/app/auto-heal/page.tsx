'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Wrench, AlertTriangle, CheckCircle, XCircle, Clock, RefreshCw, Play, Pause, FileText } from 'lucide-react';

interface HealTask {
  id: string;
  alertId: string;
  alertTitle: string;
  healPlan: string;
  riskLevel: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed' | 'failed';
  createdAt: string;
  approver?: string;
  approvalComment?: string;
  executionLog?: string;
  executionTime?: string;
}

interface HealStatistics {
  total_tasks: number;
  pending_tasks: number;
  approved_tasks: number;
  executing_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  success_rate: number;
  avg_execution_time: number;
}

export default function AutoHealPage() {
  const queryClient = useQueryClient();
  const [selectedTab, setSelectedTab] = useState<'pending' | 'approved' | 'executing' | 'completed' | 'failed'>('pending');
  const [selectedTask, setSelectedTask] = useState<HealTask | null>(null);
  const [approvalComment, setApprovalComment] = useState('');

  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch heal tasks
  const { data: healTasks, isLoading: tasksLoading, error: tasksError, refetch: refetchTasks } = useQuery<HealTask[]>({
    queryKey: ['heal-tasks'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/approvals/pending');
      const items = resp.data?.items || [];
      return items.map((item: any) => ({
        id: item.alert_id || item.id || String(Date.now()),
        alertId: item.alert_id || item.id || '',
        alertTitle: item.title || item.alert_id || '修复方案',
        healPlan: item.proposal || item.heal_plan || item.description || '',
        riskLevel: (item.risk_level || 'low') as 'low' | 'medium' | 'high',
        status: (item.status || 'pending') as HealTask['status'],
        createdAt: item.created_at || item.timestamp || new Date().toISOString(),
        approver: item.approver || '',
        approvalComment: item.approval_comment || '',
        executionLog: item.execution_log || '',
        executionTime: item.execution_time || '',
      }));
    },
    refetchInterval: 30000,
  });

  // Fetch heal statistics
  const { data: healStats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useQuery<HealStatistics>({
    queryKey: ['heal-statistics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/approvals/statistics');
      return resp.data || {
        total_tasks: 0,
        pending_tasks: 0,
        approved_tasks: 0,
        executing_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0,
        success_rate: 0,
        avg_execution_time: 0,
      };
    },
    refetchInterval: 60000,
  });

  // Approve task mutation
  const approveTaskMutation = useMutation({
    mutationFn: async (alertId: string) => {
      const resp = await api.patch(`/api/v1/approvals/${alertId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Task approved successfully');
      queryClient.invalidateQueries({ queryKey: ['heal-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['heal-statistics'] });
    },
    onError: (error: any) => {
      showError(`Failed to approve task: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Reject task mutation
  const rejectTaskMutation = useMutation({
    mutationFn: async ({ alertId, reason }: { alertId: string; reason: string }) => {
      const resp = await api.post('/api/v1/approvals/reject', { alert_id: alertId, reason });
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Task rejected successfully');
      queryClient.invalidateQueries({ queryKey: ['heal-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['heal-statistics'] });
    },
    onError: (error: any) => {
      showError(`Failed to reject task: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Execute task mutation
  const executeTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const resp = await api.patch(`/api/v1/approvals/${taskId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Task execution started');
      queryClient.invalidateQueries({ queryKey: ['heal-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['heal-statistics'] });
    },
    onError: (error: any) => {
      showError(`Failed to execute task: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (tasksError) {
      setPageError(tasksError as Error);
      showError('Failed to load heal tasks');
    }
  }, [tasksError, setPageError, showError]);

  const filteredTasks = healTasks?.filter((task) => task.status === selectedTab) || [];

  const handleApprove = async () => {
    if (!selectedTask) return;
    approveTaskMutation.mutate(selectedTask.alertId);
    setSelectedTask(null);
    setApprovalComment('');
  };

  const handleReject = async () => {
    if (!selectedTask) return;
    rejectTaskMutation.mutate({
      alertId: selectedTask.alertId,
      reason: approvalComment || '人工驳回',
    });
    setSelectedTask(null);
    setApprovalComment('');
  };

  const handleExecute = async (taskId: string) => {
    executeTaskMutation.mutate(taskId);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      case 'approved':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'executing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'pending' as const, label: '待审批', count: healStats?.pending_tasks || 0 },
    { key: 'approved' as const, label: '已批准', count: healStats?.approved_tasks || 0 },
    { key: 'executing' as const, label: '执行中', count: healStats?.executing_tasks || 0 },
    { key: 'completed' as const, label: '已完成', count: healStats?.completed_tasks || 0 },
    { key: 'failed' as const, label: '失败', count: healStats?.failed_tasks || 0 },
  ];

  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载自动修复数据，请稍后重试"
          action={<Button onClick={() => refetchTasks()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchTasks()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Wrench className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">自动修复</h1>
            <p className="text-sm text-gray-500">自动化故障修复和审批流程管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchTasks()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      {healStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">总任务数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-gray-900">{healStats.total_tasks}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">成功率</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{(healStats.success_rate * 100).toFixed(1)}%</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">平均执行时间</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">{Math.floor(healStats.avg_execution_time / 60)}m</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">待审批</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{healStats.pending_tasks}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSelectedTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${selectedTab === tab.key
                  ? 'bg-[var(--accent-blue)] text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {tab.key === 'pending' && <Clock className="h-4 w-4" />}
                {tab.key === 'approved' && <CheckCircle className="h-4 w-4" />}
                {tab.key === 'executing' && <Play className="h-4 w-4" />}
                {tab.key === 'completed' && <CheckCircle className="h-4 w-4" />}
                {tab.key === 'failed' && <XCircle className="h-4 w-4" />}
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 修复任务列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            {selectedTab === 'pending' ? '待审批' : selectedTab === 'approved' ? '已批准' : selectedTab === 'executing' ? '执行中' : selectedTab === 'completed' ? '已完成' : '失败'}任务
          </CardTitle>
        </CardHeader>
        <CardContent>
          {tasksLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : filteredTasks.length === 0 ? (
            <EmptyState
              title="没有任务"
              description={`当前没有${selectedTab === 'pending' ? '待审批' : selectedTab === 'approved' ? '已批准' : selectedTab === 'executing' ? '执行中' : selectedTab === 'completed' ? '已完成' : '失败'}任务`}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>告警</TableHead>
                  <TableHead>修复方案</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>审批人</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell className="font-mono text-sm">{task.id}</TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{task.alertTitle}</p>
                        <p className="text-sm text-gray-500">{task.alertId}</p>
                      </div>
                    </TableCell>
                    <TableCell className="max-w-md truncate">{task.healPlan}</TableCell>
                    <TableCell>
                      <Badge className={getRiskColor(task.riskLevel)}>
                        {task.riskLevel === 'low' ? '低' : task.riskLevel === 'medium' ? '中' : '高'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(task.status)}>
                        {task.status === 'pending' ? '待审批' :
                          task.status === 'approved' ? '已批准' :
                            task.status === 'rejected' ? '已拒绝' :
                              task.status === 'completed' ? '已完成' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(task.createdAt).toLocaleString()}
                    </TableCell>
                    <TableCell>{task.approver || '-'}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {task.status === 'pending' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedTask(task)}
                          >
                            审批
                          </Button>
                        )}
                        {task.status === 'approved' && (
                          <Button
                            size="sm"
                            onClick={() => handleExecute(task.id)}
                            disabled={executeTaskMutation.isPending}
                          >
                            {executeTaskMutation.isPending ? '执行中...' : '执行'}
                          </Button>
                        )}
                        {task.status === 'completed' && (
                          <Button variant="ghost" size="sm">
                            <FileText className="h-4 w-4 mr-1" />
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

      {/* 审批弹窗 */}
      {selectedTask && (
        <Dialog open={!!selectedTask} onOpenChange={() => setSelectedTask(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                审批修复任务 - {selectedTask.id}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警信息</label>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium text-gray-900">{selectedTask.alertTitle}</p>
                  <p className="text-sm text-gray-500 font-mono">{selectedTask.alertId}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">修复方案</label>
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{selectedTask.healPlan}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
                <Badge className={getRiskColor(selectedTask.riskLevel)}>
                  {selectedTask.riskLevel === 'low' ? '低风险' : selectedTask.riskLevel === 'medium' ? '中风险' : '高风险'}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">审批意见</label>
                <Textarea
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  placeholder="请输入审批意见（可选）..."
                  rows={3}
                />
              </div>
              {selectedTask.riskLevel === 'high' && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-800">⚠️ 高风险操作警告</p>
                      <p className="text-sm text-red-700 mt-1">此操作可能对系统产生重大影响，请仔细审查修复方案后再进行审批。</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedTask(null)}>
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={rejectTaskMutation.isPending}
              >
                {rejectTaskMutation.isPending ? '驳回中...' : '拒绝'}
              </Button>
              <Button
                onClick={handleApprove}
                disabled={approveTaskMutation.isPending}
              >
                {approveTaskMutation.isPending ? '批准中...' : '批准'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
