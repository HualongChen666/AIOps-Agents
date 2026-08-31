'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Users, UserPlus, Trash2, Settings, RefreshCw, Shield, Activity, MessageSquare, CheckSquare } from 'lucide-react';

interface Team {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  status: 'active' | 'inactive' | 'archived';
  tags: string[];
  created_at: string;
  member_count?: number;
}

interface Member {
  id: string;
  team_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  role: 'owner' | 'admin' | 'member' | 'guest';
  status: 'active' | 'inactive';
  joined_at: string;
}

interface Permission {
  id: string;
  team_id: string;
  resource_type: string;
  resource_id: string;
  permission_level: 'read' | 'write' | 'admin' | 'full';
  granted_to: string;
  granted_by: string;
  granted_at: string;
}

interface Activity {
  id: string;
  team_id: string;
  user_id: string;
  user_name: string;
  activity_type: string;
  description: string;
  created_at: string;
}

export default function CollaborationAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'teams' | 'members' | 'permissions' | 'activities'>('teams');
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [newTeamData, setNewTeamData] = useState({
    name: '',
    description: '',
    owner_id: '',
    tags: [],
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch teams
  const { data: teams, isLoading: teamsLoading, error: teamsError, refetch: refetchTeams } = useQuery<Team[]>({
    queryKey: ['collaboration-teams'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/collaboration/teams');
      return resp.data.teams || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch members
  const { data: members, isLoading: membersLoading, error: membersError, refetch: refetchMembers } = useQuery<Member[]>({
    queryKey: ['collaboration-members'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/collaboration/members');
      return resp.data.members || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch permissions
  const { data: permissions, isLoading: permissionsLoading, error: permissionsError, refetch: refetchPermissions } = useQuery<Permission[]>({
    queryKey: ['collaboration-permissions'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/collaboration/permissions');
      return resp.data.permissions || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch activities
  const { data: activities, isLoading: activitiesLoading, error: activitiesError, refetch: refetchActivities } = useQuery<Activity[]>({
    queryKey: ['collaboration-activities'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/collaboration/activities');
      return resp.data.activities || resp.data || [];
    },
    refetchInterval: 30000,
  });

  // Create team mutation
  const createTeamMutation = useMutation({
    mutationFn: async (teamData: typeof newTeamData) => {
      const resp = await api.post('/api/v1/collaboration/teams', teamData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Team created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['collaboration-teams'] });
    },
    onError: (error: any) => {
      showError(`Failed to create team: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete team mutation
  const deleteTeamMutation = useMutation({
    mutationFn: async (teamId: string) => {
      const resp = await api.delete(`/api/v1/collaboration/teams/${teamId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Team deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['collaboration-teams'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete team: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (teamsError) {
      setPageError(teamsError as Error);
      showError('Failed to load teams');
    }
  }, [teamsError, setPageError, showError]);

  const filteredTeams = teams?.filter((team) => {
    if (statusFilter !== 'all' && team.status !== statusFilter) return false;
    if (debouncedSearch && !team.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'archived':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'owner':
        return 'bg-purple-100 text-purple-800';
      case 'admin':
        return 'bg-blue-100 text-blue-800';
      case 'member':
        return 'bg-green-100 text-green-800';
      case 'guest':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPermissionColor = (level: string) => {
    switch (level) {
      case 'full':
        return 'bg-purple-100 text-purple-800';
      case 'admin':
        return 'bg-red-100 text-red-800';
      case 'write':
        return 'bg-blue-100 text-blue-800';
      case 'read':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'team_created':
        return <Users className="h-4 w-4" />;
      case 'member_added':
        return <UserPlus className="h-4 w-4" />;
      case 'permission_granted':
        return <Shield className="h-4 w-4" />;
      case 'message_posted':
        return <MessageSquare className="h-4 w-4" />;
      case 'task_completed':
        return <CheckSquare className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const handleCreateTeam = () => {
    if (!newTeamData.name) {
      showError('Please enter team name');
      return;
    }
    createTeamMutation.mutate(newTeamData);
  };

  const handleDeleteTeam = (teamId: string) => {
    if (!window.confirm('Are you sure you want to delete this team?')) return;
    deleteTeamMutation.mutate(teamId);
  };

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
          description="无法加载协作数据，请稍后重试"
          action={<Button onClick={() => refetchTeams()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchTeams()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">协作高级</h1>
            <p className="text-sm text-gray-500">团队、成员、权限和活动管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchTeams()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <UserPlus className="h-4 w-4 mr-2" />
            创建团队
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="teams">
            <Users className="h-4 w-4 mr-2" />
            团队
          </TabsTrigger>
          <TabsTrigger value="members">
            <UserPlus className="h-4 w-4 mr-2" />
            成员
          </TabsTrigger>
          <TabsTrigger value="permissions">
            <Shield className="h-4 w-4 mr-2" />
            权限
          </TabsTrigger>
          <TabsTrigger value="activities">
            <Activity className="h-4 w-4 mr-2" />
            活动
          </TabsTrigger>
        </TabsList>

        <TabsContent value="teams" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  团队管理
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索团队..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">全部状态</option>
                    <option value="active">活跃</option>
                    <option value="inactive">非活跃</option>
                    <option value="archived">已归档</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {teamsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredTeams.length === 0 ? (
                <EmptyState
                  title="没有团队"
                  description="点击创建团队开始协作"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建团队</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>所有者ID</TableHead>
                      <TableHead>成员数</TableHead>
                      <TableHead>标签</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTeams.map((team) => (
                      <TableRow key={team.id}>
                        <TableCell className="font-mono text-sm">{team.id}</TableCell>
                        <TableCell className="font-medium">{team.name}</TableCell>
                        <TableCell>{team.description}</TableCell>
                        <TableCell className="font-mono text-sm">{team.owner_id}</TableCell>
                        <TableCell>{team.member_count || 0}</TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {team.tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {team.tags.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{team.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(team.status)}>
                            {team.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(team.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedTeam(team)}
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteTeam(team.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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
        </TabsContent>

        <TabsContent value="members" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                成员管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              {membersLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !members || members.length === 0 ? (
                <EmptyState title="无成员" description="暂无成员记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>用户名</TableHead>
                      <TableHead>邮箱</TableHead>
                      <TableHead>团队ID</TableHead>
                      <TableHead>角色</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>加入时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell className="font-mono text-sm">{member.id}</TableCell>
                        <TableCell className="font-medium">{member.user_name}</TableCell>
                        <TableCell>{member.user_email}</TableCell>
                        <TableCell className="font-mono text-sm">{member.team_id}</TableCell>
                        <TableCell>
                          <Badge className={getRoleColor(member.role)}>
                            {member.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={member.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {member.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(member.joined_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            编辑
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="permissions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                权限管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              {permissionsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !permissions || permissions.length === 0 ? (
                <EmptyState title="无权限" description="暂无权限记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资源类型</TableHead>
                      <TableHead>资源ID</TableHead>
                      <TableHead>授予对象</TableHead>
                      <TableHead>权限级别</TableHead>
                      <TableHead>授予者</TableHead>
                      <TableHead>授予时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {permissions.map((permission) => (
                      <TableRow key={permission.id}>
                        <TableCell className="font-mono text-sm">{permission.id}</TableCell>
                        <TableCell>{permission.resource_type}</TableCell>
                        <TableCell className="font-mono text-sm">{permission.resource_id}</TableCell>
                        <TableCell>{permission.granted_to}</TableCell>
                        <TableCell>
                          <Badge className={getPermissionColor(permission.permission_level)}>
                            {permission.permission_level}
                          </Badge>
                        </TableCell>
                        <TableCell>{permission.granted_by}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(permission.granted_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            撤销
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activities" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                活动记录
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activitiesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !activities || activities.length === 0 ? (
                <EmptyState title="无活动" description="暂无活动记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>用户</TableHead>
                      <TableHead>活动类型</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>团队ID</TableHead>
                      <TableHead>时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {activities.map((activity) => (
                      <TableRow key={activity.id}>
                        <TableCell className="font-mono text-sm">{activity.id}</TableCell>
                        <TableCell>{activity.user_name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getActivityIcon(activity.activity_type)}
                            <span className="capitalize">{activity.activity_type.replace('_', ' ')}</span>
                          </div>
                        </TableCell>
                        <TableCell>{activity.description}</TableCell>
                        <TableCell className="font-mono text-sm">{activity.team_id}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(activity.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建团队</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">团队名称</label>
              <Input
                value={newTeamData.name}
                onChange={(e) => setNewTeamData({ ...newTeamData, name: e.target.value })}
                placeholder="输入团队名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={newTeamData.description}
                onChange={(e) => setNewTeamData({ ...newTeamData, description: e.target.value })}
                placeholder="团队描述"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">所有者ID</label>
              <Input
                value={newTeamData.owner_id}
                onChange={(e) => setNewTeamData({ ...newTeamData, owner_id: e.target.value })}
                placeholder="所有者用户ID"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateTeam} disabled={createTeamMutation.isPending}>
              {createTeamMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
