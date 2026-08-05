'use client'

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  actions?: Array<{
    label: string;
    onClick: () => void;
  }>;
}

interface SuggestedQuery {
  id: string;
  label: string;
  icon: string;
}

export default function AICopilotPage() {
  const [isOpen, setIsOpen] = useState(true);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '你好！我是AI Copilot智能助手。我可以帮助你：\n\n• 自然语言查询系统状态\n• 解释告警原因\n• 提供修复建议\n• 生成查询语句\n\n有什么我可以帮助你的吗？',
      timestamp: new Date(),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const suggestedQueries: SuggestedQuery[] = [
    { id: '1', label: '过去24小时CPU使用率最高的服务', icon: '📊' },
    { id: '2', label: '为什么web服务响应时间变慢了？', icon: '🔍' },
    { id: '3', label: '如何解决数据库连接超时错误？', icon: '🔧' },
    { id: '4', label: '生成最近告警的统计报告', icon: '📈' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // 🔧 修复: 使用真实 API 调用 AI 分析
    try {
      const resp = await api.post('/api/ai/analyze', {
        query: input,
        include_metrics: true,
        include_rich_context: true,
      });

      const aiResponse: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: resp.data.analysis || resp.data.response || resp.data.answer || '分析完成',
        timestamp: new Date(),
        actions: resp.data.actions ? resp.data.actions.map((action: any) => ({
          label: action.label,
          onClick: () => {
            // 实现操作点击处理
            console.log('Action clicked:', action);
          },
        })) : [],
      };

      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error('AI analysis failed:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '抱歉，AI 分析失败，请稍后重试。',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSuggestedQuery = (query: string) => {
    setInput(query);
    handleSendMessage();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4">
        <Button
          onClick={() => setIsOpen(true)}
          className="rounded-full w-14 h-14 shadow-lg"
          size="lg"
        >
          🤖
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">AI Copilot 智能助手</h1>
        <Button variant="outline" onClick={() => setIsOpen(false)}>
          最小化
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 聊天窗口 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>对话</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[500px] flex flex-col">
              {/* 消息列表 */}
              <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-4 ${message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-900'
                        }`}
                    >
                      <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                      {message.actions && message.actions.length > 0 && (
                        <div className="flex gap-2 mt-3">
                          {message.actions.map((action, index) => (
                            <Button
                              key={index}
                              variant={message.role === 'user' ? 'secondary' : 'outline'}
                              size="sm"
                              onClick={action.onClick}
                            >
                              {action.label}
                            </Button>
                          ))}
                        </div>
                      )}
                      <div className="text-xs mt-2 opacity-70">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg p-4">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* 输入框 */}
              <div className="flex gap-2">
                <Input
                  placeholder="输入你的问题... (按Enter发送)"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="flex-1"
                />
                <Button onClick={handleSendMessage} disabled={!input.trim() || isTyping}>
                  发送
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 建议查询 */}
        <Card>
          <CardHeader>
            <CardTitle>建议查询</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {suggestedQueries.map((query) => (
                <Button
                  key={query.id}
                  variant="outline"
                  className="w-full justify-start text-left h-auto py-3"
                  onClick={() => handleSuggestedQuery(query.label)}
                >
                  <span className="mr-2">{query.icon}</span>
                  <span className="text-sm">{query.label}</span>
                </Button>
              ))}
            </div>

            <div className="mt-6 pt-6 border-t">
              <h4 className="font-medium mb-3">能力说明</h4>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>自然语言查询系统状态和指标</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>智能告警解释和根因分析</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>提供修复建议和操作指南</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>生成SQL查询语句</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>对话式根因分析</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t">
              <h4 className="font-medium mb-3">使用技巧</h4>
              <div className="space-y-2 text-sm text-gray-600">
                <p>• 使用具体的问题描述</p>
                <p>• 提及时间范围（如"过去24小时"）</p>
                <p>• 提及服务名称或指标类型</p>
                <p>• 可以追问以获取更详细信息</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 功能演示 */}
      <Card>
        <CardHeader>
          <CardTitle>功能演示</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">自然语言查询</h4>
              <p className="text-sm text-gray-600">
                "过去24小时CPU使用率最高的服务" → 自动生成查询并返回结果
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">智能告警解释</h4>
              <p className="text-sm text-gray-600">
                "为什么这个告警触发了？" → 分析告警上下文并提供解释
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">修复建议生成</h4>
              <p className="text-sm text-gray-600">
                "如何解决这个错误？" → 提供分步修复指南和代码示例
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">SQL查询生成</h4>
              <p className="text-sm text-gray-600">
                "生成查询最近告警的SQL" → 自动生成可执行的SQL语句
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
