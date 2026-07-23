'use client'

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const AICopilot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '你好！我是AIOps智能助手。我可以帮你分析告警、提供修复建议、查询系统状态等。有什么我可以帮助你的吗？',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    // 模拟AI响应
    setTimeout(() => {
      const responses = [
        '根据当前告警分析，建议优先处理CPU使用率过高的问题。可以尝试重启web-service实例或增加副本数。',
        '系统健康度良好，MTTR为15分钟，低于目标值30分钟。自动修复成功率为87%，表现良好。',
        '检测到数据库查询延迟增加，建议检查慢查询日志并优化索引。我可以帮你生成优化建议。',
        '根据历史数据分析，预计7天后磁盘空间将不足，建议提前进行清理或扩容。',
        '当前系统可用性为99.95%，满足SLA要求。告警数量为23个，其中严重告警2个需要立即处理。',
      ];

      const aiMessage: Message = {
        role: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const quickActions = [
    { label: '分析当前告警', query: '分析当前告警情况' },
    { label: '系统健康度', query: '当前系统健康度如何' },
    { label: '修复建议', query: '提供修复建议' },
    { label: '容量预测', query: '预测未来容量需求' },
  ];

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 rounded-full w-14 h-14 shadow-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
        title="AI Copilot"
      >
        <span className="text-2xl">🤖</span>
      </Button>
    );
  }

  return (
    <Card className="fixed bottom-6 right-6 w-96 h-[500px] shadow-xl z-50">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <span>🤖</span>
          <span>AI Copilot</span>
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)} className="h-8 w-8">
          <span className="text-lg">×</span>
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col h-[calc(100%-60px)]">
        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="text-sm">{msg.content}</p>
                <p className="text-xs mt-1 opacity-70">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg p-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 快捷操作 */}
        {messages.length <= 1 && (
          <div className="mb-3">
            <p className="text-xs text-gray-500 mb-2">快捷操作：</p>
            <div className="flex flex-wrap gap-2">
              {quickActions.map((action) => (
                <Button
                  key={action.label}
                  variant="outline"
                  size="sm"
                  onClick={() => setInput(action.query)}
                  className="text-xs"
                >
                  {action.label}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* 输入框 */}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="输入问题..."
            disabled={isLoading}
          />
          <Button onClick={sendMessage} disabled={isLoading || !input.trim()}>
            发送
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
