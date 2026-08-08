'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

const API_BASE = '/api/v1/team-collaboration';

interface TeamMember {
  user_id: string;
  username: string;
  full_name: string;
  role: string;
  status: 'online' | 'offline' | 'busy';
  avatar?: string;
}

interface Team {
  id: string;
  name: string;
  description: string;
  members: TeamMember[];
}

interface Oncall {
  primary: TeamMember | null;
  secondary: TeamMember | null;
  since: string;
  until: string;
  next_rotation_in_hours: number;
}

interface Handoff {
  id: string;
  from_name: string;
  to_name: string | null;
  notes: string;
  created_at: string;
}

interface SharedDashboard {
  id: string;
  name: string;
  owner: string;
  lastModified: Date;
  viewers: number;
  description: string;
}

export default function TeamCollaborationPage() {
  const [activeTab, setActiveTab] = useState<'workspace' | 'comments' | 'dashboards'>('workspace');
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [oncall, setOncall] = useState<Oncall | null>(null);
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [sharedDashboards, setSharedDashboards] = useState<SharedDashboard[]>([]);
  const [selectedDashboard, setSelectedDashboard] = useState<SharedDashboard | null>(null);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedTeam = teams.find((t) => t.id === selectedTeamId) || teams[0] || null;

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/teams`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: Team[]) => {
        setTeams(data);
        if (data.length > 0) {
          setSelectedTeamId(data[0].id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedTeamId) return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`${API_BASE}/teams/${selectedTeamId}/oncall`).then((res) =>
        res.ok ? res.json() : null
      ),
      fetch(`${API_BASE}/teams/${selectedTeamId}/handoffs`).then((res) =>
        res.ok ? res.json() : []
      ),
    ])
      .then(([oncallData, handoffData]) => {
        setOncall(oncallData);
        setHandoffs(handoffData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedTeamId]);

  useEffect(() => {
    if (activeTab !== 'dashboards') return;
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/dashboards`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any) => {
        const items = Array.isArray(data) ? data : [];
        const mapped: SharedDashboard[] = items.map((d: any, index: number) => ({
          id: d.id || `dashboard-${index}`,
          name: d.name || '',
          owner: d.owner || '',
          lastModified: new Date(d.last_modified || d.lastModified || d.updated_at || Date.now()),
          viewers: d.viewers || 0,
          description: d.description || '',
        }));
        setSharedDashboards(mapped);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [activeTab]);

  const handleAddComment = async () => {
    if (!newComment.trim() || !selectedTeamId) return;
    const mentions = newComment.match(/@(\S+)/g)?.map((m) => m.substring(1)) || [];
    const body = {
      from_user_id: 'system',
      to_user_id: mentions[0] || undefined,
      notes: newComment,
    };
    const res = await fetch(`${API_BASE}/teams/${selectedTeamId}/handoffs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      const created = await res.json();
      setHandoffs((prev) => [created, ...prev]);
      setNewComment('');
    } else {
      setError('提交交接记录失败');
    }
  };

  const handleEscalate = async (incidentId: string) => {
    if (!selectedTeamId) return;
    const res = await fetch(`${API_BASE}/incidents/${incidentId}/escalate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: selectedTeamId, reason: '手动升级' }),
    });
    if (!res.ok) {
      setError('事件升级失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500';
      case 'busy':
        return 'bg-yellow-500';
      case 'offline':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'online':
        return '在线';
      case 'busy':
        return '忙碌';
      case 'offline':
        return '离线';
      default:
        return '未知';
    }
  };

  const memberAvatar = (member: TeamMember) => {
    if (member.avatar) return member.avatar;
    return member.full_name ? member.full_name.charAt(0).toUpperCase() : '?';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">团队协作</h1>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中...</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'workspace' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('workspace')}
        >
          团队工作区
        </Button>
        <Button
          variant={activeTab === 'comments' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('comments')}
        >
          交接记录
        </Button>
        <Button
          variant={activeTab === 'dashboards' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('dashboards')}
        >
          共享仪表盘
        </Button>
      </div>

      {activeTab === 'workspace' && (
        <div className="space-y-6">
          {teams.map((team) => (
            <Card key={team.id}>
              <CardHeader>
                <CardTitle>{team.name}</CardTitle>
                <p className="text-sm text-gray-500">{team.description}</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {selectedTeamId === team.id && oncall && oncall.primary && (
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm font-medium text-blue-900">
                        当前值班: {oncall.primary.full_name} ({oncall.primary.role})
                      </p>
                      {oncall.secondary && (
                        <p className="text-xs text-blue-700 mt-1">
                          备班: {oncall.secondary.full_name} | 下次轮班还有{' '}
                          {oncall.next_rotation_in_hours} 小时
                        </p>
                      )}
                      <div className="flex gap-2 mt-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEscalate(`INC-${Date.now()}`)}
                        >
                          手动升级事件
                        </Button>
                      </div>
                    </div>
                  )}
                  <div>
                    <h4 className="font-medium mb-3">
                      团队成员 ({team.members.length})
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {team.members.map((member) => (
                        <div
                          key={member.user_id}
                          className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
                        >
                          <div className="flex items-center gap-3 mb-2">
                            <div className="relative">
                              <span className="text-2xl">{memberAvatar(member)}</span>
                              <div
                                className={`absolute bottom-0 right-0 w-3 h-3 rounded-full ${getStatusColor(
                                  member.status
                                )}`}
                              />
                            </div>
                            <div>
                              <p className="font-medium">{member.full_name}</p>
                              <p className="text-xs text-gray-500">{member.role}</p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {getStatusText(member.status)}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedTeamId(team.id)}
                    >
                      查看值班表
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'comments' && selectedTeam && (
        <Card>
          <CardHeader>
            <CardTitle>交接记录 - {selectedTeam.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-6">
              {handoffs.map((handoff) => (
                <div key={handoff.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{handoff.from_name}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(handoff.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm mb-2">{handoff.notes}</p>
                  {handoff.to_name && (
                    <div className="flex gap-1">
                      <Badge variant="outline" className="text-xs">
                        @{handoff.to_name}
                      </Badge>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="border-t pt-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入交接内容..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                />
                <Button onClick={handleAddComment}>发送</Button>
              </div>
              <p className="text-xs text-gray-500 mt-2">提示：输入内容后按回车发送交接记录</p>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'dashboards' && (
        <div className="space-y-6">
          {sharedDashboards.length === 0 ? (
            <p className="text-sm text-gray-500">暂无共享仪表盘</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sharedDashboards.map((dashboard) => (
                <Card
                  key={dashboard.id}
                  className="cursor-pointer hover:shadow-lg transition"
                  onClick={() => setSelectedDashboard(dashboard)}
                >
                  <CardHeader>
                    <CardTitle className="text-lg">{dashboard.name}</CardTitle>
                    <p className="text-sm text-gray-500">{dashboard.description}</p>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">所有者</span>
                        <span>{dashboard.owner}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">查看人数</span>
                        <span>{dashboard.viewers}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">最后修改</span>
                        <span>{dashboard.lastModified.toLocaleDateString()}</span>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" className="w-full mt-4">
                      查看仪表盘
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {selectedDashboard && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>仪表盘详情: {selectedDashboard.name}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedDashboard(null)}>
                    ×
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                    <p className="text-sm">{selectedDashboard.description}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">所有者</label>
                      <p className="text-sm">{selectedDashboard.owner}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">查看人数</label>
                      <p className="text-sm">{selectedDashboard.viewers}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">最后修改</label>
                      <p className="text-sm">{selectedDashboard.lastModified.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
