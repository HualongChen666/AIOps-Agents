'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Clock, User } from 'lucide-react';

interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  messageCount: number;
  status: 'active' | 'completed';
}

export default function ChatHistoryPage() {
  const sessions: ChatSession[] = [
    {
      id: '1',
      title: '系统健康检查',
      timestamp: '2分钟前',
      messageCount: 12,
      status: 'active',
    },
    {
      id: '2',
      title: '告警分析',
      timestamp: '1小时前',
      messageCount: 8,
      status: 'completed',
    },
    {
      id: '3',
      title: '容量评估',
      timestamp: '昨天',
      messageCount: 15,
      status: 'completed',
    },
    {
      id: '4',
      title: '根因分析',
      timestamp: '2天前',
      messageCount: 20,
      status: 'completed',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">对话历史</h1>
        <p className="text-sm text-gray-500 mt-1">查看和管理历史对话记录</p>
      </div>

      <div className="grid gap-4">
        {sessions.map((session) => (
          <Card key={session.id} className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  {session.title}
                </CardTitle>
                <Badge variant={session.status === 'active' ? 'default' : 'secondary'}>
                  {session.status === 'active' ? '进行中' : '已完成'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-6 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  {session.timestamp}
                </div>
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  {session.messageCount} 条消息
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
