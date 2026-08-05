'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

const API_BASE = '/api/v1/collaboration';

interface TaskSummary {
  total: number;
  done: number;
}

interface WorkspaceSummary {
  id: string;
  name: string;
  status: string;
  members: number;
  last_activity: string;
  task_summary: TaskSummary;
}

interface Message {
  id: string;
  user: string;
  content: string;
  created_at: string;
}

interface Task {
  id: string;
  title: string;
  assignee: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Workspace extends WorkspaceSummary {
  alert_id?: string;
  repair_id?: string;
  assignees: string[];
  notes: string[];
  messages: Message[];
  tasks: Task[];
  created_at: string;
  updated_at: string;
}

export default function CollaborationPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const loadWorkspaces = async () => {
    try {
      const res = await api.get(`${API_BASE}/workspaces`);
      const list = (res.data?.workspaces || []) as WorkspaceSummary[];
      setWorkspaces(list);
      if (list.length && !selectedId) {
        setSelectedId(list[0].id);
      }
    } catch (err) {
      console.error('Failed to load workspaces', err);
    }
  };

  const loadWorkspace = async (id: string) => {
    setLoading(true);
    try {
      const res = await api.get(`${API_BASE}/workspaces/${id}`);
      setSelectedWorkspace(res.data as Workspace);
    } catch (err) {
      console.error('Failed to load workspace', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspaces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedId) {
      loadWorkspace(selectedId);
    }
  }, [selectedId]);

  const filteredWorkspaces = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreate = async () => {
    const name = window.prompt('请输入工作区名称：');
    if (!name) return;
    try {
      await api.post(`${API_BASE}/workspaces`, {
        name,
        alert_id: null,
        repair_id: null,
        assignees: [],
      });
      await loadWorkspaces();
    } catch (err) {
      console.error('Failed to create workspace', err);
    }
  };

  const handleSend = async () => {
    if (!selectedWorkspace || !message.trim()) return;
    try {
      await api.post(`${API_BASE}/workspaces/${selectedWorkspace.id}/messages`, {
        user: '当前用户',
        content: message.trim(),
      });
      setMessage('');
      if (selectedId) await loadWorkspace(selectedId);
      await loadWorkspaces();
    } catch (err) {
      console.error('Failed to send message', err);
    }
  };

  const handleResolve = async () => {
    if (!selectedWorkspace) return;
    try {
      await api.post(`${API_BASE}/workspaces/${selectedWorkspace.id}/resolve`);
      if (selectedId) await loadWorkspace(selectedId);
      await loadWorkspaces();
    } catch (err) {
      console.error('Failed to resolve workspace', err);
    }
  };

  const onlineUsers = (selectedWorkspace?.assignees || []).map((name, index) => ({
    id: `USR-${index}`,
    name,
    avatar: '👤',
    status: 'online',
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">团队协作</h1>
        <Button onClick={handleCreate}>创建工作区</Button>
      </div>

      {/* 在线成员 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">在线成员</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            {onlineUsers.length > 0 ? (
              onlineUsers.map((user) => (
                <div key={user.id} className="flex items-center gap-2">
                  <div className="relative">
                    <span className="text-2xl">{user.avatar}</span>
                    <span
                      className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white ${user.status === 'online' ? 'bg-green-500' : 'bg-yellow-500'
                        }`}
                    />
                  </div>
                  <span className="text-sm">{user.name}</span>
                </div>
              ))
            ) : (
              <span className="text-sm text-gray-400">选择一个工作区查看成员</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 工作区列表 */}
      <Card>
        <CardHeader>
          <CardTitle>工作区</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索工作区..."
            className="mb-4"
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {filteredWorkspaces.map((workspace) => (
              <div
                key={workspace.id}
                onClick={() => setSelectedId(workspace.id)}
                className={`p-4 border rounded-lg hover:bg-gray-50 transition cursor-pointer ${selectedId === workspace.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200'
                  }`}
              >
                <h3 className="font-medium mb-2">{workspace.name}</h3>
                <div className="text-sm text-gray-500">
                  <div>成员: {workspace.members}人</div>
                  <div>
                    任务: {workspace.task_summary.done}/{workspace.task_summary.total}
                  </div>
                  <div>
                    最后活动:{' '}
                    {workspace.last_activity
                      ? new Date(workspace.last_activity).toLocaleString()
                      : '无'}
                  </div>
                </div>
                <Badge className="mt-2">{workspace.status}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 活动动态 */}
      <Card>
        <CardHeader>
          <CardTitle>活动动态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {selectedWorkspace ? (
              [...selectedWorkspace.messages].reverse().map((activity) => (
                <div key={activity.id} className="flex items-start gap-3">
                  <span className="text-2xl">👤</span>
                  <div className="flex-1">
                    <p>
                      <span className="font-medium">{activity.user}</span>
                      <span className="text-gray-500"> 说：</span>
                      <span className="font-medium">{activity.content}</span>
                    </p>
                    <p className="text-sm text-gray-500">
                      {new Date(activity.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-400">选择一个工作区查看动态</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 快速消息 */}
      <Card>
        <CardHeader>
          <CardTitle>发送消息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={
                selectedWorkspace
                  ? '输入消息，使用@提及成员...'
                  : '请先选择一个工作区'
              }
              disabled={!selectedWorkspace || loading}
              className="flex-1"
            />
            <Button
              onClick={handleSend}
              disabled={!selectedWorkspace || !message.trim() || loading}
            >
              发送
            </Button>
          </div>
          <div className="mt-2 text-sm text-gray-500">
            支持 @提及成员快速通知
          </div>
        </CardContent>
      </Card>

      {/* 任务看板 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>任务看板</CardTitle>
          {selectedWorkspace && selectedWorkspace.status !== 'resolved' && (
            <Button variant="outline" size="sm" onClick={handleResolve}>
              标记已解决
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {selectedWorkspace ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {selectedWorkspace.tasks.length > 0 ? (
                selectedWorkspace.tasks.map((task) => (
                  <div key={task.id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium">{task.title}</h3>
                      <Badge>{task.status}</Badge>
                    </div>
                    <p className="text-sm text-gray-500">
                      负责人: {task.assignee || '未分配'}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400">暂无任务</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">选择一个工作区查看任务</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
