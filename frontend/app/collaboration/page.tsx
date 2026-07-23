'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

interface Workspace {
  id: string;
  name: string;
  members: number;
  lastActivity: string;
}

interface Activity {
  id: string;
  user: string;
  action: string;
  target: string;
  timestamp: string;
}

export default function CollaborationPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [message, setMessage] = useState('');

  const [workspaces, setWorkspaces] = useState<Workspace[]>([
    { id: 'WS-001', name: '生产环境监控', members: 8, lastActivity: '5分钟前' },
    { id: 'WS-002', name: '告警响应团队', members: 5, lastActivity: '1小时前' },
    { id: 'WS-003', name: '容量规划组', members: 4, lastActivity: '2小时前' },
  ]);

  const [activities, setActivities] = useState<Activity[]>([
    {
      id: 'ACT-001',
      user: '张三',
      action: '创建了仪表盘',
      target: '生产环境概览',
      timestamp: new Date().toISOString(),
    },
    {
      id: 'ACT-002',
      user: '李四',
      action: '分享了告警规则',
      target: 'CPU告警',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      id: 'ACT-003',
      user: '王五',
      action: '@提及了你',
      target: '在告警响应团队',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
  ]);

  const [onlineUsers, setOnlineUsers] = useState([
    { id: 'USR-001', name: '张三', avatar: '👤', status: 'online' },
    { id: 'USR-002', name: '李四', avatar: '👤', status: 'online' },
    { id: 'USR-003', name: '王五', avatar: '👤', status: 'away' },
  ]);

  const filteredWorkspaces = workspaces.filter(ws =>
    ws.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">团队协作</h1>
        <Button>创建工作区</Button>
      </div>

      {/* 在线用户 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">在线成员</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            {onlineUsers.map((user) => (
              <div key={user.id} className="flex items-center gap-2">
                <div className="relative">
                  <span className="text-2xl">{user.avatar}</span>
                  <span
                    className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white ${
                      user.status === 'online' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                  />
                </div>
                <span className="text-sm">{user.name}</span>
              </div>
            ))}
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
              <div key={workspace.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer">
                <h3 className="font-medium mb-2">{workspace.name}</h3>
                <div className="text-sm text-gray-500">
                  <div>成员: {workspace.members}人</div>
                  <div>最后活动: {workspace.lastActivity}</div>
                </div>
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
            {activities.map((activity) => (
              <div key={activity.id} className="flex items-start gap-3">
                <span className="text-2xl">👤</span>
                <div className="flex-1">
                  <p>
                    <span className="font-medium">{activity.user}</span>
                    <span className="text-gray-500">{activity.action}</span>
                    <span className="font-medium">{activity.target}</span>
                  </p>
                  <p className="text-sm text-gray-500">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
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
              placeholder="输入消息，使用@提及成员..."
              className="flex-1"
            />
            <Button>发送</Button>
          </div>
          <div className="mt-2 text-sm text-gray-500">
            支持 @提及成员快速通知
          </div>
        </CardContent>
      </Card>

      {/* 共享仪表盘 */}
      <Card>
        <CardHeader>
          <CardTitle>共享仪表盘</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">生产环境概览</h3>
                <Badge>共享</Badge>
              </div>
              <p className="text-sm text-gray-500">由 张三 创建</p>
              <div className="mt-2 flex gap-2">
                <Button variant="outline" size="sm">查看</Button>
                <Button variant="outline" size="sm">编辑</Button>
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium">告警响应看板</h3>
                <Badge>共享</Badge>
              </div>
              <p className="text-sm text-gray-500">由 李四 创建</p>
              <div className="mt-2 flex gap-2">
                <Button variant="outline" size="sm">查看</Button>
                <Button variant="outline" size="sm">编辑</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
