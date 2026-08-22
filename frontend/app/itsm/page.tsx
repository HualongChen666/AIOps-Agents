'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Ticket, Plus, RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface ITSMIncident {
  incident_id: string;
  summary: string;
  description: string;
  provider: string;
  status: string;
  created_at: string;
  resolved_at?: string;
}

export default function ITSMPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formData, setFormData] = useState({
    summary: '',
    description: '',
    provider: 'servicenow',
    urgency: '3',
    project_key: 'OPS',
    issue_type: 'Bug',
  });

  const queryClient = useQueryClient();

  // 🔧 获取ITSM工单列表（模拟）
  const { data: incidentsData, isLoading, error, refetch } = useQuery<{ incidents: ITSMIncident[] }>({
    queryKey: ['itsm-incidents'],
    queryFn: async () => {
      // Since there's no list endpoint, we'll return empty list
      return { incidents: [] };
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 创建ITSM工单
  const createIncidentMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/itsm/incident', data, { params: { provider: data.provider } });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['itsm-incidents'] });
      setShowCreateModal(false);
      showSuccess('ITSM工单创建成功');
    },
    onError: () => {
      showError('ITSM工单创建失败');
    },
  });

  // 🔧 解决ITSM工单
  const resolveIncidentMutation = useMutation({
    mutationFn: async ({ incidentId, provider }: { incidentId: string; provider: string }) => {
      const resp = await api.patch(`/api/itsm/incident/${incidentId}`, null, { params: { provider } });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['itsm-incidents'] });
      showSuccess('ITSM工单已关闭');
    },
    onError: () => {
      showError('ITSM工单关闭失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(isLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (error) {
      showError('Failed to load ITSM incidents');
      setPageError(error as Error);
    }
  }, [error, showError, setPageError]);

  const incidents = incidentsData?.incidents || [];

  const incidentColumns = [
    { key: 'incident_id' as const, label: '工单ID' },
    { key: 'summary' as const, label: '摘要', render: (value: string) => (
      <div className="max-w-md truncate" title={value}>{value}</div>
    )},
    { key: 'provider' as const, label: '提供商' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge status={value === 'resolved' ? 'success' : value === 'created' ? 'warning' : 'error'} text={value} />
    )},
    { key: 'created_at' as const, label: '创建时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  const handleCreateIncident = () => {
    createIncidentMutation.mutate(formData);
  };

  const handleResolveIncident = (incidentId: string, provider: string) => {
    if (confirm('确定要关闭这个工单吗？')) {
      resolveIncidentMutation.mutate({ incidentId, provider });
    }
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
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
          description="无法加载ITSM工单数据，请稍后重试"
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

  const totalIncidents = incidents.length;
  const openIncidents = incidents.filter((i) => i.status !== 'resolved').length;
  const resolvedIncidents = incidents.filter((i) => i.status === 'resolved').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Ticket className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">ITSM集成</h1>
            <p className="text-sm text-gray-500">ServiceNow和Jira工单管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            创建工单
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总工单数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{totalIncidents}</p>
            <p className="text-sm text-gray-500 mt-1">ITSM工单总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">打开工单</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{openIncidents}</p>
            <p className="text-sm text-gray-500 mt-1">待处理工单</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已解决工单</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{resolvedIncidents}</p>
            <p className="text-sm text-gray-500 mt-1">已关闭工单</p>
          </CardContent>
        </Card>
      </div>

      {/* Incidents List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Ticket className="h-5 w-5" />
            ITSM工单列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {incidents.length === 0 ? (
            <EmptyState
              title="暂无工单"
              description="当前没有ITSM工单"
              action={<Button onClick={() => setShowCreateModal(true)}>创建第一个工单</Button>}
            />
          ) : (
            <DataTable
              data={incidents}
              columns={incidentColumns}
              pageSize={10}
              emptyMessage="暂无工单"
              onRowClick={(incident) => (
                <div className="flex gap-2">
                  {incident.status !== 'resolved' && (
                    <Button size="sm" onClick={() => handleResolveIncident(incident.incident_id, incident.provider)}>
                      <CheckCircle className="h-4 w-4 mr-1" />
                      关闭
                    </Button>
                  )}
                </div>
              )}
            />
          )}
        </CardContent>
      </Card>

      {/* Create Incident Modal */}
      <EnhancedModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        title="创建ITSM工单"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">提供商</label>
            <select
              value={formData.provider}
              onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="servicenow">ServiceNow</option>
              <option value="jira">Jira</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">摘要</label>
            <Input
              value={formData.summary}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              placeholder="工单摘要"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="工单详细描述"
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[100px]"
            />
          </div>
          {formData.provider === 'servicenow' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">紧急程度</label>
              <select
                value={formData.urgency}
                onChange={(e) => setFormData({ ...formData, urgency: e.target.value })}
                className="w-full px-3 py-2 border rounded-md bg-white"
              >
                <option value="1">1 - Critical</option>
                <option value="2">2 - High</option>
                <option value="3">3 - Moderate</option>
                <option value="4">4 - Low</option>
                <option value="5">5 - Planning</option>
              </select>
            </div>
          )}
          {formData.provider === 'jira' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">项目Key</label>
                <Input
                  value={formData.project_key}
                  onChange={(e) => setFormData({ ...formData, project_key: e.target.value })}
                  placeholder="OPS"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">问题类型</label>
                <select
                  value={formData.issue_type}
                  onChange={(e) => setFormData({ ...formData, issue_type: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md bg-white"
                >
                  <option value="Bug">Bug</option>
                  <option value="Task">Task</option>
                  <option value="Story">Story</option>
                </select>
              </div>
            </>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateIncident} disabled={createIncidentMutation.isPending}>
              {createIncidentMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}