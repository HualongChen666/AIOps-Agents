'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface TeamMember {
  id: string;
  name: string;
  role: string;
  avatar: string;
  status: 'online' | 'offline' | 'busy';
}

interface Comment {
  id: string;
  author: string;
  content: string;
  timestamp: Date;
  mentions: string[];
}

interface SharedDashboard {
  id: string;
  name: string;
  owner: string;
  lastModified: Date;
  viewers: number;
  description: string;
}

interface Workspace {
  id: string;
  name: string;
  members: TeamMember[];
  description: string;
}

export default function TeamCollaborationPage() {
  const [activeTab, setActiveTab] = useState<'workspace' | 'comments' | 'dashboards'>('workspace');
  const [newComment, setNewComment] = useState('');
  const [selectedDashboard, setSelectedDashboard] = useState<SharedDashboard | null>(null);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([
    {
      id: 'WS-001',
      name: 'AIOps运维团队',
      members: [
        { id: 'U-001', name: '张三', role: 'Team Lead', avatar: '👤', status: 'online' },
        { id: 'U-002', name: '李四', role: 'DevOps Engineer', avatar: '👤', status: 'online' },
        { id: 'U-003', name: '王五', role: 'SRE', avatar: '👤', status: 'busy' },
        { id: 'U-004', name: '赵六', role: 'Developer', avatar: '👤', status: 'offline' },
      ],
      description: '负责AIOps平台的运维和监控',
    },
  ]);

  const [comments, setComments] = useState<Comment[]>([
    {
      id: 'C-001',
      author: '张三',
      content: '@李四 请检查一下数据库告警',
      timestamp: new Date(Date.now() - 3600000),
      mentions: ['李四'],
    },
    {
      id: 'C-002',
      author: '李四',
      content: '已确认，正在处理中',
      timestamp: new Date(Date.now() - 1800000),
      mentions: [],
    },
  ]);

  const [sharedDashboards, setSharedDashboards] = useState<SharedDashboard[]>([
    {
      id: 'D-001',
      name: '生产环境监控仪表盘',
      owner: '张三',
      lastModified: new Date(Date.now() - 86400000),
      viewers: 12,
      description: '生产环境关键指标监控',
    },
    {
      id: 'D-002',
      name: '成本分析仪表盘',
      owner: '李四',
      lastModified: new Date(Date.now() - 172800000),
      viewers: 8,
      description: '云资源成本分析',
    },
    {
      id: 'D-003',
      name: '告警中心仪表盘',
      owner: '王五',
      lastModified: new Date(Date.now() - 259200000),
      viewers: 15,
      description: '实时告警监控',
    },
  ]);

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    const comment: Comment = {
      id: `C-${Date.now()}`,
      author: '当前用户',
      content: newComment,
      timestamp: new Date(),
      mentions: newComment.match(/@(\S+)/g)?.map((m) => m.substring(1)) || [],
    };
    setComments([...comments, comment]);
    setNewComment('');
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">团队协作</h1>
        <Button>创建工作区</Button>
      </div>

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
          讨论区
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
          {workspaces.map((workspace) => (
            <Card key={workspace.id}>
              <CardHeader>
                <CardTitle>{workspace.name}</CardTitle>
                <p className="text-sm text-gray-500">{workspace.description}</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-3">团队成员 ({workspace.members.length})</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {workspace.members.map((member) => (
                        <div key={member.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="relative">
                              <span className="text-2xl">{member.avatar}</span>
                              <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full ${getStatusColor(member.status)}`} />
                            </div>
                            <div>
                              <p className="font-medium">{member.name}</p>
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
                    <Button variant="outline" size="sm">
                      邀请成员
                    </Button>
                    <Button variant="outline" size="sm">
                      工作区设置
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'comments' && (
        <Card>
          <CardHeader>
            <CardTitle>讨论区</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-6">
              {comments.map((comment) => (
                <div key={comment.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{comment.author}</span>
                      <span className="text-xs text-gray-500">{comment.timestamp.toLocaleString()}</span>
                    </div>
                  </div>
                  <p className="text-sm mb-2">{comment.content}</p>
                  {comment.mentions.length > 0 && (
                    <div className="flex gap-1">
                      {comment.mentions.map((mention) => (
                        <Badge key={mention} variant="outline" className="text-xs">
                          @{mention}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2 mt-3">
                    <Button variant="ghost" size="sm" className="text-xs">
                      回复
                    </Button>
                    <Button variant="ghost" size="sm" className="text-xs">
                      引用
                    </Button>
                  </div>
                </div>
              ))}
            </div>
            <div className="border-t pt-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入评论，使用 @提及成员..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                />
                <Button onClick={handleAddComment}>发送</Button>
              </div>
              <p className="text-xs text-gray-500 mt-2">提示：使用 @成员名 可以提及团队成员</p>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'dashboards' && (
        <div className="space-y-6">
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
            <Card className="border-dashed flex items-center justify-center min-h-[200px] cursor-pointer hover:bg-gray-50 transition">
              <div className="text-center">
                <p className="text-4xl mb-2">+</p>
                <p className="text-sm text-gray-500">共享仪表盘</p>
              </div>
            </Card>
          </div>

          {selectedDashboard && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>仪表盘详情: {selectedDashboard.name}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setSelectedDashboard(null)}>
                    ✕
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
                  <div className="flex gap-2 pt-4 border-t">
                    <Button variant="outline" size="sm">
                      编辑权限
                    </Button>
                    <Button variant="outline" size="sm">
                      复制仪表盘
                    </Button>
                    <Button variant="outline" size="sm" className="text-red-600">
                      删除
                    </Button>
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
