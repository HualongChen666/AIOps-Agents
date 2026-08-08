'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

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

function toStringValue(value: unknown): string | undefined {
  if (typeof value === 'string' && value.length > 0) return value;
  if (typeof value === 'number') return String(value);
  return undefined;
}

export default function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isSearching, setIsSearching] = useState(false);

  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [aiRecommendations, setAiRecommendations] = useState<KnowledgeArticle[]>([]);

  function mapToArticle(result: any, idx: number): KnowledgeArticle {
    const payload = result?.payload || {};
    const title =
      toStringValue(payload.title) ??
      toStringValue(payload.script_key) ??
      toStringValue(payload.alert_id) ??
      toStringValue(payload.host) ??
      `RAG 结果 ${idx + 1}`;
    const raw = payload.comment ?? payload.evidence ?? payload;
    const content = typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2);
    const category =
      toStringValue(payload.category) ??
      toStringValue(payload.script_key) ??
      toStringValue(payload.alert_id) ??
      'RAG';
    return {
      id: `rag-article-${idx}`,
      title,
      content,
      category,
      relevance: typeof result.score === 'number' ? result.score : 0,
    };
  }

  function mapToRunbook(result: any, idx: number): Runbook {
    const payload = result?.payload || {};
    const title =
      toStringValue(payload.title) ??
      toStringValue(payload.script_key) ??
      toStringValue(payload.alert_id) ??
      toStringValue(payload.host) ??
      `RAG 结果 ${idx + 1}`;
    const category =
      toStringValue(payload.category) ??
      toStringValue(payload.script_key) ??
      toStringValue(payload.alert_id) ??
      'RAG';
    const author = toStringValue(payload.author) ?? toStringValue(payload.host) ?? 'RAG';
    const tags = [payload.alert_id, payload.script_key, payload.host]
      .map(toStringValue)
      .filter((v): v is string => v !== undefined);
    let updatedAt = new Date().toISOString();
    if (payload.updated_at) {
      const d = new Date(payload.updated_at);
      if (!isNaN(d.getTime())) updatedAt = d.toISOString();
    }
    return {
      id: `rag-runbook-${idx}`,
      title,
      category,
      author,
      updatedAt,
      tags: tags.length > 0 ? tags : ['RAG'],
      aiRecommended: (typeof result.score === 'number' ? result.score : 0) >= 0.8,
    };
  }

  async function handleCreateRunbook() {
    const title = window.prompt('Runbook 标题：');
    if (!title) return;
    const content = window.prompt('Runbook 内容：');
    if (!content) return;
    try {
      await api.post('/api/v1/rag/ingest', {
        text: content,
        payload: { title, category: '未分类', author: '当前用户', tags: [] },
      });
      window.alert('Runbook 创建成功');
    } catch (err) {
      window.alert('Runbook 创建失败');
    }
  }

  async function handleSearch() {
    const query = searchQuery.trim();
    if (!query) return;
    setIsSearching(true);
    try {
      const { data } = await api.post('/api/v1/rag/search', { query, top_k: 10 });
      const results = Array.isArray(data) ? data : [];
      setAiRecommendations(results.slice(0, 3).map(mapToArticle));
      setRunbooks(results.map(mapToRunbook));
    } finally {
      setIsSearching(false);
    }
  }

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
        <Button onClick={handleCreateRunbook}>创建Runbook</Button>
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
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
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
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? '搜索中...' : '搜索'}
            </Button>
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
              <div className="text-2xl font-bold">—</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">使用次数</div>
              <div className="text-2xl font-bold">—</div>
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
