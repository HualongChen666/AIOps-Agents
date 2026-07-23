'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface Runbook {
  id: string;
  title: string;
  category: string;
  author: string;
  updatedAt: string;
  tags: string[];
  aiRecommended: boolean;
}

interface KnowledgeArticle {
  id: string;
  title: string;
  content: string;
  category: string;
  relevance: number;
}

export default function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const [runbooks, setRunbooks] = useState<Runbook[]>([
    {
      id: 'RB-001',
      title: '数据库连接池耗尽处理',
      category: '数据库',
      author: '张三',
      updatedAt: new Date().toISOString(),
      tags: ['数据库', '连接池', '故障处理'],
      aiRecommended: true,
    },
    {
      id: 'RB-002',
      title: 'API网关超时排查',
      category: '网络',
      author: '李四',
      updatedAt: new Date(Date.now() - 86400000).toISOString(),
      tags: ['API', '网关', '超时'],
      aiRecommended: false,
    },
    {
      id: 'RB-003',
      title: '内存泄漏诊断流程',
      category: '应用',
      author: '王五',
      updatedAt: new Date(Date.now() - 172800000).toISOString(),
      tags: ['内存', '泄漏', '诊断'],
      aiRecommended: true,
    },
  ]);

  const [aiRecommendations, setAiRecommendations] = useState<KnowledgeArticle[]>([
    {
      id: 'KA-001',
      title: '当前告警可能由数据库连接池耗尽引起',
      content: '根据历史数据分析，当前告警模式与数据库连接池耗尽案例匹配度85%。建议检查连接池配置和慢查询。',
      category: '故障诊断',
      relevance: 0.85,
    },
    {
      id: 'KA-002',
      title: '推荐参考Runbook: 数据库连接池耗尽处理',
      content: '该Runbook包含详细的排查步骤和解决方案，已成功解决23次类似问题。',
      category: '解决方案',
      relevance: 0.92,
    },
  ]);

  const filteredRunbooks = runbooks.filter(rb => {
    const matchesSearch = rb.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         rb.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory = selectedCategory === 'all' || rb.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">知识库</h1>
        <Button>创建Runbook</Button>
      </div>

      {/* AI推荐 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span>🤖</span>
            <span>AI推荐</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {aiRecommendations.map((rec) => (
              <div key={rec.id} className="p-4 border border-blue-200 bg-blue-50 rounded-lg">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium">{rec.title}</h3>
                  <Badge className="bg-blue-100 text-blue-800">
                    相关度: {(rec.relevance * 100).toFixed(0)}%
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 mb-2">{rec.content}</p>
                <div className="text-sm text-gray-500">类别: {rec.category}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索Runbook..."
              className="flex-1"
            />
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="all">全部类别</option>
              <option value="数据库">数据库</option>
              <option value="网络">网络</option>
              <option value="应用">应用</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Runbook列表 */}
      <Card>
        <CardHeader>
          <CardTitle>Runbook知识库</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredRunbooks.map((runbook) => (
              <div key={runbook.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium">{runbook.title}</h3>
                      {runbook.aiRecommended && (
                        <Badge className="bg-purple-100 text-purple-800">AI推荐</Badge>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      类别: {runbook.category} · 作者: {runbook.author} · 更新: {new Date(runbook.updatedAt).toLocaleDateString()}
                    </div>
                  </div>
                  <Button variant="outline" size="sm">
                    查看
                  </Button>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {runbook.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 知识统计 */}
      <Card>
        <CardHeader>
          <CardTitle>知识统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">总Runbook数</div>
              <div className="text-2xl font-bold">{runbooks.length}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">AI推荐</div>
              <div className="text-2xl font-bold text-purple-600">
                {runbooks.filter(rb => rb.aiRecommended).length}
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">本周新增</div>
              <div className="text-2xl font-bold">3</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">使用次数</div>
              <div className="text-2xl font-bold">156</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 快速创建 */}
      <Card>
        <CardHeader>
          <CardTitle>快速创建</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button variant="outline" className="h-24 flex flex-col items-center justify-center gap-2">
              <span className="text-2xl">📝</span>
              <span>从告警创建</span>
            </Button>
            <Button variant="outline" className="h-24 flex flex-col items-center justify-center gap-2">
              <span className="text-2xl">📋</span>
              <span>从模板创建</span>
            </Button>
            <Button variant="outline" className="h-24 flex flex-col items-center justify-center gap-2">
              <span className="text-2xl">🤖</span>
              <span>AI辅助创建</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
