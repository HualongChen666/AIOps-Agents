'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Users, RefreshCw, Plus, UserCheck, Clock, AlertTriangle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface Team {
  id: string;
  name: string;
  description: string;
  members: Array<{
    user_id: string;
    username: string;
    full_name: string;
    role: string;
    status: string;
  }>;
  rotation: {
    type: string;
    start_date: string;
  };
}

interface OnCall {
  primary: {
    user_id: string;
    username: string;
    full_name: string;
  };
  secondary?: {
    user_id: string;
    username: string;
    full_name: string;
  };
}

interface Handoff {
  id: string;
  from_user_id: string;
  to_user_id: string;
  notes: string;
  created_at: string;
}

export default function TeamCollaborationPage() {
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [showHandoffModal, setShowHandoffModal] = useState(false);
  const [handoffNotes, setHandoffNotes] = useState('');

  const queryClient = useQueryClient();

  // 🔧 获取团队列表
  const { data: teamsData, isLoading: teamsLoading, error: teamsError, refetch: refetchTeams } = useQuery<Team[]>({
    queryKey: ['team-collaboration-teams'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/team-collaboration/teams');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取值班信息
  const { data: onCallData, isLoading: onCallLoading, refetch: refetchOnCall } = useQuery<OnCall>({
    queryKey: ['team-collaboration-oncall', selectedTeam?.id],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/team-collaboration/teams/${selectedTeam?.id}/oncall`);
      return resp.data;
    },
    enabled: !!selectedTeam,
    refetchInterval: 120000,
  });

  // 🔧 获取交接记录
  const { data: handoffsData, isLoading: handoffsLoading, refetch: refetchHandoffs } = useQuery<Handoff[]>({
    queryKey: ['team-collaboration-handoffs', selectedTeam?.id],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/team-collaboration/teams/${selectedTeam?.id}/handoffs`);
      return resp.data;
    },
    enabled: !!selectedTeam,
    refetchInterval: 120000,
  });

  // 🔧 创建交接记录
  const createHandoffMutation = useMutation({
    mutationFn: async (notes: string) => {
      const resp = await api.post(`/api/v1/team-collaboration/teams/${selectedTeam?.id}/handoffs`, {
        from_user_id: 'system',
        to_user_id: null,
        notes,
      });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-collaboration-handoffs'] });
      setShowHandoffModal(false);
      setHandoffNotes('');
      showSuccess('交接记录创建成功');
    },
    onError: () => {
      showError('交接记录创建失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(teamsLoading || onCallLoading || handoffsLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (teamsError) {
      showError('Failed to load teams');
      setPageError(teamsError as Error);
    }
  }, [teamsError, showError, setPageError]);

  const teams = teamsData || [];
  const onCall = onCallData || null;
  const handoffs = handoffsData || [];

  const teamColumns = [
    { key: 'name' as const, label: '团队名称' },
    {
      key: 'description' as const, label: '描述', render: (value: string) => (
        <div className="max-w-md truncate" title={value}>{value}</div>
      )
    },
    { key: 'members' as const, label: '成员数', render: (value: any[]) => value.length },
    { key: 'rotation' as const, label: '轮值类型', render: (value: any) => value.type },
  ];

  const handoffColumns = [
    { key: 'from_user_id' as const, label: '发送者' },
    { key: 'to_user_id' as const, label: '接收者', render: (value: string) => value || '-' },
    {
      key: 'notes' as const, label: '交接内容', render: (value: string) => (
        <div className="max-w-md truncate" title={value}>{value}</div>
      )
    },
    { key: 'created_at' as const, label: '创建时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  const handleTeamClick = (team: Team) => {
    setSelectedTeam(team);
  };

  const handleCreateHandoff = () => {
    createHandoffMutation.mutate(handoffNotes);
  };

  const handleRefresh = () => {
    refetchTeams();
    if (selectedTeam) {
      refetchOnCall();
      refetchHandoffs();
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
          description="无法加载团队协作数据，请稍后重试"
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const totalTeams = teams.length;
  const totalMembers = teams.reduce((sum, team) => sum + team.members.length, 0);
  const onlineMembers = teams.reduce((sum, team) => sum + team.members.filter((m) => m.status === 'online').length, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">团队协作</h1>
            <p className="text-sm text-gray-500">SRE团队管理和值班轮值</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总团队数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{totalTeams}</p>
            <p className="text-sm text-gray-500 mt-1">SRE团队总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总成员数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{totalMembers}</p>
            <p className="text-sm text-gray-500 mt-1">团队成员总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">在线成员</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{onlineMembers}</p>
            <p className="text-sm text-gray-500 mt-1">当前在线成员</p>
          </CardContent>
        </Card>
      </div>

      {/* Teams List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            团队列表 ({teams.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {teams.length === 0 ? (
            <EmptyState
              title="暂无团队"
              description="当前没有配置的SRE团队"
            />
          ) : (
            <DataTable
              data={teams}
              columns={teamColumns}
              pageSize={10}
              emptyMessage="暂无团队"
              onRowClick={handleTeamClick}
            />
          )}
        </CardContent>
      </Card>

      {/* Team Detail */}
      {selectedTeam && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserCheck className="h-5 w-5" />
                {selectedTeam.name} - 值班信息
              </CardTitle>
            </CardHeader>
            <CardContent>
              {onCallLoading ? (
                <LoadingSpinner />
              ) : onCall ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border rounded-lg bg-blue-50">
                    <div>
                      <label className="text-sm font-medium text-gray-700">主值班</label>
                      <p className="text-lg font-semibold text-gray-900">{onCall.primary.full_name} (@{onCall.primary.username})</p>
                    </div>
                    <UserCheck className="h-6 w-6 text-blue-600" />
                  </div>
                  {onCall.secondary && (
                    <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
                      <div>
                        <label className="text-sm font-medium text-gray-700">副值班</label>
                        <p className="text-lg font-semibold text-gray-900">{onCall.secondary.full_name} (@{onCall.secondary.username})</p>
                      </div>
                      <Clock className="h-6 w-6 text-gray-600" />
                    </div>
                  )}
                </div>
              ) : (
                <EmptyState title="暂无值班信息" description="当前团队没有配置值班轮值" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  交接记录
                </CardTitle>
                <Button size="sm" onClick={() => setShowHandoffModal(true)}>
                  <Plus className="h-4 w-4 mr-1" />
                  创建交接
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {handoffs.length === 0 ? (
                <EmptyState title="暂无交接记录" description="当前团队没有交接记录" />
              ) : (
                <DataTable
                  data={handoffs}
                  columns={handoffColumns}
                  pageSize={10}
                  emptyMessage="暂无交接记录"
                />
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Create Handoff Modal */}
      <EnhancedModal
        open={showHandoffModal}
        onOpenChange={setShowHandoffModal}
        title="创建交接记录"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">交接内容</label>
            <textarea
              value={handoffNotes}
              onChange={(e) => setHandoffNotes(e.target.value)}
              placeholder="输入交接内容..."
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[150px]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowHandoffModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateHandoff} disabled={createHandoffMutation.isPending}>
              {createHandoffMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}