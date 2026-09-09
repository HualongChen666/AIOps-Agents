'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { MessageSquare, Search, Zap, Activity, Container, Send } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '您好！我是AIOps智能助手。我可以帮您进行智能查数、快速调查、深度分析和容器巡检。请选择快捷操作或直接输入您的问题。',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');

  const quickActions = [
    { icon: Search, label: '智能查数', description: '查询指标、日志和告警' },
    { icon: Zap, label: '快速调查', description: '初步排查异常事件' },
    { icon: Activity, label: '深度调查', description: '多维度深入分析' },
    { icon: Container, label: '容器巡检', description: 'K8s集群健康巡检' },
  ];

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);
    setInput('');

    // 模拟AI回复
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '收到您的问题，正在分析中...',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }, 1000);
  };

  const handleQuickAction = (label: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `执行${label}`,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);

    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `正在执行${label}，请稍候...`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }, 1000);
  };

  return (
    <div className="h-full flex">
      {/* 左侧历史会话 */}
      <aside className="w-80 border-r border-gray-200 bg-gray-50 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">历史会话</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <div className="p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-500 cursor-pointer transition-colors">
            <div className="text-sm font-medium text-gray-900">系统健康检查</div>
            <div className="text-xs text-gray-500 mt-1">2分钟前</div>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-500 cursor-pointer transition-colors">
            <div className="text-sm font-medium text-gray-900">告警分析</div>
            <div className="text-xs text-gray-500 mt-1">1小时前</div>
          </div>
          <div className="p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-500 cursor-pointer transition-colors">
            <div className="text-sm font-medium text-gray-900">容量评估</div>
            <div className="text-xs text-gray-500 mt-1">昨天</div>
          </div>
        </div>
      </aside>

      {/* 中央对话区域 */}
      <main className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* 快捷操作按钮 */}
            {messages.length === 1 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                {quickActions.map((action) => (
                  <Card
                    key={action.label}
                    className="cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => handleQuickAction(action.label)}
                  >
                    <CardContent className="p-4 text-center">
                      <action.icon className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                      <h3 className="font-medium text-sm text-gray-900">{action.label}</h3>
                      <p className="text-xs text-gray-500 mt-1">{action.description}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* 消息列表 */}
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-2xl rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-200 text-gray-900'
                  }`}
                >
                  <div className="text-sm">{message.content}</div>
                  <div
                    className={`text-xs mt-2 ${
                      message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}
                  >
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 输入框 */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <div className="max-w-4xl mx-auto flex gap-2">
            <Input
              placeholder="输入您的问题，或使用 / 唤出操作列表"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              className="flex-1"
            />
            <Button onClick={handleSend}>
              <Send className="h-4 w-4 mr-2" />
              发送
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
