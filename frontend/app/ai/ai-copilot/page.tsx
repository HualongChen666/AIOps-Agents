'use client'

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function AICopilotPage() {
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

    try {
      const resp = await api.post('/api/ai/analyze', {
        query: input,
        include_metrics: true,
        include_rich_context: true,
      });

      const analysis = resp.data?.analysis ?? resp.data;
      const content =
        typeof analysis === 'string'
          ? analysis
          : analysis?.recommended_action
            ? String(analysis.recommended_action)
            : JSON.stringify(analysis, null, 2) || '分析完成';

      const aiResponse: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiResponse]);
    } catch (error: any) {
      console.error('AI analysis failed:', error);

      let errorMessage = '抱歉，AI 分析服务暂时不可用。';
      let errorDetails = '';

      if (error?.response) {
        errorDetails = `状态码: ${error.response.status}\n`;
        if (error.response.data) {
          errorDetails += `响应数据: ${JSON.stringify(error.response.data, null, 2)}\n`;
        }
      } else if (error?.request) {
        errorDetails = '请求已发送但没有收到响应\n';
      } else {
        errorDetails = `错误信息: ${error?.message || '未知错误'}\n`;
      }

      if (error?.response?.status === 500) {
        errorMessage = 'AI 服务配置错误：请检查后端是否配置了 AI_API_KEY (MiniMax) 或 OPENAI_API_KEY 环境变量。';
      } else if (error?.response?.status === 401) {
        errorMessage = 'AI 服务认证失败：请检查 API Key 配置是否正确。';
      } else if (error?.code === 'ECONNREFUSED') {
        errorMessage = '无法连接到 AI 服务：请确认后端服务正在运行。';
      }

      const errorResponse: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: errorMessage + '\n\n调试信息:\n' + errorDetails + '\n\n如需启用 AI 功能，请在后端 .env 文件中配置：\n• AI_API_KEY=your_minimax_key_here (MiniMax)\n• OPENAI_API_KEY=your_openai_key_here (OpenAI)\n• ANTHROPIC_API_KEY=your_anthropic_key_here (Anthropic)',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">AI Copilot 智能助手</h1>
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

        {/* 能力说明 */}
        <Card>
          <CardHeader>
            <CardTitle>能力说明</CardTitle>
          </CardHeader>
          <CardContent>
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
    </div>
  );
}
